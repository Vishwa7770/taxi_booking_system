"""
taxiapp/views.py
All views:
  - Template views (HTML dashboards)
  - REST API ViewSets
"""
import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Avg
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User, Vehicle, Ride, Payment, Rating, RideStatus, PaymentStatus, PaymentMethod
from .serializers import (
    UserRegisterSerializer, UserProfileSerializer, VehicleSerializer,
    RideListSerializer, RideDetailSerializer, RideCreateSerializer,
    PaymentSerializer, RatingSerializer, AnalyticsSummarySerializer,
    VehicleLocationSerializer,
)

stripe.api_key = settings.STRIPE_SECRET_KEY


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE VIEWS
# ══════════════════════════════════════════════════════════════════════════════

def home(request):
    """Landing page – redirect logged-in users to their dashboard."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "taxiapp/home.html")


def signup_view(request):
    if request.method == "POST":
        data = request.POST
        if data["password1"] != data["password2"]:
            messages.error(request, "Passwords do not match.")
            return render(request, "taxiapp/signup.html")
        if User.objects.filter(username=data["username"]).exists():
            messages.error(request, "Username already taken.")
            return render(request, "taxiapp/signup.html")
        user = User.objects.create_user(
            username=data["username"],
            email=data.get("email", ""),
            password=data["password1"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            phone=data.get("phone", ""),
        )
        role = data.get("role", "rider")
        user.is_rider = role == "rider"
        user.is_driver = role == "driver"
        user.save()
        login(request, user)
        messages.success(request, "Account created! Welcome to TaxiApp.")
        return redirect("dashboard")
    return render(request, "taxiapp/signup.html")


def login_view(request):
    if request.method == "POST":
        user = authenticate(request, username=request.POST["username"], password=request.POST["password"])
        if user:
            login(request, user)
            return redirect("dashboard")
        messages.error(request, "Invalid credentials.")
    return render(request, "taxiapp/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard(request):
    if request.user.is_driver:
        return redirect("driver_dashboard")
    return redirect("rider_dashboard")


@login_required
def rider_dashboard(request):
    rides = Ride.objects.filter(rider=request.user).order_by("-requested_at")[:5]
    return render(request, "taxiapp/rider_dashboard.html", {"rides": rides})


@login_required
def driver_dashboard(request):
    if not request.user.is_driver:
        messages.error(request, "You are not registered as a driver.")
        return redirect("rider_dashboard")
    rides = Ride.objects.filter(driver=request.user).order_by("-requested_at")[:5]
    vehicle = getattr(request.user, "vehicle", None)
    earnings = (
        Ride.objects.filter(driver=request.user, status=RideStatus.COMPLETED)
        .aggregate(total=Sum("final_fare"))["total"] or 0
    )
    return render(
        request, "taxiapp/driver_dashboard.html",
        {"rides": rides, "vehicle": vehicle, "total_earnings": earnings}
    )

@login_required
def book_ride(request):
    """Direct POST view for booking - avoids DRF session auth issues."""
    if request.method == "POST":
        from .utils import haversine_distance, estimate_fare
        pickup_lat  = request.POST.get("pickup_lat", "").strip()
        pickup_lng  = request.POST.get("pickup_lng", "").strip()
        dropoff_lat = request.POST.get("dropoff_lat", "").strip()
        dropoff_lng = request.POST.get("dropoff_lng", "").strip()
        pickup_address  = request.POST.get("pickup_address", "")
        dropoff_address = request.POST.get("dropoff_address", "")
        vehicle_type    = request.POST.get("vehicle_type", "economy")

        if not all([pickup_lat, pickup_lng, dropoff_lat, dropoff_lng]):
            messages.error(request, "Please click the map to set both Pickup and Drop-off locations.")
            return redirect("rider_dashboard")
        try:
            plat, plng = round(float(pickup_lat), 6), round(float(pickup_lng), 6)
            dlat, dlng = round(float(dropoff_lat), 6), round(float(dropoff_lng), 6)
            dist = haversine_distance(plat, plng, dlat, dlng)
            fare = estimate_fare(dist)
            ride = Ride.objects.create(
                rider=request.user,
                pickup_address=pickup_address or f"{plat}, {plng}",
                pickup_latitude=plat,
                pickup_longitude=plng,
                dropoff_address=dropoff_address or f"{dlat}, {dlng}",
                dropoff_latitude=dlat,
                dropoff_longitude=dlng,
                vehicle_type_requested=vehicle_type,
                distance_km=round(dist, 2),
                estimated_fare=fare,
            )
            messages.success(request, f"Ride #{ride.id} booked! Estimated fare: ${fare}. Searching for a driver...")
        except Exception as e:
            messages.error(request, f"Booking failed: {e}")
    return redirect("rider_dashboard")

@login_required
def ride_history(request):
    if request.user.is_driver:
        rides = Ride.objects.filter(driver=request.user)
    else:
        rides = Ride.objects.filter(rider=request.user)
    return render(request, "taxiapp/ride_history.html", {"rides": rides})


@login_required
def ride_detail_view(request, pk):
    ride = get_object_or_404(Ride, pk=pk)
    # Only allow rider or driver to see this page
    if ride.rider != request.user and ride.driver != request.user and not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect("dashboard")
    already_rated = Rating.objects.filter(ride=ride, rater=request.user).exists()
    return render(request, "taxiapp/ride_detail.html", {"ride": ride, "already_rated": already_rated})


# ══════════════════════════════════════════════════════════════════════════════
#  REST API – AUTH
# ══════════════════════════════════════════════════════════════════════════════

class RegisterAPIView(generics.CreateAPIView):
    """POST /api/auth/register/ – Create a new user account."""
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegisterSerializer


class MeAPIView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/auth/me/ – Current user's profile."""
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


# ══════════════════════════════════════════════════════════════════════════════
#  REST API – VEHICLE
# ══════════════════════════════════════════════════════════════════════════════

class VehicleViewSet(viewsets.ModelViewSet):
    """
    CRUD for driver vehicles.
    Only the owning driver can manage their vehicle.
    """
    serializer_class = VehicleSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return Vehicle.objects.all()
        return Vehicle.objects.filter(driver=self.request.user)

    def perform_create(self, serializer):
        serializer.save(driver=self.request.user)

    @action(detail=True, methods=["post"], url_path="toggle-online")
    def toggle_online(self, request, pk=None):
        """POST /api/vehicles/<pk>/toggle-online/ – Go online or offline."""
        vehicle = self.get_object()
        vehicle.is_online = not vehicle.is_online
        vehicle.save(update_fields=["is_online"])
        return Response({"is_online": vehicle.is_online})

    @action(detail=True, methods=["post"], url_path="update-location")
    def update_location(self, request, pk=None):
        """POST /api/vehicles/<pk>/update-location/ – Update GPS."""
        vehicle = self.get_object()
        lat = request.data.get("lat")
        lng = request.data.get("lng")
        if lat is None or lng is None:
            return Response({"error": "lat and lng required"}, status=400)
        vehicle.update_location(lat, lng)
        return Response(VehicleLocationSerializer(vehicle).data)


# ══════════════════════════════════════════════════════════════════════════════
#  REST API – RIDE
# ══════════════════════════════════════════════════════════════════════════════

class IsRiderOrDriver(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated


class RideViewSet(viewsets.ModelViewSet):
    """
    Ride lifecycle management.
    Riders create rides; drivers accept/start/complete them.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [
        __import__('rest_framework.authentication', fromlist=['SessionAuthentication']).SessionAuthentication,
        __import__('rest_framework_simplejwt.authentication', fromlist=['JWTAuthentication']).JWTAuthentication,
    ]

    def get_serializer_class(self):
        if self.action == "create":
            return RideCreateSerializer
        if self.action in ("list",):
            return RideListSerializer
        return RideDetailSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Ride.objects.all()
        if user.is_driver:
            return Ride.objects.filter(driver=user) | Ride.objects.filter(status=RideStatus.REQUESTED)
        return Ride.objects.filter(rider=user)

    # ── Rider actions ──────────────────────────────────────────────────────

    @action(detail=False, methods=["get"], url_path="fare-estimate")
    def fare_estimate(self, request):
        """
        GET /api/rides/fare-estimate/?pickup_lat=...&pickup_lng=...&dropoff_lat=...&dropoff_lng=...
        Returns estimated fare and distance.
        """
        from .utils import haversine_distance, estimate_fare
        try:
            dist = haversine_distance(
                float(request.query_params["pickup_lat"]),
                float(request.query_params["pickup_lng"]),
                float(request.query_params["dropoff_lat"]),
                float(request.query_params["dropoff_lng"]),
            )
        except (KeyError, ValueError):
            return Response({"error": "Provide pickup_lat, pickup_lng, dropoff_lat, dropoff_lng"}, status=400)
        fare = estimate_fare(dist)
        return Response({"distance_km": round(dist, 2), "estimated_fare": str(fare)})

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_ride(self, request, pk=None):
        """POST /api/rides/<pk>/cancel/ – Rider or driver cancels a ride."""
        ride = self.get_object()
        if ride.status in (RideStatus.COMPLETED, RideStatus.CANCELLED):
            return Response({"error": "Ride cannot be cancelled."}, status=400)
        ride.cancel(reason=request.data.get("reason", ""))
        return Response(RideDetailSerializer(ride).data)

    # ── Driver actions ─────────────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="accept")
    def accept_ride(self, request, pk=None):
        """POST /api/rides/<pk>/accept/ – Driver accepts a requested ride."""
        ride = get_object_or_404(Ride, pk=pk, status=RideStatus.REQUESTED)
        if not request.user.is_driver:
            return Response({"error": "Only drivers can accept rides."}, status=403)
        ride.accept(request.user)
        self._notify_user(ride.rider_id, ride.id, ride.status, "Your driver is on the way!")
        return Response(RideDetailSerializer(ride).data)

    @action(detail=True, methods=["post"], url_path="start")
    def start_ride(self, request, pk=None):
        """POST /api/rides/<pk>/start/ – Driver starts the ride (rider onboard)."""
        ride = get_object_or_404(Ride, pk=pk, driver=request.user, status=RideStatus.ACCEPTED)
        ride.start()
        self._notify_user(ride.rider_id, ride.id, ride.status, "Your ride has started!")
        return Response(RideDetailSerializer(ride).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete_ride(self, request, pk=None):
        """POST /api/rides/<pk>/complete/ – Driver marks ride as completed."""
        ride = get_object_or_404(Ride, pk=pk, driver=request.user, status=RideStatus.IN_PROGRESS)
        from .utils import estimate_fare
        final_fare = estimate_fare(float(ride.distance_km or 0), ride.duration_minutes)
        ride.complete(final_fare=final_fare)
        # Auto-create payment record
        Payment.objects.get_or_create(
            ride=ride,
            defaults={"amount": final_fare, "payment_method": PaymentMethod.CASH},
        )
        self._notify_user(ride.rider_id, ride.id, ride.status, "Ride completed! Please rate your driver.")
        return Response(RideDetailSerializer(ride).data)

    @action(detail=False, methods=["get"], url_path="pending")
    def pending_rides(self, request):
        """GET /api/rides/pending/ – Driver sees all requested (unaccepted) rides."""
        if not request.user.is_driver:
            return Response({"error": "Drivers only"}, status=403)
        rides = Ride.objects.filter(status=RideStatus.REQUESTED)
        return Response(RideListSerializer(rides, many=True).data)

    # ── Helper ─────────────────────────────────────────────────────────────

    @staticmethod
    def _notify_user(user_id, ride_id, status, message):
        """
        Push a WebSocket notification to the user's notification group.
        This is a fire-and-forget; if Redis is unavailable it silently fails.
        """
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            layer = get_channel_layer()
            async_to_sync(layer.group_send)(
                f"user_{user_id}_notifications",
                {"type": "ride_update", "ride_id": ride_id, "status": status, "message": message},
            )
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  REST API – PAYMENT
# ══════════════════════════════════════════════════════════════════════════════

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(ride__rider=user) | Payment.objects.filter(ride__driver=user)

    @action(detail=True, methods=["post"], url_path="pay-stripe")
    def pay_stripe(self, request, pk=None):
        """
        POST /api/payments/<pk>/pay-stripe/
        Body: {"payment_method_id": "pm_xxxx"}
        Creates a Stripe PaymentIntent and confirms it.
        """
        payment = self.get_object()
        if payment.status == PaymentStatus.COMPLETED:
            return Response({"error": "Already paid."}, status=400)
        if not settings.STRIPE_SECRET_KEY:
            return Response({"error": "Stripe not configured."}, status=503)
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(payment.amount * 100),  # Stripe uses cents
                currency="usd",
                payment_method=request.data.get("payment_method_id"),
                confirm=True,
                return_url="http://localhost:8000/payment/success/",
            )
            payment.mark_paid(transaction_id=intent.id)
            payment.payment_method = PaymentMethod.STRIPE
            payment.save(update_fields=["payment_method"])
            return Response(PaymentSerializer(payment).data)
        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)


# ══════════════════════════════════════════════════════════════════════════════
#  REST API – RATING
# ══════════════════════════════════════════════════════════════════════════════

class RatingViewSet(viewsets.ModelViewSet):
    serializer_class = RatingSerializer
    http_method_names = ["get", "post", "head", "options"]  # No update/delete

    def get_queryset(self):
        return Rating.objects.filter(rater=self.request.user)

    def perform_create(self, serializer):
        serializer.save(rater=self.request.user)


# ══════════════════════════════════════════════════════════════════════════════
#  REST API – ADMIN ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

class AnalyticsAPIView(APIView):
    """GET /api/analytics/ – Admin-only summary stats."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        rides = Ride.objects.all()
        completed = rides.filter(status=RideStatus.COMPLETED)
        revenue = Payment.objects.filter(status=PaymentStatus.COMPLETED).aggregate(
            total=Sum("amount")
        )["total"] or 0
        avg_fare = completed.aggregate(avg=Avg("final_fare"))["avg"] or 0

        data = {
            "total_rides": rides.count(),
            "completed_rides": completed.count(),
            "cancelled_rides": rides.filter(status=RideStatus.CANCELLED).count(),
            "total_revenue": revenue,
            "total_drivers": User.objects.filter(is_driver=True).count(),
            "total_riders": User.objects.filter(is_rider=True).count(),
            "online_drivers": Vehicle.objects.filter(is_online=True).count(),
            "avg_fare": avg_fare,
        }
        return Response(AnalyticsSummarySerializer(data).data)
