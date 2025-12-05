from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import TruckingAccount
import logging

logger = logging.getLogger(__name__)


class ClearTruckingDataView(APIView):
    """
    DELETE: Clear all trucking account data
    """
    def delete(self, request):
        try:
            # Get count before deletion
            count = TruckingAccount.objects.count()
            
            if count == 0:
                return Response({
                    'message': 'No trucking account records to delete',
                    'deleted_count': 0
                }, status=status.HTTP_200_OK)
            
            # Use transaction to ensure atomicity
            with transaction.atomic():
                deleted_count, deleted_dict = TruckingAccount.objects.all().delete()
                
            logger.info(f'Successfully deleted {deleted_count} trucking account records')
            
            return Response({
                'message': f'Successfully deleted {deleted_count} trucking account records',
                'deleted_count': deleted_count
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Failed to clear trucking data: {str(e)}', exc_info=True)
            return Response({
                'error': f'Failed to clear trucking data: {str(e)}',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

