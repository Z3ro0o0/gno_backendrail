from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Sum, Count
from collections import defaultdict
from datetime import datetime
from .models import TruckingAccount
from decimal import Decimal


class DriversSummaryView(APIView):
    """
    GET: Retrieve driver summary from trucking accounts
    Query params:
    - start_date: Filter by start date (YYYY-MM-DD or MM/DD/YYYY)
    - end_date: Filter by end date (YYYY-MM-DD or MM/DD/YYYY)
    """
    def get(self, request):
        try:
            # Get query parameters
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            # Base queryset with related objects
            queryset = TruckingAccount.objects.select_related('truck', 'driver', 'route').all()
            
            # Apply date filters if provided
            if start_date:
                try:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        start_date_obj = datetime.strptime(start_date, '%m/%d/%Y').date()
                    except ValueError:
                        return Response(
                            {'error': 'Invalid start_date format. Use YYYY-MM-DD or MM/DD/YYYY'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                queryset = queryset.filter(date__gte=start_date_obj)
            
            if end_date:
                try:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        end_date_obj = datetime.strptime(end_date, '%m/%d/%Y').date()
                    except ValueError:
                        return Response(
                            {'error': 'Invalid end_date format. Use YYYY-MM-DD or MM/DD/YYYY'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                queryset = queryset.filter(date__lte=end_date_obj)
            
            # Group by driver and calculate totals
            drivers_summary = defaultdict(lambda: {
                'driver': '',
                'total_trips': 0,
                'total_front_load': Decimal('0.00'),
                'total_back_load': Decimal('0.00'),
                'total_amount': Decimal('0.00'),
                'routes': set(),
                'trucks': set()
            })
            
            # Get all trucking accounts ordered by date, truck plate_number
            accounts = queryset.order_by('date', 'truck__plate_number', 'id')
            
            # Track entries for Strike logic
            entry_tracker = defaultdict(list)  # Key: (date, plate_number)
            
            for account in accounts:
                if not account.driver:
                    continue
                
                driver_name = account.driver.name
                amount = abs(float(account.credit)) if float(account.credit) != 0 else abs(float(account.debit))
                
                # Get plate_number from truck FK
                plate = account.truck.plate_number if account.truck else None
                
                # Track entry for Strike logic
                key = (str(account.date), plate or '')
                entry_tracker[key].append({
                    'account': account,
                    'amount': amount,
                    'driver_name': driver_name
                })
            
            # Process entries with Strike logic
            for key, entries in entry_tracker.items():
                for idx, entry in enumerate(entries):
                    account = entry['account']
                    amount = entry['amount']
                    driver_name = entry['driver_name']
                    
                    front_load = account.front_load
                    back_load = account.back_load
                    
                    # Skip records where both front_load and back_load are empty/None
                    if not front_load and not back_load:
                        continue
                    
                    # Determine amount allocation based on Strike logic
                    front_amount = Decimal('0.00')
                    back_amount = Decimal('0.00')
                    
                    if front_load and 'Strike' in front_load:
                        # If front_load is Strike, amount goes to back_load
                        back_amount = Decimal(str(amount))
                    elif back_load and 'Strike' in back_load:
                        # If back_load is Strike, amount goes to front_load
                        front_amount = Decimal(str(amount))
                    else:
                        # Multiple entries with same date and plate number
                        if len(entries) > 1:
                            if idx == 0:
                                front_amount = Decimal(str(amount))
                            else:
                                back_amount = Decimal(str(amount))
                        else:
                            # Single entry - check if both loads exist
                            if front_load and back_load:
                                # Split amount between front and back
                                front_amount = Decimal(str(amount)) / 2
                                back_amount = Decimal(str(amount)) / 2
                            elif front_load:
                                front_amount = Decimal(str(amount))
                            elif back_load:
                                back_amount = Decimal(str(amount))
                    
                    # Update driver summary
                    drivers_summary[driver_name]['driver'] = driver_name
                    drivers_summary[driver_name]['total_front_load'] += front_amount
                    drivers_summary[driver_name]['total_back_load'] += back_amount
                    drivers_summary[driver_name]['total_amount'] += Decimal(str(amount))
                    drivers_summary[driver_name]['total_trips'] += 1
                    
                    if account.route:
                        drivers_summary[driver_name]['routes'].add(account.route.name)
                    if account.truck and account.truck.plate_number:
                        drivers_summary[driver_name]['trucks'].add(account.truck.plate_number)
            
            # Convert to list format
            result = []
            for driver_name, data in drivers_summary.items():
                result.append({
                    'driver': data['driver'],
                    'total_trips': data['total_trips'],
                    'total_front_load': float(data['total_front_load']),
                    'total_back_load': float(data['total_back_load']),
                    'total_amount': float(data['total_amount']),
                    'routes': list(data['routes']),
                    'trucks': list(data['trucks'])
                })
            
            # Sort by total amount descending
            result.sort(key=lambda x: x['total_amount'], reverse=True)
            
            return Response({
                'drivers': result,
                'total_drivers': len(result),
                'summary': {
                    'total_front_load': sum(d['total_front_load'] for d in result),
                    'total_back_load': sum(d['total_back_load'] for d in result),
                    'total_amount': sum(d['total_amount'] for d in result),
                    'total_trips': sum(d['total_trips'] for d in result)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve drivers summary: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
