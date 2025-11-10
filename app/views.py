from django.shortcuts import render
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from django.db.models import Q, Sum, Count
from collections import defaultdict
from django.contrib.auth import get_user_model
from .models import Role, Driver, RepairAndMaintenanceAccount, InsuranceAccount, FuelAccount, Route, TaxAccount, AllowanceAccount, IncomeAccount, Truck, TruckingAccount, SalaryAccount, TruckType, AccountType, PlateNumber, LoadType
from .trucking_upload_view import TruckingAccountUploadView, TruckUploadView
from .salary_upload_view import SalaryAccountUploadView
from .serializers import (
    RoleSerializer,
    CustomUserSerializer,
    CustomUserCreateSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    DriverSerializer,
    RepairAndMaintenanceAccountSerializer,
    InsuranceAccountSerializer,
    FuelAccountSerializer,
    RouteSerializer,
    TaxAccountSerializer,
    AllowanceAccountSerializer,
    IncomeAccountSerializer,
    TruckSerializer,
    TruckingAccountSerializer,
    SalaryAccountSerializer,
    TruckTypeSerializer,
    AccountTypeSerializer,
    PlateNumberSerializer,
    LoadTypeSerializer
)
import pandas as pd
from datetime import datetime
from decimal import Decimal

User = get_user_model()


class RoleListView(ListCreateAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


class RoleDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


class OTPRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'A verification code has been sent to your email.'}, status=status.HTTP_200_OK)


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.save()
        return Response({'token': token.key}, status=status.HTTP_200_OK)


class UserListView(ListCreateAPIView):
    queryset = User.objects.all().select_related('role')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CustomUserCreateSerializer
        return CustomUserSerializer


class UserDetailView(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all().select_related('role')
    serializer_class = CustomUserSerializer


class DriverListView(ListCreateAPIView):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer


class DriverDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer


class RouteListView(ListCreateAPIView):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer


class RouteDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer


class TruckListView(ListCreateAPIView):
    queryset = Truck.objects.all()
    serializer_class = TruckSerializer


class TruckDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Truck.objects.all()
    serializer_class = TruckSerializer


# TruckType Views
class TruckTypeListView(ListCreateAPIView):
    """
    GET: List all truck types
    POST: Create a new truck type
    """
    queryset = TruckType.objects.all()
    serializer_class = TruckTypeSerializer


class TruckTypeDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific truck type
    PUT: Update a specific truck type
    PATCH: Partially update a specific truck type
    DELETE: Delete a specific truck type
    """
    queryset = TruckType.objects.all()
    serializer_class = TruckTypeSerializer


# AccountType Views
class AccountTypeListView(ListCreateAPIView):
    """
    GET: List all account types
    POST: Create a new account type
    """
    queryset = AccountType.objects.all()
    serializer_class = AccountTypeSerializer


class AccountTypeDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific account type
    PUT: Update a specific account type
    PATCH: Partially update a specific account type
    DELETE: Delete a specific account type
    """
    queryset = AccountType.objects.all()
    serializer_class = AccountTypeSerializer


# LoadType Views
class LoadTypeListView(ListCreateAPIView):
    """
    GET: List all load types
    POST: Create a new load type
    """
    queryset = LoadType.objects.all()
    serializer_class = LoadTypeSerializer


class LoadTypeDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific load type
    PUT: Update a specific load type
    PATCH: Partially update a specific load type
    DELETE: Delete a specific load type
    """
    queryset = LoadType.objects.all()
    serializer_class = LoadTypeSerializer


# PlateNumber Views
class PlateNumberListView(ListCreateAPIView):
    """
    GET: List all plate numbers
    POST: Create a new plate number
    """
    queryset = PlateNumber.objects.all()
    serializer_class = PlateNumberSerializer


class PlateNumberDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific plate number
    PUT: Update a specific plate number
    PATCH: Partially update a specific plate number
    DELETE: Delete a specific plate number
    """
    queryset = PlateNumber.objects.all()
    serializer_class = PlateNumberSerializer


# RepairAndMaintenanceAccount Views
class RepairAndMaintenanceAccountListView(ListCreateAPIView):
    """
    GET: List all repair and maintenance accounts
    POST: Create a new repair and maintenance account
    """
    queryset = RepairAndMaintenanceAccount.objects.all()
    serializer_class = RepairAndMaintenanceAccountSerializer


class RepairAndMaintenanceAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific repair and maintenance account
    PUT: Update a specific repair and maintenance account
    PATCH: Partially update a specific repair and maintenance account
    DELETE: Delete a specific repair and maintenance account
    """
    queryset = RepairAndMaintenanceAccount.objects.all()
    serializer_class = RepairAndMaintenanceAccountSerializer


class RepairAndMaintenanceUploadView(APIView):
    """
    POST: Upload Excel file and bulk create repair and maintenance accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create RepairAndMaintenanceAccount
                    RepairAndMaintenanceAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=clean_decimal(row.get('Final Total', row.get('final_total', 0))),
                        reference_number=str(row.get('Reference Number', row.get('reference_number', ''))),
                        date=date_obj,
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer

    def perform_destroy(self, instance):
        if instance.is_locked:
            raise ValidationError('Locked trucking accounts cannot be deleted.')
        instance.delete()

    def perform_destroy(self, instance):
        if instance.is_locked:
            raise ValidationError('Locked trucking accounts cannot be deleted.')
        instance.delete()

    def perform_destroy(self, instance):
        if instance.is_locked:
            raise ValidationError('Locked trucking accounts cannot be deleted.')
        instance.delete()


class IncomeAccountListView(ListCreateAPIView):
    """
    GET: List all income accounts
    POST: Create a new income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific income account
    PUT: Update a specific income account
    PATCH: Partially update a specific income account
    DELETE: Delete a specific income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create income accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create IncomeAccount
                    IncomeAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        driver=str(row.get('Driver', row.get('driver', ''))),
                        route=str(row.get('Route', row.get('route', ''))),
                        quantity=clean_decimal(row.get('Quantity', row.get('quantity', 0))),
                        price=clean_decimal(row.get('Price', row.get('price', 0))),
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', ''))),
                        front_load=str(row.get('Front_Loa', row.get('front_load', ''))),
                        back_load=str(row.get('Back_Load', row.get('back_load', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TaxAccountListView(ListCreateAPIView):
    """
    GET: List all tax accounts
    POST: Create a new tax account
    """
    queryset = TaxAccount.objects.all()
    serializer_class = TaxAccountSerializer


class TaxAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific tax account
    PUT: Update a specific tax account
    PATCH: Partially update a specific tax account
    DELETE: Delete a specific tax account
    """
    queryset = TaxAccount.objects.all()
    serializer_class = TaxAccountSerializer


class TaxAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create tax accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create TaxAccount
                    TaxAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', ''))),
                        price=clean_decimal(row.get('Price', row.get('price', 0))),
                        quantity=clean_decimal(row.get('Quantity', row.get('quantity', 0)))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class AllowanceAccountListView(ListCreateAPIView):
    """
    GET: List all allowance accounts
    POST: Create a new allowance account
    """
    queryset = AllowanceAccount.objects.all()
    serializer_class = AllowanceAccountSerializer


class AllowanceAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific allowance account
    PUT: Update a specific allowance account
    PATCH: Partially update a specific allowance account
    DELETE: Delete a specific allowance account
    """
    queryset = AllowanceAccount.objects.all()
    serializer_class = AllowanceAccountSerializer


class AllowanceAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create allowance accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create AllowanceAccount
                    AllowanceAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class IncomeAccountListView(ListCreateAPIView):
    """
    GET: List all income accounts
    POST: Create a new income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific income account
    PUT: Update a specific income account
    PATCH: Partially update a specific income account
    DELETE: Delete a specific income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create income accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create IncomeAccount
                    IncomeAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        driver=str(row.get('Driver', row.get('driver', ''))),
                        route=str(row.get('Route', row.get('route', ''))),
                        quantity=clean_decimal(row.get('Quantity', row.get('quantity', 0))),
                        price=clean_decimal(row.get('Price', row.get('price', 0))),
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', ''))),
                        front_load=str(row.get('Front_Loa', row.get('front_load', ''))),
                        back_load=str(row.get('Back_Load', row.get('back_load', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class InsuranceAccountListView(ListCreateAPIView):
    """
    GET: List all insurance accounts
    POST: Create a new insurance account
    """
    queryset = InsuranceAccount.objects.all()
    serializer_class = InsuranceAccountSerializer


class InsuranceAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific insurance account
    PUT: Update a specific insurance account
    PATCH: Partially update a specific insurance account
    DELETE: Delete a specific insurance account
    """
    queryset = InsuranceAccount.objects.all()
    serializer_class = InsuranceAccountSerializer


class InsuranceAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create insurance accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create InsuranceAccount
                    InsuranceAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class IncomeAccountListView(ListCreateAPIView):
    """
    GET: List all income accounts
    POST: Create a new income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific income account
    PUT: Update a specific income account
    PATCH: Partially update a specific income account
    DELETE: Delete a specific income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create income accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create IncomeAccount
                    IncomeAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        driver=str(row.get('Driver', row.get('driver', ''))),
                        route=str(row.get('Route', row.get('route', ''))),
                        quantity=clean_decimal(row.get('Quantity', row.get('quantity', 0))),
                        price=clean_decimal(row.get('Price', row.get('price', 0))),
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', ''))),
                        front_load=str(row.get('Front_Loa', row.get('front_load', ''))),
                        back_load=str(row.get('Back_Load', row.get('back_load', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class AllowanceAccountListView(ListCreateAPIView):
    """
    GET: List all allowance accounts
    POST: Create a new allowance account
    """
    queryset = AllowanceAccount.objects.all()
    serializer_class = AllowanceAccountSerializer


class AllowanceAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific allowance account
    PUT: Update a specific allowance account
    PATCH: Partially update a specific allowance account
    DELETE: Delete a specific allowance account
    """
    queryset = AllowanceAccount.objects.all()
    serializer_class = AllowanceAccountSerializer


class AllowanceAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create allowance accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create AllowanceAccount
                    AllowanceAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class FuelAccountListView(ListCreateAPIView):
    """
    GET: List all fuel accounts
    POST: Create a new fuel account
    """
    queryset = FuelAccount.objects.all()
    serializer_class = FuelAccountSerializer


class FuelAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific fuel account
    PUT: Update a specific fuel account
    PATCH: Partially update a specific fuel account
    DELETE: Delete a specific fuel account
    """
    queryset = FuelAccount.objects.all()
    serializer_class = FuelAccountSerializer


class FuelAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create fuel accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'Account' in df.columns:
                    df['Account'] = df['Account'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('Account', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create FuelAccount
                    FuelAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        driver=str(row.get('Driver', row.get('driver', ''))),
                        route=str(row.get('Route', row.get('route', ''))),
                        liters=clean_decimal(row.get('Liters', row.get('liters', 0))),
                        price=clean_decimal(row.get('Price', row.get('price', 0))),
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', ''))),
                        front_load=str(row.get('Front_Loa', row.get('front_load', ''))),
                        back_load=str(row.get('Back_Load', row.get('back_load', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class IncomeAccountListView(ListCreateAPIView):
    """
    GET: List all income accounts
    POST: Create a new income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific income account
    PUT: Update a specific income account
    PATCH: Partially update a specific income account
    DELETE: Delete a specific income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create income accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create IncomeAccount
                    IncomeAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        driver=str(row.get('Driver', row.get('driver', ''))),
                        route=str(row.get('Route', row.get('route', ''))),
                        quantity=clean_decimal(row.get('Quantity', row.get('quantity', 0))),
                        price=clean_decimal(row.get('Price', row.get('price', 0))),
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', ''))),
                        front_load=str(row.get('Front_Loa', row.get('front_load', ''))),
                        back_load=str(row.get('Back_Load', row.get('back_load', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TaxAccountListView(ListCreateAPIView):
    """
    GET: List all tax accounts
    POST: Create a new tax account
    """
    queryset = TaxAccount.objects.all()
    serializer_class = TaxAccountSerializer


class TaxAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific tax account
    PUT: Update a specific tax account
    PATCH: Partially update a specific tax account
    DELETE: Delete a specific tax account
    """
    queryset = TaxAccount.objects.all()
    serializer_class = TaxAccountSerializer


class TaxAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create tax accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create TaxAccount
                    TaxAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', ''))),
                        price=clean_decimal(row.get('Price', row.get('price', 0))),
                        quantity=clean_decimal(row.get('Quantity', row.get('quantity', 0)))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class IncomeAccountListView(ListCreateAPIView):
    """
    GET: List all income accounts
    POST: Create a new income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific income account
    PUT: Update a specific income account
    PATCH: Partially update a specific income account
    DELETE: Delete a specific income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create income accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create IncomeAccount
                    IncomeAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        driver=str(row.get('Driver', row.get('driver', ''))),
                        route=str(row.get('Route', row.get('route', ''))),
                        quantity=clean_decimal(row.get('Quantity', row.get('quantity', 0))),
                        price=clean_decimal(row.get('Price', row.get('price', 0))),
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', ''))),
                        front_load=str(row.get('Front_Loa', row.get('front_load', ''))),
                        back_load=str(row.get('Back_Load', row.get('back_load', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class AllowanceAccountListView(ListCreateAPIView):
    """
    GET: List all allowance accounts
    POST: Create a new allowance account
    """
    queryset = AllowanceAccount.objects.all()
    serializer_class = AllowanceAccountSerializer


class AllowanceAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific allowance account
    PUT: Update a specific allowance account
    PATCH: Partially update a specific allowance account
    DELETE: Delete a specific allowance account
    """
    queryset = AllowanceAccount.objects.all()
    serializer_class = AllowanceAccountSerializer


class AllowanceAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create allowance accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create AllowanceAccount
                    AllowanceAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class IncomeAccountListView(ListCreateAPIView):
    """
    GET: List all income accounts
    POST: Create a new income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific income account
    PUT: Update a specific income account
    PATCH: Partially update a specific income account
    DELETE: Delete a specific income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create income accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create IncomeAccount
                    IncomeAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        driver=str(row.get('Driver', row.get('driver', ''))),
                        route=str(row.get('Route', row.get('route', ''))),
                        quantity=clean_decimal(row.get('Quantity', row.get('quantity', 0))),
                        price=clean_decimal(row.get('Price', row.get('price', 0))),
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', ''))),
                        front_load=str(row.get('Front_Loa', row.get('front_load', ''))),
                        back_load=str(row.get('Back_Load', row.get('back_load', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class AllowanceAccountListView(ListCreateAPIView):
    """
    GET: List all allowance accounts
    POST: Create a new allowance account
    """
    queryset = AllowanceAccount.objects.all()
    serializer_class = AllowanceAccountSerializer


class AllowanceAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific allowance account
    PUT: Update a specific allowance account
    PATCH: Partially update a specific allowance account
    DELETE: Delete a specific allowance account
    """
    queryset = AllowanceAccount.objects.all()
    serializer_class = AllowanceAccountSerializer


class AllowanceAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create allowance accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create AllowanceAccount
                    AllowanceAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class IncomeAccountListView(ListCreateAPIView):
    """
    GET: List all income accounts
    POST: Create a new income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific income account
    PUT: Update a specific income account
    PATCH: Partially update a specific income account
    DELETE: Delete a specific income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create income accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create IncomeAccount
                    IncomeAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        driver=str(row.get('Driver', row.get('driver', ''))),
                        route=str(row.get('Route', row.get('route', ''))),
                        quantity=clean_decimal(row.get('Quantity', row.get('quantity', 0))),
                        price=clean_decimal(row.get('Price', row.get('price', 0))),
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', ''))),
                        front_load=str(row.get('Front_Loa', row.get('front_load', ''))),
                        back_load=str(row.get('Back_Load', row.get('back_load', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class FuelAccountListView(ListCreateAPIView):
    """
    GET: List all fuel accounts
    POST: Create a new fuel account
    """
    queryset = FuelAccount.objects.all()
    serializer_class = FuelAccountSerializer


class FuelAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific fuel account
    PUT: Update a specific fuel account
    PATCH: Partially update a specific fuel account
    DELETE: Delete a specific fuel account
    """
    queryset = FuelAccount.objects.all()
    serializer_class = FuelAccountSerializer


class FuelAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create fuel accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'Account' in df.columns:
                    df['Account'] = df['Account'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('Account', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create FuelAccount
                    FuelAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        driver=str(row.get('Driver', row.get('driver', ''))),
                        route=str(row.get('Route', row.get('route', ''))),
                        liters=clean_decimal(row.get('Liters', row.get('liters', 0))),
                        price=clean_decimal(row.get('Price', row.get('price', 0))),
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', ''))),
                        front_load=str(row.get('Front_Loa', row.get('front_load', ''))),
                        back_load=str(row.get('Back_Load', row.get('back_load', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class IncomeAccountListView(ListCreateAPIView):
    """
    GET: List all income accounts
    POST: Create a new income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific income account
    PUT: Update a specific income account
    PATCH: Partially update a specific income account
    DELETE: Delete a specific income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create income accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create IncomeAccount
                    IncomeAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        driver=str(row.get('Driver', row.get('driver', ''))),
                        route=str(row.get('Route', row.get('route', ''))),
                        quantity=clean_decimal(row.get('Quantity', row.get('quantity', 0))),
                        price=clean_decimal(row.get('Price', row.get('price', 0))),
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', ''))),
                        front_load=str(row.get('Front_Loa', row.get('front_load', ''))),
                        back_load=str(row.get('Back_Load', row.get('back_load', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class AllowanceAccountListView(ListCreateAPIView):
    """
    GET: List all allowance accounts
    POST: Create a new allowance account
    """
    queryset = AllowanceAccount.objects.all()
    serializer_class = AllowanceAccountSerializer


class AllowanceAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific allowance account
    PUT: Update a specific allowance account
    PATCH: Partially update a specific allowance account
    DELETE: Delete a specific allowance account
    """
    queryset = AllowanceAccount.objects.all()
    serializer_class = AllowanceAccountSerializer


class AllowanceAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create allowance accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create AllowanceAccount
                    AllowanceAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class IncomeAccountListView(ListCreateAPIView):
    """
    GET: List all income accounts
    POST: Create a new income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific income account
    PUT: Update a specific income account
    PATCH: Partially update a specific income account
    DELETE: Delete a specific income account
    """
    queryset = IncomeAccount.objects.all()
    serializer_class = IncomeAccountSerializer


class IncomeAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create income accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create IncomeAccount
                    IncomeAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        driver=str(row.get('Driver', row.get('driver', ''))),
                        route=str(row.get('Route', row.get('route', ''))),
                        quantity=clean_decimal(row.get('Quantity', row.get('quantity', 0))),
                        price=clean_decimal(row.get('Price', row.get('price', 0))),
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', ''))),
                        front_load=str(row.get('Front_Loa', row.get('front_load', ''))),
                        back_load=str(row.get('Back_Load', row.get('back_load', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TruckingAccount Views
class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts
    POST: Create a new trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class AllowanceAccountListView(ListCreateAPIView):
    """
    GET: List all allowance accounts
    POST: Create a new allowance account
    """
    queryset = AllowanceAccount.objects.all()
    serializer_class = AllowanceAccountSerializer


class AllowanceAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific allowance account
    PUT: Update a specific allowance account
    PATCH: Partially update a specific allowance account
    DELETE: Delete a specific allowance account
    """
    queryset = AllowanceAccount.objects.all()
    serializer_class = AllowanceAccountSerializer


class AllowanceAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create allowance accounts
    """
    def post(self, request):
        try:
            # Check if file is present
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return Response(
                    {'error': 'File must be an Excel file (.xlsx or .xls)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
                print(f"Excel file loaded successfully. Shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                # Convert account number column to string to avoid decimal places
                if 'AccountNumber' in df.columns:
                    df['AccountNumber'] = df['AccountNumber'].astype(str).str.replace('.0', '', regex=False)
                elif 'account_number' in df.columns:
                    df['account_number'] = df['account_number'].astype(str).str.replace('.0', '', regex=False)
                    
            except Exception as e:
                return Response(
                    {'error': f'Failed to read Excel file: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track results
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    print(f"Processing row {index + 1}: {dict(row)}")
                    # Get or create TruckType (handle both column name formats)
                    truck_type_name = str(row.get('TruckType', row.get('truck_type', ''))).strip()
                    if truck_type_name:
                        truck_type, _ = TruckType.objects.get_or_create(name=truck_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing TruckType")
                        error_count += 1
                        continue
                    
                    # Get or create AccountType
                    account_type_name = str(row.get('AccountType', row.get('account_type', ''))).strip()
                    if account_type_name:
                        account_type, _ = AccountType.objects.get_or_create(name=account_type_name)
                    else:
                        errors.append(f"Row {index + 2}: Missing AccountType")
                        error_count += 1
                        continue
                    
                    # Get or create PlateNumber
                    plate_number_value = str(row.get('PlateNumber', row.get('plate_number', ''))).strip()
                    if plate_number_value:
                        plate_number, _ = PlateNumber.objects.get_or_create(number=plate_number_value)
                    else:
                        errors.append(f"Row {index + 2}: Missing PlateNumber")
                        error_count += 1
                        continue
                    
                    # Parse date (handle both column name formats)
                    date_value = row.get('Date', row.get('date'))
                    if pd.notna(date_value):
                        if isinstance(date_value, str):
                            try:
                                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                            except ValueError:
                                # Try other common date formats
                                try:
                                    date_obj = datetime.strptime(date_value, '%m/%d/%Y').date()
                                except ValueError:
                                    date_obj = pd.to_datetime(date_value).date()
                        else:
                            date_obj = pd.to_datetime(date_value).date()
                    else:
                        errors.append(f"Row {index + 2}: Missing or invalid Date")
                        error_count += 1
                        continue
                    
                    # Clean and parse numeric values
                    def clean_decimal(value):
                        if pd.isna(value) or value == '' or str(value).strip() == '':
                            return Decimal('0')
                        # Remove commas and convert to string
                        cleaned = str(value).replace(',', '').strip()
                        if cleaned == '' or cleaned.lower() in ['nan', 'null', 'none']:
                            return Decimal('0')
                        try:
                            return Decimal(cleaned)
                        except:
                            return Decimal('0')
                    
                    # Clean account number (remove .0 if present)
                    account_number = str(row.get('AccountNumber', row.get('account_number', ''))).replace('.0', '')
                    
                    # Create AllowanceAccount
                    AllowanceAccount.objects.create(
                        account_number=account_number,
                        truck_type=truck_type,
                        account_type=account_type,
                        plate_number=plate_number,
                        debit=clean_decimal(row.get('Debit', row.get('debit', 0))),
                        credit=clean_decimal(row.get('Credit', row.get('credit', 0))),
                        final_total=-clean_decimal(row.get('FinalTotal', row.get('final_total', 0))),
                        reference_number=str(row.get('ReferenceNumber', row.get('reference_number', ''))),
                        date=date_obj,
                        description=str(row.get('Description', row.get('description', ''))),
                        remarks=str(row.get('Remarks', row.get('remarks', '')))
                    )
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return Response({
                'message': 'Upload completed',
                'created': created_count,
                'errors': error_count,
                'error_details': errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DriversSummaryView(APIView):
    """
    GET: Get drivers summary with front_load, back_load, and allowance amounts
    """
    def get(self, request):
        try:
            drivers_data = {}
            
            # Process IncomeAccount (for front_load and back_load)
            income_accounts = IncomeAccount.objects.all().order_by('reference_number', 'account_number', 'date', 'id')
            
            # Group by reference_number, account_number, and date
            grouped_income = defaultdict(list)
            for account in income_accounts:
                key = (account.reference_number, account.account_number, account.date)
                grouped_income[key].append(account)
            
            for key, accounts in grouped_income.items():
                reference_number, account_number, date = key
                
                # Sort by ID to ensure consistent ordering
                accounts.sort(key=lambda x: x.id)
                
                # Check if there's only 1 entry for this combination
                if len(accounts) == 1:
                    # Split the single entry equally between front_load and back_load
                    account = accounts[0]
                    
                    # Skip if no route
                    if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                        continue
                    
                    driver = account.driver
                    half_amount = float(account.final_total) / 2
                    
                    if driver not in drivers_data:
                        drivers_data[driver] = {
                            'driver_name': driver,
                            'front_load_amount': 0,
                            'back_load_amount': 0,
                            'allowance_amount': 0,
                            'total_loads': 0,
                            'details': []
                        }
                    
                    # Add half to front_load and half to back_load
                    drivers_data[driver]['front_load_amount'] += half_amount
                    drivers_data[driver]['back_load_amount'] += half_amount
                    drivers_data[driver]['total_loads'] += 1
                    
                    # Add details for both front and back load
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'front_load',
                        'route': account.route,
                        'description': account.description
                    })
                    drivers_data[driver]['details'].append({
                        'reference_number': reference_number,
                        'account_number': account_number,
                        'date': date.strftime('%Y-%m-%d'),
                        'amount': half_amount,
                        'load_type': 'back_load',
                        'route': account.route,
                        'description': account.description
                    })
                else:
                    # Multiple entries - use original logic
                    for i, account in enumerate(accounts):
                        # Skip if no route
                        if not account.route or str(account.route).strip() == '' or str(account.route).lower() == 'nan':
                            continue
                        
                        driver = account.driver
                        if driver not in drivers_data:
                            drivers_data[driver] = {
                                'driver_name': driver,
                                'front_load_amount': 0,
                                'back_load_amount': 0,
                                'allowance_amount': 0,
                                'total_loads': 0,
                                'details': []
                            }
                        
                        # First occurrence is front_load, subsequent are back_load
                        if i == 0:
                            load_type = 'front_load'
                            drivers_data[driver]['front_load_amount'] += float(account.final_total)
                        else:
                            load_type = 'back_load'
                            drivers_data[driver]['back_load_amount'] += float(account.final_total)
                        
                        drivers_data[driver]['total_loads'] += 1
                        drivers_data[driver]['details'].append({
                            'reference_number': reference_number,
                            'account_number': account_number,
                            'date': date.strftime('%Y-%m-%d'),
                            'amount': float(account.final_total),
                            'load_type': load_type,
                            'route': account.route,
                            'description': account.description
                        })
            
            # Process AllowanceAccount (for allowances)
            # Match allowance accounts with income accounts by date and plate number to get driver name
            allowance_accounts = AllowanceAccount.objects.all()
            for allowance in allowance_accounts:
                # Find matching income account by date and plate number to get driver name
                matching_income = IncomeAccount.objects.filter(
                    date=allowance.date,
                    plate_number=allowance.plate_number
                ).first()
                
                if matching_income:
                    driver = matching_income.driver
                else:
                    # Fallback: try to get driver from allowance if it exists
                    driver = allowance.driver if hasattr(allowance, 'driver') else 'Unknown'
                
                if driver not in drivers_data:
                    drivers_data[driver] = {
                        'driver_name': driver,
                        'front_load_amount': 0,
                        'back_load_amount': 0,
                        'allowance_amount': 0,
                        'total_loads': 0,
                        'details': []
                    }
                
                drivers_data[driver]['allowance_amount'] += float(allowance.final_total)
            
            # Convert to list, filter out drivers with no front_load or back_load, and sort by driver name
            result = [
                driver for driver in drivers_data.values() 
                if driver['front_load_amount'] > 0 or driver['back_load_amount'] > 0
            ]
            result.sort(key=lambda x: x['driver_name'])

            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['front_load_amount'] for d in result),
                    'total_back_load': sum(d['back_load_amount'] for d in result),
                    'total_allowance': sum(d['allowance_amount'] for d in result),
                    'total_loads': sum(d['total_loads'] for d in result)
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )