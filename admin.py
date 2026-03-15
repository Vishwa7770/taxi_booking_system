"""
taxiapp/admin.py
Django admin configuration with custom list views and analytics.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Vehicle, Ride, Payment, Rating


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "email", "first_name", "last_name", "is_driver", "is_rider", "average_rating", "is_staff"]
    list_filter = ["is_driver", "is_rider", "is_staff", "is_active"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Taxi Profile", {"fields": ("is_driver", "is_rider", "phone", "avatar", "average_rating", "total_ratings")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Taxi Profile", {"fields": ("is_driver", "is_rider", "phone")}),
    )
    search_fields = ["username", "email", "phone"]


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ["__str__", "driver", "vehicle_type", "license_plate", "is_online", "last_location_update"]
    list_filter = ["vehicle_type", "is_online"]
    search_fields = ["license_plate", "driver__username", "make", "model"]
    actions = ["set_online", "set_offline"]

    @admin.action(description="Set selected vehicles ONLINE")
    def set_online(self, request, queryset):
        queryset.update(is_online=True)

    @admin.action(description="Set selected vehicles OFFLINE")
    def set_offline(self, request, queryset):
        queryset.update(is_online=False)


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = [
        "id", "rider", "driver", "status", "pickup_address",
        "dropoff_address", "estimated_fare", "final_fare", "requested_at"
    ]
    list_filter = ["status", "vehicle_type_requested", "requested_at"]
    search_fields = ["rider__username", "driver__username", "pickup_address", "dropoff_address"]
    readonly_fields = ["requested_at", "accepted_at", "started_at", "completed_at", "cancelled_at"]
    date_hierarchy = "requested_at"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("rider", "driver")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "ride", "amount", "payment_method", "status", "paid_at"]
    list_filter = ["status", "payment_method"]
    search_fields = ["ride__id", "transaction_id"]
    readonly_fields = ["paid_at", "created_at"]


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ["id", "ride", "rater", "rated_user", "score", "created_at"]
    list_filter = ["score"]
    search_fields = ["rater__username", "rated_user__username"]


# ── Customise admin site branding ──────────────────────────────────────────────
admin.site.site_header = "🚕 TaxiApp Administration"
admin.site.site_title = "TaxiApp Admin"
admin.site.index_title = "Welcome to TaxiApp Control Panel"
