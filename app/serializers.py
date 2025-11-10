from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.authtoken.models import Token
import random
from datetime import timedelta

from .models import (
    Role,
    OTPCode,
    Driver, RepairAndMaintenanceAccount, InsuranceAccount, FuelAccount, Route, TaxAccount, 
    AllowanceAccount, IncomeAccount, Truck, TruckingAccount, SalaryAccount, TruckType, AccountType, PlateNumber, LoadType
)

User = get_user_model()


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'description']
        read_only_fields = ['id']


class CustomUserSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source='role', write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'role_id', 'is_active']
        read_only_fields = ['id', 'is_active']

    def update(self, instance, validated_data):
        role = validated_data.pop('role', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if role is not None:
            instance.role = role
        instance.save()
        return instance


class CustomUserCreateSerializer(serializers.ModelSerializer):
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source='role', required=False, allow_null=True
    )
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'role_id']
        read_only_fields = ['id']

    def create(self, validated_data):
        role = validated_data.pop('role', None)
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = False
        if role:
            user.role = role
        user.save()
        return user


class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        user_model = get_user_model()
        try:
            user = user_model.objects.get(email__iexact=email)
        except user_model.DoesNotExist:
            raise serializers.ValidationError({'email': 'No account is associated with this email.'})
        if not user.is_active:
            raise serializers.ValidationError({'email': 'This account is not yet activated.'})
        if not user.check_password(password):
            raise serializers.ValidationError({'password': 'Incorrect password.'})
        self.context['user'] = user
        return attrs

    def save(self, **kwargs):
        user = self.context['user']
        code = f"{random.randint(0, 999999):06d}"
        expires_at = timezone.now() + timedelta(minutes=3)
        otp = OTPCode.objects.create(user=user, code=code, expires_at=expires_at)

        from .emails import OTPEmail

        OTPEmail(otp).send()
        return otp


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs.get('email')
        code = attrs.get('code')
        user_model = get_user_model()
        try:
            user = user_model.objects.get(email__iexact=email)
        except user_model.DoesNotExist:
            raise serializers.ValidationError({'email': 'Invalid email or code.'})

        otp = (
            OTPCode.objects.filter(user=user, code=code, is_used=False)
            .order_by('-created_at')
            .first()
        )

        if otp is None:
            raise serializers.ValidationError({'code': 'Invalid or expired code.'})
        if otp.has_expired():
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            raise serializers.ValidationError({'code': 'This code has expired. Request a new one.'})

        attrs['user'] = user
        attrs['otp'] = otp
        return attrs

    def create(self, validated_data):
        user = validated_data['user']
        otp = validated_data['otp']
        otp.is_used = True
        otp.save(update_fields=['is_used'])

        token, _ = Token.objects.get_or_create(user=user)
        return token

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
    locked_at = serializers.DateTimeField(read_only=True)
    
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
            'is_locked',
            'locked_at',
        ]
        read_only_fields = ['id', 'is_locked', 'locked_at']

    def update(self, instance, validated_data):
        if instance.is_locked:
            raise serializers.ValidationError('Locked trucking accounts cannot be modified.')
        return super().update(instance, validated_data)


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
