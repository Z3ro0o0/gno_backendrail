from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from .models import TruckingAccount, AccountType
from datetime import datetime


class AllowanceTransferView(APIView):
    """
    POST: Transfer allowance entries from one date to another
    Updates TruckingAccount records with Driver's Allowance account type
    Request body:
    {
        "source_plate_number": "NGS4359",
        "source_date": "2025-07-06",
        "target_plate_number": "NGS4359",
        "target_date": "2025-07-05",
        "entry_ids": [1, 2, 3, 4]  // Optional: specific entry IDs to transfer. If not provided, transfers all
    }
    """
    
    def post(self, request):
        try:
            source_plate_number = request.data.get('source_plate_number')
            source_date = request.data.get('source_date')
            target_plate_number = request.data.get('target_plate_number')
            target_date = request.data.get('target_date')
            entry_ids = request.data.get('entry_ids', [])
            
            if not all([source_plate_number, source_date, target_plate_number, target_date]):
                return Response(
                    {'error': 'Missing required fields: source_plate_number, source_date, target_plate_number, target_date'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Parse dates
            try:
                source_date_obj = datetime.strptime(source_date, '%Y-%m-%d').date()
                target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Standardize plate numbers for matching
            def standardize_plate(plate):
                if not plate:
                    return ''
                return str(plate).replace(' ', '').replace('-', '').upper()
            
            standardized_source_plate = standardize_plate(source_plate_number)
            
            # Get Driver's Allowance account type
            try:
                driver_allowance_type = AccountType.objects.filter(name__icontains='Driver').filter(name__icontains='Allowance').first()
                if not driver_allowance_type:
                    # Try alternative name
                    driver_allowance_type = AccountType.objects.filter(name__icontains="Driver's Allowance").first()
            except Exception:
                driver_allowance_type = None
            
            if not driver_allowance_type:
                return Response(
                    {'error': 'Driver\'s Allowance account type not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get all trucking accounts with Driver's Allowance on source date
            source_records = TruckingAccount.objects.filter(
                account_type=driver_allowance_type,
                date=source_date_obj
            ).select_related('truck', 'account_type')
            
            # Filter by plate number in Python since we need to standardize
            matching_records = []
            for record in source_records:
                record_plate = None
                if record.truck and record.truck.plate_number:
                    record_plate = record.truck.plate_number
                
                if record_plate and standardize_plate(record_plate) == standardized_source_plate:
                    # If entry_ids provided, only include those IDs
                    if entry_ids:
                        if record.id in entry_ids:
                            matching_records.append(record)
                    else:
                        matching_records.append(record)
            
            if not matching_records:
                return Response(
                    {'error': 'No matching allowance entries found to transfer'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Update dates
            updated_count = 0
            updated_ids = []
            for record in matching_records:
                record.date = target_date_obj
                record.save()
                updated_count += 1
                updated_ids.append(record.id)
            
            return Response({
                'success': True,
                'message': f'Successfully transferred {updated_count} allowance entries',
                'transferred_count': updated_count,
                'updated_ids': updated_ids,
                'source': {
                    'plate_number': source_plate_number,
                    'date': source_date
                },
                'target': {
                    'plate_number': target_plate_number,
                    'date': target_date
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            return Response(
                {'error': f'Failed to transfer allowance entries: {str(e)}', 'traceback': traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

