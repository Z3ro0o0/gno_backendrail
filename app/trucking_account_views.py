from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from .models import TruckingAccount
from .serializers import TruckingAccountSerializer


class TruckingAccountListView(ListCreateAPIView):
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer


class TruckingAccountDetailView(RetrieveUpdateDestroyAPIView):
    queryset = TruckingAccount.objects.all()
    serializer_class = TruckingAccountSerializer

    def perform_destroy(self, instance):
        if instance.is_locked:
            raise ValidationError('Locked trucking accounts cannot be deleted.')
        instance.delete()

