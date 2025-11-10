from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TruckingAccount


class LockTruckingAccountsView(APIView):
    """
    POST: Lock trucking account records that are currently unlocked.
    Optional payload:
      - ids: list of record IDs to lock (otherwise all unlocked records are targeted)
    """

    def post(self, request):
        ids = request.data.get('ids')

        if ids is not None and not isinstance(ids, (list, tuple)):
            return Response(
                {'error': 'ids must be an array of integers when provided.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                queryset = TruckingAccount.objects.filter(is_locked=False)

                if ids:
                    queryset = queryset.filter(id__in=ids)

                locked_at = timezone.now()
                updated_count = queryset.update(is_locked=True, locked_at=locked_at)

            return Response(
                {
                    'locked_count': updated_count,
                    'locked_at': locked_at,
                    'message': 'No unlocked records found.' if updated_count == 0 else 'Successfully locked trucking account records.',
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            return Response(
                {'error': f'Failed to lock trucking account records: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

