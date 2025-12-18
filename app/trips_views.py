from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from collections import defaultdict
import re
from datetime import datetime
from .models import (
    RepairAndMaintenanceAccount, 
    InsuranceAccount, 
    FuelAccount, 
    TaxAccount, 
    AllowanceAccount, 
    IncomeAccount,
    TruckingAccount,
    Driver,
    Route,
    LoadType
)


def parse_remarks(remarks):
    """
    Parse remarks to extract driver, route, front_load, and back_load
    Format: "LRO: 140Liters Fuel and Oil NGS-4359 Francis Ariglado:PAG-ILIGAN: Strike/Cement:"
    """
    if not remarks:
        return None, None, None, None
    
    # Known drivers list
    drivers = [
        'Edgardo Agapay', 'Romel Bantilan', 'Reynaldo Rizalda', 'Francis Ariglado',
        'Roque Oling', 'Pablo Hamo', 'Albert Saavedra', 'Jimmy Oclarit', 'Nicanor',
        'Arnel Duhilag', 'Benjamin Aloso', 'Roger', 'Joseph Bahan', 'Doming'
    ]
    
    # Known routes list
    routes = [
        'PAG-CDO', 'PAG-ILIGAN', 'Strike Holcim', 'PAG-ILIGAN STRIKE', 'PAG-CDO (CARGILL)',
        'PAG-CDO STRIKE', 'PAG-BUK', 'PAG-DIPLAHAN', 'PAG-MARANDING', 'PAG-COTABATO',
        'PAG-ZMBGA', 'Pag-COTABATO', 'Pag-AURORA', 'PAG-DIPOLOG', 'PAG-MOLAVE',
        'PAGADIAN', 'PAG-DIMATALING', 'PAG-DINAS', 'PAG-LABANGAN', 'PAG-MIDSALIP',
        'PAGADIAN', 'PAG-OZAMIS', 'PAG-OSMENIA', 'PAG-DUMINGAG', 'PAG-KUMALARANG',
        'PAG-MAHAYAG', 'PAG-TAMBULIG', 'PAG-SURIGAO', 'PAG-BUYOGAN', 'PAG-SAN PABLO',
        'PAGADIAN-OPEX', 'CDO-OPEX', 'PAG-BAYOG', 'PAG-LAKEWOOD', 'PAG-BUUG'
    ]
    
    driver = None
    route = None
    front_load = None
    back_load = None
    
    # Find driver
    for known_driver in drivers:
        if known_driver in remarks:
            driver = known_driver
            break
    
    # Find route
    for known_route in routes:
        if known_route in remarks:
            route = known_route
            break
    
    # Find front_load/back_load pattern (format: "value/value")
    load_pattern = r'([^:]+)/([^:]+):'
    load_match = re.search(load_pattern, remarks)
    if load_match:
        front_load = load_match.group(1).strip()
        back_load = load_match.group(2).strip()
    
    return driver, route, front_load, back_load


class TripsView(APIView):
    """
    GET: Get consolidated trips data grouped by plate number and date
    """
    
    def get(self, request):
        try:
            # Dictionary to store trips grouped by (plate_number, date)
            trips = defaultdict(lambda: {
                'account_number': '',
                'plate_number': '',
                'date': '',
                'trip_route': '',
                'driver': '',
                'allowance': 0,
                'reference_number': '',
                'fuel_liters': 0,
                'fuel_price': 0,
                'front_load': '',
                'front_load_reference_number': '',
                'front_load_amount': 0,
                'back_load_reference_number': '',
                'back_load_amount': 0,
                'front_and_back_load_amount': 0,
                'remarks': '',
                'insurance_expense': 0,
                'repairs_maintenance_expense': 0,
                'taxes_permits_licenses_expense': 0,
                'salaries_allowance': 0
            })
            
            # Process Income Accounts for front_load and back_load
            income_accounts = IncomeAccount.objects.select_related('plate_number').all()
            
            # Group income by plate, date, and reference number
            income_grouped = defaultdict(list)
            for account in income_accounts:
                key = (account.plate_number.number, account.date, account.reference_number)
                income_grouped[key].append(account)
            
            # Process each income group
            for (plate_num, date, ref_num), accounts in income_grouped.items():
                trip_key = (plate_num, date)
                
                if len(accounts) == 1:
                    # Single entry - check if front_load has value
                    account = accounts[0]
                    front_load_value = str(account.front_load).strip().lower()
                    back_load_value = str(account.back_load).strip().lower()
                    
                    trips[trip_key]['account_number'] = account.account_number
                    trips[trip_key]['plate_number'] = plate_num
                    trips[trip_key]['date'] = date.strftime('%Y-%m-%d')
                    trips[trip_key]['trip_route'] = account.route
                    trips[trip_key]['driver'] = account.driver
                    trips[trip_key]['reference_number'] = ref_num
                    
                    # Set front_load name from income record if not already set
                    if not trips[trip_key]['front_load'] and account.front_load:
                        trips[trip_key]['front_load'] = str(account.front_load)
                    
                    trips[trip_key]['remarks'] = account.remarks
                    
                    # Check if front_load has a meaningful value (not empty, 'n', 'nan', etc.)
                    if (front_load_value and front_load_value != '' and 
                        front_load_value not in ['n', 'nan', 'none', '0'] and
                        back_load_value and back_load_value != '' and 
                        back_load_value not in ['nan', 'none', '0']):
                        # Both front_load and back_load have meaningful values - divide by 2
                        half_amount = float(account.final_total) / 2
                        trips[trip_key]['front_load_amount'] += half_amount
                        trips[trip_key]['back_load_amount'] += half_amount
                        trips[trip_key]['front_load_reference_number'] = ref_num
                        trips[trip_key]['back_load_reference_number'] = ref_num
                    elif (back_load_value and back_load_value != '' and 
                          back_load_value not in ['nan', 'none', '0']):
                        # Only back_load has value - all goes to back_load, front_load = 0
                        trips[trip_key]['front_load_amount'] = 0  # Explicitly set to 0
                        trips[trip_key]['back_load_amount'] += float(account.final_total)
                        trips[trip_key]['back_load_reference_number'] = ref_num
                    elif (front_load_value and front_load_value != '' and 
                          front_load_value not in ['n', 'nan', 'none', '0']):
                        # Only front_load has value - all goes to front_load, back_load = 0
                        trips[trip_key]['front_load_amount'] += float(account.final_total)
                        trips[trip_key]['back_load_amount'] = 0  # Explicitly set to 0
                        trips[trip_key]['front_load_reference_number'] = ref_num
                    else:
                        # Neither has meaningful value - still keep the names if they exist
                        pass
                else:
                    # Multiple entries - first is front_load, rest are back_load
                    for i, account in enumerate(accounts):
                        trips[trip_key]['account_number'] = account.account_number
                        trips[trip_key]['plate_number'] = plate_num
                        trips[trip_key]['date'] = date.strftime('%Y-%m-%d')
                        trips[trip_key]['trip_route'] = account.route
                        trips[trip_key]['driver'] = account.driver
                        
                        if not trips[trip_key]['front_load'] and account.front_load:
                            trips[trip_key]['front_load'] = str(account.front_load)
                            
                        trips[trip_key]['remarks'] = account.remarks
                        
                        if i == 0:
                            # First entry is front_load
                            trips[trip_key]['front_load_amount'] += float(account.final_total)
                            trips[trip_key]['front_load_reference_number'] = ref_num
                        else:
                            # Subsequent entries are back_load
                            trips[trip_key]['back_load_amount'] += float(account.final_total)
                            trips[trip_key]['back_load_reference_number'] = ref_num
            
            # Process Fuel Accounts
            fuel_accounts = FuelAccount.objects.select_related('plate_number', 'front_load', 'back_load').all()
            for account in fuel_accounts:
                trip_key = (account.plate_number.number, account.date)
                if trip_key in trips or not trips[trip_key]['plate_number']:
                    trips[trip_key]['plate_number'] = account.plate_number.number
                    trips[trip_key]['date'] = account.date.strftime('%Y-%m-%d')
                    trips[trip_key]['fuel_liters'] += float(account.liters or 0)
                    trips[trip_key]['fuel_price'] = float(account.price or 0)
                    if not trips[trip_key]['driver']:
                        trips[trip_key]['driver'] = account.driver
                    if not trips[trip_key]['trip_route']:
                        trips[trip_key]['trip_route'] = account.route
                    if not trips[trip_key]['front_load'] and account.front_load:
                        trips[trip_key]['front_load'] = str(account.front_load)
            
            # Process Allowance Accounts
            allowance_accounts = AllowanceAccount.objects.select_related('plate_number').all()
            for account in allowance_accounts:
                trip_key = (account.plate_number.number, account.date)
                if trip_key in trips or not trips[trip_key]['plate_number']:
                    trips[trip_key]['plate_number'] = account.plate_number.number
                    trips[trip_key]['date'] = account.date.strftime('%Y-%m-%d')
                    trips[trip_key]['allowance'] += float(account.final_total)
                    trips[trip_key]['salaries_allowance'] += float(account.final_total)
            
            # Process Insurance Accounts
            insurance_accounts = InsuranceAccount.objects.select_related('plate_number').all()
            for account in insurance_accounts:
                trip_key = (account.plate_number.number, account.date)
                if trip_key in trips or not trips[trip_key]['plate_number']:
                    trips[trip_key]['plate_number'] = account.plate_number.number
                    trips[trip_key]['date'] = account.date.strftime('%Y-%m-%d')
                    trips[trip_key]['insurance_expense'] += float(account.final_total)
            
            # Process Repair and Maintenance Accounts
            repair_accounts = RepairAndMaintenanceAccount.objects.select_related('plate_number').all()
            for account in repair_accounts:
                trip_key = (account.plate_number.number, account.date)
                if trip_key in trips or not trips[trip_key]['plate_number']:
                    trips[trip_key]['plate_number'] = account.plate_number.number
                    trips[trip_key]['date'] = account.date.strftime('%Y-%m-%d')
                    trips[trip_key]['repairs_maintenance_expense'] += float(account.final_total)
            
            # Process Tax Accounts
            tax_accounts = TaxAccount.objects.select_related('plate_number').all()
            for account in tax_accounts:
                trip_key = (account.plate_number.number, account.date)
                if trip_key in trips or not trips[trip_key]['plate_number']:
                    trips[trip_key]['plate_number'] = account.plate_number.number
                    trips[trip_key]['date'] = account.date.strftime('%Y-%m-%d')
                    trips[trip_key]['taxes_permits_licenses_expense'] += float(account.final_total)
            
            # Also process TruckingAccount for any missing metadata (like front_load set via modal)
            trucking_accounts = TruckingAccount.objects.filter(is_locked=False).select_related('truck', 'front_load', 'back_load').all()
            for account in trucking_accounts:
                if not account.truck or not account.truck.plate_number:
                    continue
                trip_key = (account.truck.plate_number, account.date)
                if trip_key in trips:
                    if not trips[trip_key]['front_load'] and account.front_load:
                        trips[trip_key]['front_load'] = str(account.front_load.name)
            
            # Calculate front_and_back_load_amount for each trip
            # Include all trips (route is optional - can be set later)
            trips_list = []
            for trip_data in trips.values():
                # Skip trips with 'nan' as route, but allow empty routes
                route = str(trip_data.get('trip_route', '')).strip().lower()
                if route == 'nan':
                    trip_data['trip_route'] = ''  # Set to empty string instead of skipping
                    
                trip_data['front_and_back_load_amount'] = (
                    trip_data['front_load_amount'] + trip_data['back_load_amount']
                )
                trips_list.append(trip_data)
            
            # Sort by date and plate number
            trips_list.sort(key=lambda x: (x['date'], x['plate_number']))
            
            # Return array directly as frontend expects an array
            return Response(trips_list, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch trips data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdateTripFieldView(APIView):
    """
    POST: Update trip_route, driver, front_load, or back_load for all TruckingAccount records
    matching the plate_number and date
    """
    
    def post(self, request):
        try:
            plate_number = request.data.get('plate_number')
            date_str = request.data.get('date')
            field = request.data.get('field')  # 'trip_route', 'driver', 'front_load', 'back_load'
            value = request.data.get('value')  # String value to set
            
            if not all([plate_number, date_str, field]):
                return Response(
                    {'error': 'Missing required fields: plate_number, date, field'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate field
            valid_fields = ['trip_route', 'driver', 'front_load', 'back_load']
            if field not in valid_fields:
                return Response(
                    {'error': f'Invalid field. Must be one of: {", ".join(valid_fields)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Parse date
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Standardize plate number for matching
            def standardize_plate(plate):
                if not plate:
                    return ''
                return str(plate).replace(' ', '').replace('-', '').upper()
            
            standardized_plate = standardize_plate(plate_number)
            
            # Get all TruckingAccount records matching the plate number and date
            matching_accounts = TruckingAccount.objects.filter(date=date_obj).select_related('truck')
            
            # Filter by plate number
            accounts_to_update = []
            locked_accounts = []
            for account in matching_accounts:
                account_plate = None
                if account.truck and account.truck.plate_number:
                    account_plate = account.truck.plate_number
                
                if account_plate and standardize_plate(account_plate) == standardized_plate:
                    if account.is_locked:
                        locked_accounts.append(account.id)
                    else:
                        accounts_to_update.append(account)
            
            if locked_accounts:
                return Response(
                    {
                        'error': 'Some trucking accounts for the selected trip are locked and cannot be modified.',
                        'locked_account_ids': locked_accounts,
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not accounts_to_update:
                return Response(
                    {'error': 'No matching trucking accounts found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Update the field for all matching accounts
            updated_count = 0
            for account in accounts_to_update:
                if field == 'trip_route':
                    if value:
                        route, created = Route.objects.get_or_create(name=value)
                        account.route = route
                    else:
                        account.route = None
                elif field == 'driver':
                    if value:
                        driver, created = Driver.objects.get_or_create(name=value)
                        account.driver = driver
                    else:
                        account.driver = None
                elif field == 'front_load':
                    if value:
                        load_type, created = LoadType.objects.get_or_create(name=value)
                        account.front_load = load_type
                    else:
                        account.front_load = None
                elif field == 'back_load':
                    if value:
                        load_type, created = LoadType.objects.get_or_create(name=value)
                        account.back_load = load_type
                    else:
                        account.back_load = None
                
                account.save()
                updated_count += 1
            
            return Response({
                'success': True,
                'message': f'Successfully updated {field} for {updated_count} records',
                'updated_count': updated_count,
                'plate_number': plate_number,
                'date': date_str,
                'field': field,
                'value': value
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            return Response(
                {'error': f'Failed to update trip field: {str(e)}', 'traceback': traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
