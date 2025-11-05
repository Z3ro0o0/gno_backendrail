from rest_framework import serializers
from .models import (
    Driver, RepairAndMaintenanceAccount, InsuranceAccount, FuelAccount, Route, TaxAccount, 
    AllowanceAccount, IncomeAccount, Truck, TruckingAccount, SalaryAccount, TruckType, AccountType, PlateNumber, LoadType
)

class TruckTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TruckType
        fields = ['id', 'name']
        read_only_fields = ['id']

class AccountTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountType
        fields = ['id', 'name']
        read_only_fields = ['id']

class PlateNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlateNumber
        fields = ['id', 'number']
        read_only_fields = ['id']

class RepairAndMaintenanceAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairAndMaintenanceAccount
        fields = [
            'id', 'account_number', 'account_type', 'truck_type', 'plate_number',
            'description', 'debit', 'credit', 'final_total', 'remarks',
            'reference_number', 'date'
        ]
        read_only_fields = ['id']

class InsuranceAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsuranceAccount
        fields = [
            'id', 'account_number', 'account_type', 'truck_type', 'plate_number',
            'description', 'debit', 'credit', 'final_total', 'remarks',
            'reference_number', 'date', 'unit_cost'
        ]
        read_only_fields = ['id']

class FuelAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuelAccount
        fields = [
            'id', 'account', 'account_type', 'truck_type', 'plate_number',
            'description', 'debit', 'credit', 'final_total', 'remarks',
            'reference_number', 'date', 'liters', 'price', 'driver', 'route',
            'front_load', 'back_load'
        ]
        read_only_fields = ['id']

class TaxAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxAccount
        fields = [
            'id', 'account_number', 'account_type', 'truck_type', 'plate_number',
            'description', 'debit', 'credit', 'final_total', 'remarks',
            'reference_number', 'date', 'price', 'quantity'
        ]
        read_only_fields = ['id']

class AllowanceAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = AllowanceAccount
        fields = [
            'id', 'account_number', 'account_type', 'truck_type', 'plate_number',
            'description', 'debit', 'credit', 'final_total', 'remarks',
            'reference_number', 'date'
        ]
        read_only_fields = ['id']

class IncomeAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncomeAccount
        fields = [
            'id', 'account_number', 'account_type', 'truck_type', 'plate_number',
            'description', 'debit', 'credit', 'final_total', 'remarks',
            'reference_number', 'date', 'driver', 'route', 'quantity', 'price',
            'front_load', 'back_load'
        ]
        read_only_fields = ['id']

class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ['id', 'name']
        read_only_fields = ['id']

class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ['id', 'name']
        read_only_fields = ['id']

class LoadTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoadType
        fields = ['id', 'name']
        read_only_fields = ['id']

class TruckSerializer(serializers.ModelSerializer):
    truck_type = TruckTypeSerializer(read_only=True)
    truck_type_id = serializers.PrimaryKeyRelatedField(queryset=TruckType.objects.all(), source='truck_type', write_only=True, required=False)
    
    class Meta:
        model = Truck
        fields = ['id', 'plate_number', 'truck_type', 'truck_type_id', 'company']
        read_only_fields = ['id']



class TruckingAccountSerializer(serializers.ModelSerializer):
    date = serializers.DateField(format='%m/%d/%Y', input_formats=['%m/%d/%Y', '%Y-%m-%d'])
    driver = DriverSerializer(read_only=True)
    route = RouteSerializer(read_only=True)
    truck = TruckSerializer(read_only=True)
    account_type = AccountTypeSerializer(read_only=True)
    account_type_id = serializers.PrimaryKeyRelatedField(queryset=AccountType.objects.all(), source='account_type', write_only=True, required=False)
    front_load = LoadTypeSerializer(read_only=True)
    front_load_id = serializers.PrimaryKeyRelatedField(queryset=LoadType.objects.all(), source='front_load', write_only=True, required=False)
    back_load = LoadTypeSerializer(read_only=True)
    back_load_id = serializers.PrimaryKeyRelatedField(queryset=LoadType.objects.all(), source='back_load', write_only=True, required=False)
    
    driver_id = serializers.PrimaryKeyRelatedField(queryset=Driver.objects.all(), source='driver', write_only=True, required=False)
    route_id = serializers.PrimaryKeyRelatedField(queryset=Route.objects.all(), source='route', write_only=True, required=False)
    truck_id = serializers.PrimaryKeyRelatedField(queryset=Truck.objects.all(), source='truck', write_only=True, required=False)
    
    class Meta:
        model = TruckingAccount
        fields = [
            'id',
            'account_number',
            'account_type',
            'account_type_id',
            'truck',
            'truck_id',
            'description',
            'debit',
            'credit',
            'final_total',
            'remarks',
            'reference_number',
            'date',
            'quantity',
            'price',
            'driver',
            'driver_id',
            'route',
            'route_id',
            'front_load',
            'front_load_id',
            'back_load',
            'back_load_id',
        ]
        read_only_fields = ['id']


class SalaryAccountSerializer(serializers.ModelSerializer):
    date = serializers.DateField(format='%m/%d/%Y', input_formats=['%m/%d/%Y', '%Y-%m-%d'])
    
    class Meta:
        model = SalaryAccount
        fields = [
            'id',
            'account_number',
            'account_type',
            'truck_type',
            'plate_number',
            'description',
            'debit',
            'credit',
            'final_total',
            'remarks',
            'reference_number',
            'date',
            'quantity',
            'price',
            'driver',
            'route',
            'front_load',
            'back_load',
        ]
        read_only_fields = ['id']
