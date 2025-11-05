from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, Q
from collections import defaultdict
from datetime import datetime
from .models import TruckingAccount
from decimal import Decimal


class TruckingDriversSummaryView(APIView):
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
                
                driver = account.driver
                amount = abs(float(account.credit)) if float(account.credit) != 0 else abs(float(account.debit))
                
                # Get plate_number from truck FK
                plate = account.truck.plate_number if account.truck else None
                
                # Track entry for Strike logic
                key = (str(account.date), plate or '')
                entry_tracker[key].append({
                    'account': account,
                    'amount': amount,
                    'driver': driver
                })
            
            # Process entries with Strike logic
            for key, entries in entry_tracker.items():
                for idx, entry in enumerate(entries):
                    account = entry['account']
                    amount = entry['amount']
                    driver = entry['driver']
                    
                    front_load = account.front_load
                    back_load = account.back_load
                    
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
                                # First entry: amount for front_load
                                front_amount = Decimal(str(amount))
                            else:
                                # Subsequent entries: amount for back_load
                                back_amount = Decimal(str(amount))
                        else:
                            # Single entry: distribute based on availability
                            if front_load and back_load:
                                # Both loads present, split equally
                                front_amount = Decimal(str(amount)) / 2
                                back_amount = Decimal(str(amount)) / 2
                            elif front_load:
                                front_amount = Decimal(str(amount))
                            elif back_load:
                                back_amount = Decimal(str(amount))
                            else:
                                # No load info, assign to total only
                                front_amount = Decimal(str(amount))
                    
                    # Update driver summary
                    drivers_summary[driver]['driver'] = driver
                    drivers_summary[driver]['total_trips'] += 1
                    drivers_summary[driver]['total_front_load'] += front_amount
                    drivers_summary[driver]['total_back_load'] += back_amount
                    drivers_summary[driver]['total_amount'] += Decimal(str(amount))
                    
                    if account.route:
                        route_name = account.route.name if hasattr(account.route, 'name') else account.route
                        drivers_summary[driver]['routes'].add(route_name)
                    if account.truck and account.truck.plate_number:
                        drivers_summary[driver]['trucks'].add(account.truck.plate_number)
            
            # Convert to list and format
            result = []
            for driver_data in drivers_summary.values():
                result.append({
                    'driver': driver_data['driver'],
                    'total_trips': driver_data['total_trips'],
                    'total_front_load': float(driver_data['total_front_load']),
                    'total_back_load': float(driver_data['total_back_load']),
                    'total_amount': float(driver_data['total_amount']),
                    'routes': sorted(list(driver_data['routes'])),
                    'trucks': sorted(list(driver_data['trucks']))
                })
            
            # Sort by total_amount descending
            result.sort(key=lambda x: x['total_amount'], reverse=True)
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drivers summary: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TruckingRevenueStreamsView(APIView):
    """
    GET: Retrieve revenue streams from trucking accounts
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
            
            # Group by route and calculate totals
            revenue_streams = defaultdict(lambda: {
                'route': '',
                'total_trips': 0,
                'total_front_load': Decimal('0.00'),
                'total_back_load': Decimal('0.00'),
                'total_revenue': Decimal('0.00'),
                'drivers': set(),
                'trucks': set()
            })
            
            # Get all trucking accounts ordered by date, truck plate_number
            accounts = queryset.order_by('date', 'truck__plate_number', 'id')
            
            # Track entries for Strike logic
            entry_tracker = defaultdict(list)  # Key: (date, plate_number)
            
            for account in accounts:
                if not account.route:
                    continue
                
                route = account.route
                amount = abs(float(account.credit)) if float(account.credit) != 0 else abs(float(account.debit))
                
                # Get plate_number from truck FK
                plate = account.truck.plate_number if account.truck else None
                
                # Track entry for Strike logic
                key = (str(account.date), plate or '')
                entry_tracker[key].append({
                    'account': account,
                    'amount': amount,
                    'route': route
                })
            
            # Process entries with Strike logic
            for key, entries in entry_tracker.items():
                for idx, entry in enumerate(entries):
                    account = entry['account']
                    amount = entry['amount']
                    route = entry['route']
                    
                    front_load = account.front_load
                    back_load = account.back_load
                    
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
                                # First entry: amount for front_load
                                front_amount = Decimal(str(amount))
                            else:
                                # Subsequent entries: amount for back_load
                                back_amount = Decimal(str(amount))
                        else:
                            # Single entry: distribute based on availability
                            if front_load and back_load:
                                # Both loads present, split equally
                                front_amount = Decimal(str(amount)) / 2
                                back_amount = Decimal(str(amount)) / 2
                            elif front_load:
                                front_amount = Decimal(str(amount))
                            elif back_load:
                                back_amount = Decimal(str(amount))
                            else:
                                # No load info, assign to total only
                                front_amount = Decimal(str(amount))
                    
                    # Update revenue streams
                    revenue_streams[route]['route'] = route
                    revenue_streams[route]['total_trips'] += 1
                    revenue_streams[route]['total_front_load'] += front_amount
                    revenue_streams[route]['total_back_load'] += back_amount
                    revenue_streams[route]['total_revenue'] += Decimal(str(amount))
                    
                    if account.driver:
                        driver_name = account.driver.name if hasattr(account.driver, 'name') else account.driver
                        revenue_streams[route]['drivers'].add(driver_name)
                    if account.truck and account.truck.plate_number:
                        revenue_streams[route]['trucks'].add(account.truck.plate_number)
            
            # Convert to list and format
            result = []
            for route_data in revenue_streams.values():
                result.append({
                    'route': route_data['route'],
                    'total_trips': route_data['total_trips'],
                    'total_front_load': float(route_data['total_front_load']),
                    'total_back_load': float(route_data['total_back_load']),
                    'total_revenue': float(route_data['total_revenue']),
                    'drivers': sorted(list(route_data['drivers'])),
                    'trucks': sorted(list(route_data['trucks']))
                })
            
            # Sort by total_revenue descending
            result.sort(key=lambda x: x['total_revenue'], reverse=True)
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch revenue streams: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TruckingAccountsSummaryView(APIView):
    """
    GET: Retrieve accounts summary from trucking accounts
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
            queryset = TruckingAccount.objects.select_related('truck', 'truck__truck_type').all()
            
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
            
            # Group by account_type and truck_type
            accounts_summary = defaultdict(lambda: defaultdict(lambda: {
                'account_type': '',
                'truck_type': '',
                'total_debit': Decimal('0.00'),
                'total_credit': Decimal('0.00'),
                'total_final': Decimal('0.00'),
                'count': 0,
                'trucks': set()
            }))
            
            for account in queryset:
                account_type = account.account_type or 'Unknown'
                # Get truck_type from truck FK
                truck_type = account.truck.truck_type.name if (account.truck and account.truck.truck_type) else 'Unknown'
                
                accounts_summary[account_type][truck_type]['account_type'] = account_type
                accounts_summary[account_type][truck_type]['truck_type'] = truck_type
                accounts_summary[account_type][truck_type]['total_debit'] += Decimal(str(account.debit))
                accounts_summary[account_type][truck_type]['total_credit'] += Decimal(str(account.credit))
                accounts_summary[account_type][truck_type]['total_final'] += Decimal(str(account.final_total))
                accounts_summary[account_type][truck_type]['count'] += 1
                
                if account.truck and account.truck.plate_number:
                    accounts_summary[account_type][truck_type]['trucks'].add(account.truck.plate_number)
            
            # Convert to list and format
            result = []
            for account_type, truck_types in accounts_summary.items():
                for truck_type, data in truck_types.items():
                    result.append({
                        'account_type': data['account_type'],
                        'truck_type': data['truck_type'],
                        'total_debit': float(data['total_debit']),
                        'total_credit': float(data['total_credit']),
                        'total_final': float(data['total_final']),
                        'count': data['count'],
                        'trucks': sorted(list(data['trucks']))
                    })
            
            # Sort by account_type, then truck_type
            result.sort(key=lambda x: (x['account_type'], x['truck_type']))
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch accounts summary: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TruckingTripsSummaryView(APIView):
    """
    GET: Retrieve trips summary from trucking accounts (1 day = 1 trip)
    Query params:
    - start_date: Filter by start date (YYYY-MM-DD or MM/DD/YYYY)
    - end_date: Filter by end date (YYYY-MM-DD or MM/DD/YYYY)
    - plate_number: Filter by specific truck (optional)
    """
    def get(self, request):
        try:
            # Get query parameters
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            plate_number = request.query_params.get('plate_number')
            
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
            
            # Apply plate_number filter if provided (through truck FK)
            if plate_number:
                queryset = queryset.filter(truck__plate_number=plate_number)
            
            # Group by date and plate_number (1 day = 1 trip per truck)
            trips_summary = defaultdict(lambda: {
                'date': '',
                'plate_number': '',
                'driver': '',
                'routes': set(),
                'front_loads': [],
                'back_loads': [],
                'total_amount': Decimal('0.00'),
                'trip_count': 0
            })
            
            # Get all trucking accounts ordered by date, truck plate_number
            accounts = queryset.order_by('date', 'truck__plate_number', 'id')
            
            # Track entries for Strike logic
            entry_tracker = defaultdict(list)  # Key: (date, plate_number)
            
            for account in accounts:
                # Get plate_number from truck FK
                plate = account.truck.plate_number if account.truck else None
                if not plate:
                    continue
                
                amount = abs(float(account.credit)) if float(account.credit) != 0 else abs(float(account.debit))
                
                # Track entry for Strike logic
                key = (str(account.date), plate)
                entry_tracker[key].append({
                    'account': account,
                    'amount': amount
                })
            
            # Process entries with Strike logic
            for key, entries in entry_tracker.items():
                date_str, plate = key
                trip_key = key
                
                for idx, entry in enumerate(entries):
                    account = entry['account']
                    amount = entry['amount']
                    
                    # Get plate_number from truck FK
                    plate_num = account.truck.plate_number if account.truck else ''
                    
                    # Update trip summary
                    trips_summary[trip_key]['date'] = str(account.date)
                    trips_summary[trip_key]['plate_number'] = plate_num
                    trips_summary[trip_key]['total_amount'] += Decimal(str(amount))
                    trips_summary[trip_key]['trip_count'] = len(entries)
                    
                    if account.driver:
                        driver_name = account.driver.name if hasattr(account.driver, 'name') else account.driver
                        trips_summary[trip_key]['driver'] = driver_name
                    if account.route:
                        route_name = account.route.name if hasattr(account.route, 'name') else account.route
                        trips_summary[trip_key]['routes'].add(route_name)
                    if account.front_load:
                        trips_summary[trip_key]['front_loads'].append(account.front_load)
                    if account.back_load:
                        trips_summary[trip_key]['back_loads'].append(account.back_load)
            
            # Convert to list and format
            result = []
            for trip_data in trips_summary.values():
                result.append({
                    'date': trip_data['date'],
                    'plate_number': trip_data['plate_number'],
                    'driver': trip_data['driver'],
                    'routes': sorted(list(trip_data['routes'])),
                    'front_loads': trip_data['front_loads'],
                    'back_loads': trip_data['back_loads'],
                    'total_amount': float(trip_data['total_amount']),
                    'trip_count': trip_data['trip_count']
                })
            
            # Sort by date descending, then plate_number
            result.sort(key=lambda x: (x['date'], x['plate_number']), reverse=True)
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch trips summary: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
