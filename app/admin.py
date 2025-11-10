from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import (
    Role,
    OTPCode,
    TruckType, AccountType, PlateNumber, 
    RepairAndMaintenanceAccount, InsuranceAccount, FuelAccount, 
    TaxAccount, AllowanceAccount, IncomeAccount, TruckingAccount,
    SalaryAccount, Truck, Driver, Route
)

User = get_user_model()


# Register your models here.
admin.site.register(User)
admin.site.register(Role)
admin.site.register(OTPCode)
admin.site.register(TruckType)
admin.site.register(AccountType)
admin.site.register(PlateNumber)
admin.site.register(RepairAndMaintenanceAccount)
admin.site.register(InsuranceAccount)
admin.site.register(FuelAccount)
admin.site.register(TaxAccount)
admin.site.register(AllowanceAccount)
admin.site.register(IncomeAccount)
admin.site.register(TruckingAccount)
admin.site.register(SalaryAccount)
admin.site.register(Truck)
admin.site.register(Driver)
admin.site.register(Route)
