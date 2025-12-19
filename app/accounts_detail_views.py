from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import TruckingAccount
from django.db.models import Q

class AccountsDetailView(APIView):
    """
    GET: Get detailed account entries from TruckingAccount model
    """
    def get(self, request):
        try:
            # Define account type mappings
            account_mappings = {
                'repair_maintenance': {
                    'account_type': 'Repairs and Maintenance Expense',
                    'name': 'Repair & Maintenance'
                },
                'insurance': {
                    'account_type': 'Insurance Expense',
                    'name': 'Insurance'
                },
                'fuel': {
                    'account_type': 'Fuel and Oil',
                    'name': 'Fuel & Oil'
                },
                'tax': {
                    'account_type': 'Tax Expense',
                    'name': 'Tax Account'
                },
                'allowance': {
                    'account_type': 'Driver\'s Allowance',
                    'name': 'Allowance Account'
                },
                'income': {
                    'account_type': 'Hauling Income',
                    'name': 'Income Account'
                },
                'salaries_wages': {
                    'account_type': 'Salaries and Wages',
                    'name': 'Salaries and Wages'
                },
                'taxes_permits_licenses': {
                    'account_type': 'Taxes, Permits and Licenses Expense',
                    'name': 'Taxes, Permits and Licenses'
                }
            }
            
            # Fetch ALL records in a single optimized query
            # Using select_related to avoid N+1 queries - this fetches all related objects in one query
            all_records = TruckingAccount.objects.select_related(
                'driver', 'route', 'truck', 'truck__truck_type', 'account_type', 'front_load', 'back_load'
            ).order_by('id')  # Consistent ordering for predictable results
            
            # Group records by account type in Python (faster than multiple DB queries)
            records_by_account_type = {}
            for record in all_records:
                account_type_name = None
                if record.account_type:
                    account_type_name = record.account_type.name if hasattr(record.account_type, 'name') else str(record.account_type)
                
                if account_type_name:
                    if account_type_name not in records_by_account_type:
                        records_by_account_type[account_type_name] = []
                    records_by_account_type[account_type_name].append(record)
            
            accounts_data = {}
            
            for key, mapping in account_mappings.items():
                # Get records for this account type from the pre-grouped data
                records = records_by_account_type.get(mapping['account_type'], [])
                
                # Convert to the format expected by frontend
                entries = []
                for record in records:
                    # Handle driver - can be ForeignKey object or None
                    driver_data = None
                    if record.driver:
                        if hasattr(record.driver, 'name'):
                            # It's a Driver model instance
                            driver_data = {
                                'id': record.driver.id,
                                'name': record.driver.name
                            }
                        else:
                            # It's already a string
                            driver_data = record.driver
                    
                    # Handle route - can be ForeignKey object or None
                    route_data = None
                    if record.route:
                        if hasattr(record.route, 'name'):
                            # It's a Route model instance
                            route_data = {
                                'id': record.route.id,
                                'name': record.route.name
                            }
                        else:
                            # It's already a string
                            route_data = record.route
                    
                    # Handle truck - get plate_number, truck_type, and company from truck FK
                    plate_number = ''
                    truck_type = ''
                    company = ''
                    if record.truck:
                        plate_number = record.truck.plate_number or ''
                        truck_type = record.truck.truck_type.name if record.truck.truck_type else ''
                        company = record.truck.company or ''
                    
                    # Handle account_type
                    account_type_data = None
                    if record.account_type:
                        if hasattr(record.account_type, 'name'):
                            account_type_data = record.account_type.name
                        else:
                            account_type_data = record.account_type
                    
                    # Handle front_load and back_load
                    front_load_data = None
                    if record.front_load:
                        if hasattr(record.front_load, 'name'):
                            front_load_data = record.front_load.name
                        else:
                            front_load_data = record.front_load
                    
                    back_load_data = None
                    if record.back_load:
                        if hasattr(record.back_load, 'name'):
                            back_load_data = record.back_load.name
                        else:
                            back_load_data = record.back_load
                    
                    entry = {
                        'id': record.id,
                        'account_number': record.account_number or '',
                        'truck_type': truck_type,
                        'company': company,
                        'account_type': account_type_data or '',
                        'plate_number': plate_number,
                        'debit': float(record.debit or 0),
                        'credit': float(record.credit or 0),
                        'final_total': float(record.final_total or 0),
                        'reference_number': record.reference_number or '',
                        'date': record.date.strftime('%Y-%m-%d') if record.date else '',
                        'description': record.description or '',
                        'remarks': record.remarks or '',
                        'driver': driver_data,
                        'route': route_data,
                        'liters': float(record.quantity or 0) if record.quantity else None,
                        'price': float(record.price or 0) if record.price else None,
                        'front_load': front_load_data or '',
                        'back_load': back_load_data or '',
                        'quantity': float(record.quantity or 0) if record.quantity else None
                    }
                    entries.append(entry)
                
                accounts_data[key] = {
                    'name': mapping['name'],
                    'entries': entries
                }
            
            return Response({
                'accounts': accounts_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch accounts detail data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )