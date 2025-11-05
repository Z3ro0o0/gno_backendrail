from django.urls import path
from .views import (
    DriverDetailView,
    DriverListView,
    RouteDetailView,
    RouteListView,
    TruckDetailView,
    TruckListView,
    TruckTypeListView,
    TruckTypeDetailView,
    AccountTypeListView,
    AccountTypeDetailView,
    LoadTypeListView,
    LoadTypeDetailView,
    PlateNumberListView,
    PlateNumberDetailView,
    RepairAndMaintenanceAccountListView,
    RepairAndMaintenanceAccountDetailView,
    RepairAndMaintenanceUploadView,
    InsuranceAccountListView,
    InsuranceAccountDetailView,
    InsuranceAccountUploadView,
    FuelAccountListView,
    FuelAccountDetailView,
    FuelAccountUploadView,
    TaxAccountListView,
    TaxAccountDetailView,
    TaxAccountUploadView,
    AllowanceAccountListView,
    AllowanceAccountDetailView,
    AllowanceAccountUploadView,
    IncomeAccountListView,
    IncomeAccountDetailView,
    IncomeAccountUploadView,
    TruckingAccountListView,
    TruckingAccountDetailView,
    TruckingAccountUploadView,
)
from .drivers_summary_view import DriversSummaryView
from .trucking_upload_view import TruckingAccountPreviewView, TruckUploadView
from .revenue_views import RevenueStreamsView
from .opex_views import OPEXView
from .accounts_views import AccountsSummaryView, TruckingAccountSummaryView
from .accounts_detail_views import AccountsDetailView
from .trips_views import TripsView, UpdateTripFieldView
from .allowance_transfer_view import AllowanceTransferView
from .clear_trucking_view import ClearTruckingDataView

urlpatterns = [
    # TruckType URLs
    path('truck-types/', TruckTypeListView.as_view(), name='truck-type-list'),
    path('truck-types/<int:pk>/', TruckTypeDetailView.as_view(), name='truck-type-detail'),
    
    # AccountType URLs
    path('account-types/', AccountTypeListView.as_view(), name='account-type-list'),
    path('account-types/<int:pk>/', AccountTypeDetailView.as_view(), name='account-type-detail'),
    
    # LoadType URLs
    path('load-types/', LoadTypeListView.as_view(), name='load-type-list'),
    path('load-types/<int:pk>/', LoadTypeDetailView.as_view(), name='load-type-detail'),
    
    # PlateNumber URLs
    path('plate-numbers/', PlateNumberListView.as_view(), name='plate-number-list'),
    path('plate-numbers/<int:pk>/', PlateNumberDetailView.as_view(), name='plate-number-detail'),
    
    # Repair and Maintenance Account URLs
    path('repair-maintenance/', RepairAndMaintenanceAccountListView.as_view(), name='repair-maintenance-list'),
    path('repair-maintenance/<int:pk>/', RepairAndMaintenanceAccountDetailView.as_view(), name='repair-maintenance-detail'),
    path('repair-maintenance/upload/', RepairAndMaintenanceUploadView.as_view(), name='repair-maintenance-upload'),
    
    # Insurance Account URLs
    path('insurance/', InsuranceAccountListView.as_view(), name='insurance-list'),
    path('insurance/<int:pk>/', InsuranceAccountDetailView.as_view(), name='insurance-detail'),
    path('insurance/upload/', InsuranceAccountUploadView.as_view(), name='insurance-upload'),
    
    # Fuel Account URLs
    path('fuel/', FuelAccountListView.as_view(), name='fuel-list'),
    path('fuel/<int:pk>/', FuelAccountDetailView.as_view(), name='fuel-detail'),
    path('fuel/upload/', FuelAccountUploadView.as_view(), name='fuel-upload'),
    
    # Tax Account URLs
    path('tax/', TaxAccountListView.as_view(), name='tax-list'),
    path('tax/<int:pk>/', TaxAccountDetailView.as_view(), name='tax-detail'),
    path('tax/upload/', TaxAccountUploadView.as_view(), name='tax-upload'),
    
    # Allowance Account URLs
    path('allowance/', AllowanceAccountListView.as_view(), name='allowance-list'),
    path('allowance/<int:pk>/', AllowanceAccountDetailView.as_view(), name='allowance-detail'),
    path('allowance/upload/', AllowanceAccountUploadView.as_view(), name='allowance-upload'),
    
    # Income Account URLs
    path('income/', IncomeAccountListView.as_view(), name='income-list'),
    path('income/<int:pk>/', IncomeAccountDetailView.as_view(), name='income-detail'),
    path('income/upload/', IncomeAccountUploadView.as_view(), name='income-upload'),
    
    # Trucking Account URLs
    path('trucking/', TruckingAccountListView.as_view(), name='trucking-list'),
    path('trucking/<int:pk>/', TruckingAccountDetailView.as_view(), name='trucking-detail'),
    path('trucking/upload/', TruckingAccountUploadView.as_view(), name='trucking-upload'),
    path('trucking/preview/', TruckingAccountPreviewView.as_view(), name='trucking-preview'),
    path('trucking/clear/', ClearTruckingDataView.as_view(), name='trucking-clear'),
    
    
    path('drivers/summary/', DriversSummaryView.as_view(), name='drivers-summary'),
    
    # Revenue Streams URL
    path('revenue/streams/', RevenueStreamsView.as_view(), name='revenue-streams'),
    
    # OPEX URL
    path('revenue/opex/', OPEXView.as_view(), name='opex'),
    
    # Accounts Summary URL
    path('accounts/summary/', AccountsSummaryView.as_view(), name='accounts-summary'),
    
    # Trucking Account Summary URL
    path('trucking/accounts-summary/', TruckingAccountSummaryView.as_view(), name='trucking-accounts-summary'),
    
    # Accounts Detail URL
    path('accounts/detail/', AccountsDetailView.as_view(), name='accounts-detail'),
    
    # Trips URL
    path('trips/', TripsView.as_view(), name='trips'),
    path('trips/update-field/', UpdateTripFieldView.as_view(), name='trips-update-field'),
    
    # Allowance Transfer URL
    path('allowance/transfer/', AllowanceTransferView.as_view(), name='allowance-transfer'),

    # Driver URLs
    path('drivers/', DriverListView.as_view(), name='driver-list'),
    path('drivers/<int:pk>/', DriverDetailView.as_view(), name='driver-detail'),
    
    # Route URLs
    path('routes/', RouteListView.as_view(), name='route-list'),
    path('routes/<int:pk>/', RouteDetailView.as_view(), name='route-detail'),

    # Truck URLs
    path('trucks/', TruckListView.as_view(), name='truck-list'),
    path('trucks/<int:pk>/', TruckDetailView.as_view(), name='truck-detail'),
    path('trucks/upload/', TruckUploadView.as_view(), name='truck-upload'),
]