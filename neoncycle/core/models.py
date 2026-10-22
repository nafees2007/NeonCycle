from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('HOUSEHOLD', 'Household'),
        ('COLLECTOR', 'Collector'),
        ('RECYCLER', 'Recycler'),
        ('ADMIN', 'Admin'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='HOUSEHOLD')
    wallet_balance = models.FloatField(default=0.0)
    co2_saved_kg = models.FloatField(default=0.0)
    is_online = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class GarbagePrice(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=15, unique=True)
    price_per_kg = models.FloatField(default=40.0)
    change_pct = models.FloatField(default=2.5)

    def __str__(self):
        return f"{self.code} - {self.name}: ₹{self.price_per_kg}/kg"


class CollectionOrder(models.Model):
    STATUS_CHOICES = [
        ('PENDING', '1. Waiting for Nearby Collector'),
        ('ACCEPTED', '2. Collector Assigned & En Route'),
        ('WEIGHED', '3. Weighed & Paid (In Transit to Recycler)'),
        ('RECYCLED', '4. Delivered & Recycled'),
    ]
    household = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hh_orders')
    collector = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='col_orders')
    garbage_type = models.ForeignKey(GarbagePrice, on_delete=models.CASCADE)
    address = models.CharField(max_length=255)

    estimated_weight_kg = models.FloatField()
    actual_weight_kg = models.FloatField(null=True, blank=True)

    household_payout = models.FloatField(default=0.0)
    collector_earning = models.FloatField(default=0.0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def step_num(self):
        return {'PENDING': 1, 'ACCEPTED': 2, 'WEIGHED': 3, 'RECYCLED': 4}.get(self.status, 1)

    @property
    def weight_variance_pct(self):
        """Calculates % difference between Actual Scale Weight and Estimated Weight."""
        if self.actual_weight_kg is None or not self.estimated_weight_kg:
            return 0.0
        return round(((self.actual_weight_kg - self.estimated_weight_kg) / max(0.1, self.estimated_weight_kg)) * 100.0, 1)

    @property
    def is_scale_anomaly(self):
        """Flags fraud/anomaly if scale weight deviates by more than ±40% from estimated weight."""
        if self.actual_weight_kg is None:
            return False
        return abs(self.weight_variance_pct) > 40.0

    @property
    def anomaly_reason(self):
        """Explains why the AI Scale Detector flagged or verified the order."""
        if self.actual_weight_kg is None:
            return "Awaiting Smart-Scale Weighing"
        var = self.weight_variance_pct
        if var > 40.0:
            return f"FRAUD ALERT (+{var}%): Possible Scale Tampering / Payout Inflation"
        elif var < -40.0:
            return f"FRAUD ALERT ({var}%): Possible Rider Skimming / Under-Weighing"
        return f"AI Scale Verified ({var:+.1f}% within normal ±40% tolerance)"


class RecyclerDemand(models.Model):
    recycler = models.ForeignKey(User, on_delete=models.CASCADE)
    garbage_type = models.ForeignKey(GarbagePrice, on_delete=models.CASCADE)
    needed_kg = models.FloatField()
    offered_bonus_per_kg = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)


class RecycledProduct(models.Model):
    recycler = models.ForeignKey(User, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=150)
    quantity_kg = models.FloatField()
    price_per_kg = models.FloatField()
    manufacturer_buyer = models.CharField(max_length=150)
    is_sold = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_price(self):
        return round(self.quantity_kg * self.price_per_kg, 2)