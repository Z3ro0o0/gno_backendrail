from django.contrib import admin
from .models import (
    TruckType, AccountType, PlateNumber, 
    RepairAndMaintenanceAccount, InsuranceAccount, FuelAccount, 
    TaxAccount, AllowanceAccount, IncomeAccount, TruckingAccount,
    SalaryAccount, Truck, Driver, Route
)
# Register your models here.
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
