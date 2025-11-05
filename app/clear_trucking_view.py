from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import TruckingAccount


class ClearTruckingDataView(APIView):
    """
    DELETE: Clear all trucking account data
    """
    def delete(self, request):
        try:
            count = TruckingAccount.objects.count()
            TruckingAccount.objects.all().delete()
            return Response({
                'message': f'Successfully deleted {count} trucking account records',
                'deleted_count': count
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': f'Failed to clear trucking data: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

