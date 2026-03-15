"""
taxiapp/models.py
All database models for the taxi booking platform.
"""
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


# ─── User ──────────────────────────────────────────────────────────────────────

class User(AbstractUser):
    """
    Extended user model.
    A user is either a rider, a driver, or both (edge case for testing).
    Staff users are admins.
    """
    is_driver = models.BooleanField(default=False, help_text="User registered as a driver")
    is_rider = models.BooleanField(default=True, help_text="User registered as a rider")
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    # Aggregate rating (recalculated on each new rating)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    total_ratings = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        role = "Driver" if self.is_driver else "Rider"
        return f"{self.get_full_name() or self.username} ({role})"

    def recalculate_rating(self):
        """Recalculate and save average rating from all received ratings."""
        received = Rating.objects.filter(rated_user=self)
        count = received.count()
        if count:
            avg = received.aggregate(models.Avg("score"))["score__avg"]
            self.average_rating = round(avg, 2)
            self.total_ratings = count
            self.save(update_fields=["average_rating", "total_ratings"])


# ─── Vehicle ───────────────────────────────────────────────────────────────────

class VehicleType(models.TextChoices):
    ECONOMY = "economy", "Economy"
    COMFORT = "comfort", "Comfort"
    XL = "xl", "XL / SUV"
    PREMIUM = "premium", "Premium"


class Vehicle(models.Model):
    """Vehicle owned by a driver."""
    driver = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="vehicle", limit_choices_to={"is_driver": True}
    )
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices, default=VehicleType.ECONOMY)
    make = models.CharField(max_length=50, help_text="e.g. Toyota")
    model = models.CharField(max_length=50, help_text="e.g. Camry")
    year = models.PositiveSmallIntegerField()
    color = models.CharField(max_length=30)
    license_plate = models.CharField(max_length=20, unique=True)
    seats = models.PositiveSmallIntegerField(default=4)
    # Driver availability toggle
    is_online = models.BooleanField(default=False)
    # Last known GPS location
    current_latitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.year} {self.make} {self.model} [{self.license_plate}]"

    def update_location(self, lat, lng):
        self.current_latitude = lat
        self.current_longitude = lng
        self.last_location_update = timezone.now()
        self.save(update_fields=["current_latitude", "current_longitude", "last_location_update"])


# ─── Ride ──────────────────────────────────────────────────────────────────────

class RideStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    ACCEPTED = "accepted", "Accepted"
    DRIVER_EN_ROUTE = "driver_en_route", "Driver En Route"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class Ride(models.Model):
    """A single ride from pickup to drop-off."""
    rider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="rides_as_rider")
    driver = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="rides_as_driver"
    )
    vehicle_type_requested = models.CharField(
        max_length=20, choices=VehicleType.choices, default=VehicleType.ECONOMY
    )
    # Pickup location
    pickup_address = models.CharField(max_length=255)
    pickup_latitude = models.DecimalField(max_digits=11, decimal_places=8)
    pickup_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    # Drop-off location
    dropoff_address = models.CharField(max_length=255)
    dropoff_latitude = models.DecimalField(max_digits=11, decimal_places=8)
    dropoff_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    # Fare
    estimated_fare = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    final_fare = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    distance_km = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    # Status and timestamps
    status = models.CharField(max_length=20, choices=RideStatus.choices, default=RideStatus.REQUESTED)
    requested_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(blank=True)
    # Special notes
    notes = models.TextField(blank=True, help_text="Rider notes to driver")

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Ride #{self.pk} | {self.rider} → {self.dropoff_address} [{self.status}]"

    def accept(self, driver):
        self.driver = driver
        self.status = RideStatus.ACCEPTED
        self.accepted_at = timezone.now()
        self.save()

    def start(self):
        self.status = RideStatus.IN_PROGRESS
        self.started_at = timezone.now()
        self.save()

    def complete(self, final_fare=None):
        self.status = RideStatus.COMPLETED
        self.completed_at = timezone.now()
        if final_fare is not None:
            self.final_fare = final_fare
        self.save()

    def cancel(self, reason=""):
        self.status = RideStatus.CANCELLED
        self.cancelled_at = timezone.now()
        self.cancel_reason = reason
        self.save()


# ─── Payment ───────────────────────────────────────────────────────────────────

class PaymentMethod(models.TextChoices):
    CASH = "cash", "Cash"
    STRIPE = "stripe", "Card (Stripe)"
    PAYPAL = "paypal", "PayPal"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"


class Payment(models.Model):
    """Payment record associated with a completed ride."""
    ride = models.OneToOneField(Ride, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    # Stripe / PayPal transaction reference
    transaction_id = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment #{self.pk} | ${self.amount} [{self.status}]"

    def mark_paid(self, transaction_id=""):
        self.status = PaymentStatus.COMPLETED
        self.paid_at = timezone.now()
        if transaction_id:
            self.transaction_id = transaction_id
        self.save()


# ─── Rating ────────────────────────────────────────────────────────────────────

class Rating(models.Model):
    """
    Rating left after a completed ride.
    Both rider and driver can leave one rating per ride.
    """
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name="ratings")
    rater = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="ratings_given")
    rated_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="ratings_received")
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5"
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevent duplicate ratings for the same ride by the same user
        unique_together = ("ride", "rater")

    def __str__(self):
        return f"Rating {self.score}★ on Ride #{self.ride_id} by {self.rater}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Recalculate the rated user's average rating
        if self.rated_user:
            self.rated_user.recalculate_rating()
