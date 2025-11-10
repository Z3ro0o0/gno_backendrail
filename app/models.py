from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class Role(models.Model):
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class User(AbstractUser):
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self) -> str:
        return self.username or super().__str__()


class OTPCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_codes')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'code', 'is_used']),
            models.Index(fields=['expires_at']),
        ]
        verbose_name = 'One-Time Password'
        verbose_name_plural = 'One-Time Passwords'

    def has_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def __str__(self) -> str:
        return f"OTP for {self.user} at {self.created_at:%Y-%m-%d %H:%M:%S}"


class TruckType(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
    
class AccountType(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class PlateNumber(models.Model):
    number = models.CharField(max_length=255)

    def __str__(self):
        return self.number
    
class RepairAndMaintenanceAccount(models.Model):
    account_number = models.CharField(max_length=255)
    truck_type = models.ForeignKey(TruckType, on_delete=models.CASCADE)
    account_type = models.ForeignKey(AccountType, on_delete=models.CASCADE)
    plate_number = models.ForeignKey(PlateNumber, on_delete=models.CASCADE)
    debit = models.DecimalField(max_digits=10, decimal_places=2)
    credit = models.DecimalField(max_digits=10, decimal_places=2)
    final_total = models.DecimalField(max_digits=10, decimal_places=2)
    reference_number = models.CharField(max_length=255)
    date = models.DateField()
    description = models.CharField(max_length=255)
    remarks = models.CharField(max_length=255)

    def __str__(self):
        return self.account_number

class InsuranceAccount(models.Model):
    account_number = models.CharField(max_length=255)
    truck_type = models.ForeignKey(TruckType, on_delete=models.CASCADE)
    account_type = models.ForeignKey(AccountType, on_delete=models.CASCADE)
    plate_number = models.ForeignKey(PlateNumber, on_delete=models.CASCADE)
    debit = models.DecimalField(max_digits=10, decimal_places=2)
    credit = models.DecimalField(max_digits=10, decimal_places=2)
    final_total = models.DecimalField(max_digits=10, decimal_places=2)
    reference_number = models.CharField(max_length=255)
    date = models.DateField()
    description = models.CharField(max_length=255)
    remarks = models.CharField(max_length=255)

    def __str__(self):
        return self.account_number

class FuelAccount(models.Model):
    account_number = models.CharField(max_length=255)
    truck_type = models.ForeignKey(TruckType, on_delete=models.CASCADE)
    account_type = models.ForeignKey(AccountType, on_delete=models.CASCADE)
    plate_number = models.ForeignKey(PlateNumber, on_delete=models.CASCADE)
    debit = models.DecimalField(max_digits=10, decimal_places=2)
    credit = models.DecimalField(max_digits=10, decimal_places=2)
    final_total = models.DecimalField(max_digits=10, decimal_places=2)
    reference_number = models.CharField(max_length=255)
    date = models.DateField()
    driver = models.CharField(max_length=255)
    route = models.CharField(max_length=255)
    liters = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    route = models.CharField(max_length=255)
    description = models.TextField()
    remarks = models.CharField(max_length=255)
    front_load = models.CharField(max_length=255)
    back_load = models.CharField(max_length=255)

    def __str__(self):
        return self.account_number

class TaxAccount(models.Model):
    account_number = models.CharField(max_length=255)
    truck_type = models.ForeignKey(TruckType, on_delete=models.CASCADE)
    account_type = models.ForeignKey(AccountType, on_delete=models.CASCADE)
    plate_number = models.ForeignKey(PlateNumber, on_delete=models.CASCADE)
    debit = models.DecimalField(max_digits=10, decimal_places=2)
    credit = models.DecimalField(max_digits=10, decimal_places=2)
    final_total = models.DecimalField(max_digits=10, decimal_places=2)
    reference_number = models.CharField(max_length=255)
    date = models.DateField()
    description = models.TextField()
    remarks = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.account_number

class AllowanceAccount(models.Model):
    account_number = models.CharField(max_length=255)
    truck_type = models.ForeignKey(TruckType, on_delete=models.CASCADE)
    account_type = models.ForeignKey(AccountType, on_delete=models.CASCADE)
    plate_number = models.ForeignKey(PlateNumber, on_delete=models.CASCADE)
    debit = models.DecimalField(max_digits=10, decimal_places=2)
    credit = models.DecimalField(max_digits=10, decimal_places=2)
    final_total = models.DecimalField(max_digits=10, decimal_places=2)
    reference_number = models.CharField(max_length=255)
    date = models.DateField()
    description = models.TextField()
    remarks = models.CharField(max_length=255)

    def __str__(self):
        return self.account_number

class IncomeAccount(models.Model):
    account_number = models.CharField(max_length=255)
    truck_type = models.ForeignKey(TruckType, on_delete=models.CASCADE)
    account_type = models.ForeignKey(AccountType, on_delete=models.CASCADE)
    plate_number = models.ForeignKey(PlateNumber, on_delete=models.CASCADE)
    debit = models.DecimalField(max_digits=10, decimal_places=2)
    credit = models.DecimalField(max_digits=10, decimal_places=2)
    final_total = models.DecimalField(max_digits=10, decimal_places=2)
    reference_number = models.CharField(max_length=255)
    date = models.DateField()
    driver = models.CharField(max_length=255)
    route = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    route = models.CharField(max_length=255)
    description = models.TextField()
    remarks = models.CharField(max_length=255)
    front_load = models.CharField(max_length=255)
    back_load = models.CharField(max_length=255)

    def __str__(self):
        return self.account_number

class Driver(models.Model):
    name = models.CharField(max_length=255)
    def __str__(self):
        return self.name

class Route(models.Model):
    name = models.CharField(max_length=255)
    def __str__(self):
        return self.name

class Truck(models.Model):
    plate_number = models.CharField(max_length=255)
    truck_type = models.ForeignKey(TruckType, on_delete=models.CASCADE, null=True, blank=True)
    company = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.plate_number

class LoadType(models.Model):
    name = models.CharField(max_length=255)
    def __str__(self):
        return self.name

class TruckingAccount(models.Model):
    account_number = models.CharField(max_length=255)
    account_type = models.ForeignKey(AccountType, on_delete=models.CASCADE, null=True, blank=True)
    truck = models.ForeignKey(Truck, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    debit = models.DecimalField(max_digits=15, decimal_places=2)
    credit = models.DecimalField(max_digits=15, decimal_places=2)
    final_total = models.DecimalField(max_digits=15, decimal_places=2)
    remarks = models.TextField()
    reference_number = models.CharField(max_length=255, null=True, blank=True)
    date = models.DateField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True)
    route = models.ForeignKey(Route, on_delete=models.SET_NULL, null=True, blank=True)
    front_load = models.ForeignKey(LoadType, on_delete=models.SET_NULL, null=True, blank=True,related_name='front_trucking_accounts')
    back_load = models.ForeignKey(LoadType, on_delete=models.SET_NULL, null=True, blank=True, related_name='back_trucking_accounts')
    is_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.account_number} - {self.description}"


class SalaryAccount(models.Model):
    account_number = models.CharField(max_length=255)
    truck_type = models.ForeignKey(TruckType, on_delete=models.CASCADE)
    plate_number = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField()
    debit = models.DecimalField(max_digits=15, decimal_places=2)
    credit = models.DecimalField(max_digits=15, decimal_places=2)
    final_total = models.DecimalField(max_digits=15, decimal_places=2)
    remarks = models.TextField()
    reference_number = models.CharField(max_length=255, null=True, blank=True)
    date = models.DateField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    driver = models.CharField(max_length=255, null=True, blank=True)
    route = models.CharField(max_length=255, null=True, blank=True)
    front_load = models.CharField(max_length=255, null=True, blank=True)
    back_load = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.account_number} - {self.description}"
