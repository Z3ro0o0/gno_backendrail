from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from collections import defaultdict
from decimal import Decimal
from .models import TruckingAccount, AllowanceAccount, FuelAccount


class RevenueStreamsView(APIView):
    """
    GET: Get revenue and expense streams data
    """
    
    def get(self, request):
        try:
            # Get hauling income accounts from TruckingAccount
            hauling_accounts = TruckingAccount.objects.filter(account_type__name='Hauling Income')
            
            # Initialize revenue streams
            front_load_amount = Decimal('0.00')
            back_load_amount = Decimal('0.00')
            
            # Group hauling accounts by route, date, and reference number
            grouped_accounts = defaultdict(list)
            
            for account in hauling_accounts:
                # Skip if no route
                if not account.route:
                    continue
                
                key = (account.route, account.date, account.reference_number)
                grouped_accounts[key].append(account)
            
            # Process each group according to business rules
            for key, accounts in grouped_accounts.items():
                route, date, reference_number = key
                
                if len(accounts) == 1:
                    # Single entry - apply Strike logic
                    account = accounts[0]
                    amount = abs(float(account.credit)) if float(account.credit) != 0 else abs(float(account.debit))
                    front_load = account.front_load
                    back_load = account.back_load
                    
                    # Get front_load and back_load names
                    front_load_name = front_load.name if front_load and hasattr(front_load, 'name') else (front_load if isinstance(front_load, str) else None)
                    back_load_name = back_load.name if back_load and hasattr(back_load, 'name') else (back_load if isinstance(back_load, str) else None)
                    
                    if front_load_name and 'Strike' in front_load_name:
                        # If front_load is Strike, amount goes to back_load
                        back_load_amount += Decimal(str(amount))
                    elif back_load_name and 'Strike' in back_load_name:
                        # If back_load is Strike, amount goes to front_load
                        front_load_amount += Decimal(str(amount))
                    else:
                        # Check if both loads exist
                        if front_load and back_load:
                            # Split amount between front and back
                            half_amount = Decimal(str(amount)) / 2
                            front_load_amount += half_amount
                            back_load_amount += half_amount
                        elif front_load:
                            front_load_amount += Decimal(str(amount))
                        elif back_load:
                            back_load_amount += Decimal(str(amount))
                else:
                    # Multiple entries - first is front_load, rest are back_load
                    for i, account in enumerate(accounts):
                        amount = abs(float(account.credit)) if float(account.credit) != 0 else abs(float(account.debit))
                        if i == 0:
                            front_load_amount += Decimal(str(amount))
                        else:
                            back_load_amount += Decimal(str(amount))
            
            # Calculate expense streams from TruckingAccount
            # Get allowance amounts (Driver's Allowance)
            allowance_amount = TruckingAccount.objects.filter(account_type__name='Driver\'s Allowance').aggregate(
                total=Sum('final_total')
            )['total'] or 0
            
            # Get fuel amounts (Fuel and Oil)
            fuel_amount = TruckingAccount.objects.filter(account_type__name='Fuel and Oil').aggregate(
                total=Sum('final_total')
            )['total'] or 0
            
            # Get OPEX amounts by account types - sum actual values (negative values will be subtracted)
            insurance_records = TruckingAccount.objects.filter(account_type__name='Insurance Expense')
            insurance_amount = sum(float(record.final_total) for record in insurance_records)
            
            repairs_records = TruckingAccount.objects.filter(account_type__name='Repairs and Maintenance Expense')
            repairs_amount = sum(float(record.final_total) for record in repairs_records)
            
            taxes_permits_records = TruckingAccount.objects.filter(account_type__name='Taxes, Permits and Licenses Expense')
            taxes_permits_amount = sum(float(record.final_total) for record in taxes_permits_records)
            
            salaries_records = TruckingAccount.objects.filter(account_type__name='Salaries and Wages')
            salaries_amount = sum(float(record.final_total) for record in salaries_records)
            
            tax_records = TruckingAccount.objects.filter(account_type__name='Tax Expense')
            tax_amount = sum(float(record.final_total) for record in tax_records)
            
            # Calculate total OPEX (excluding Driver's Allowance and Fuel)
            total_opex = insurance_amount + repairs_amount + taxes_permits_amount + salaries_amount + tax_amount
            
            return Response({
                'revenue_streams': {
                    'front_load_amount': float(front_load_amount),
                    'back_load_amount': float(back_load_amount)
                },
                'expense_streams': {
                    'allowance': float(allowance_amount),
                    'add_allowance': 0,  # Additional allowance if needed
                    'fuel_amount': float(fuel_amount),
                    'add_fuel_amount': 0,  # Additional fuel if needed
                    'total_opex': total_opex
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch revenue streams data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



