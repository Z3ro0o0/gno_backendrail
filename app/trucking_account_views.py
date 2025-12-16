from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.pagination import PageNumberPagination

from .models import TruckingAccount
from .serializers import TruckingAccountSerializer


class TruckingAccountPagination(PageNumberPagination):
    """Pagination for trucking accounts to improve performance"""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class TruckingAccountListView(ListCreateAPIView):
    """
    GET: List all trucking accounts with optimized queries
    POST: Create a new trucking account
    """
    serializer_class = TruckingAccountSerializer
    pagination_class = TruckingAccountPagination
    
    def get_queryset(self):
        """
        Optimize queries by using select_related to fetch all ForeignKey relationships
        in a single query instead of N+1 queries. This dramatically improves performance
        when accessing remote databases like Railway Postgres.
        """
        return TruckingAccount.objects.select_related(
            'account_type',      # ForeignKey to AccountType
            'truck',             # ForeignKey to Truck
            'truck__truck_type', # ForeignKey from Truck to TruckType
            'driver',            # ForeignKey to Driver
            'route',             # ForeignKey to Route
            'front_load',        # ForeignKey to LoadType
            'back_load',         # ForeignKey to LoadType
        ).order_by('-date', '-id')  # Order by date descending (most recent first)


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific trucking account
    PUT: Update a specific trucking account
    PATCH: Partially update a specific trucking account
    DELETE: Delete a specific trucking account
    """
    serializer_class = TruckingAccountSerializer
    
    def get_queryset(self):
        """
        Optimize queries by using select_related to fetch all ForeignKey relationships
        """
        return TruckingAccount.objects.select_related(
            'account_type',
            'truck',
            'truck__truck_type',
            'driver',
            'route',
            'front_load',
            'back_load',
        )

    def perform_destroy(self, instance):
        if instance.is_locked:
            raise ValidationError('Locked trucking accounts cannot be deleted.')
        instance.delete()

