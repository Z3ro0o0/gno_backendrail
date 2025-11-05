from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from collections import defaultdict
from .models import TruckingAccount


class OPEXView(APIView):
    """
    GET: Get OPEX breakdown by account types with percentages
    """
    
    def get(self, request):
        try:
            # Get OPEX amounts by account types
            opex_data = {}
            
            # Helper function to get account breakdown for a given account type
            def get_account_breakdown(account_type):
                records = TruckingAccount.objects.filter(account_type__name=account_type)
                account_totals = defaultdict(float)
                
                for record in records:
                    account_num = record.account_number if record.account_number else 'No Account Number'
                    account_totals[account_num] += float(record.final_total)
                
                return {
                    'total_amount': sum(account_totals.values()),
                    'account_details': [
                        {
                            'account_number': account_num,
                            'amount': round(amount, 2)
                        }
                        for account_num, amount in sorted(account_totals.items(), key=lambda x: x[1], reverse=True)
                    ]
                }
            
            # Get breakdown for each OPEX account type
            insurance_breakdown = get_account_breakdown('Insurance Expense')
            repairs_breakdown = get_account_breakdown('Repairs and Maintenance Expense')
            taxes_permits_breakdown = get_account_breakdown('Taxes, Permits and Licenses Expense')
            salaries_breakdown = get_account_breakdown('Salaries and Wages')
            tax_breakdown = get_account_breakdown('Tax Expense')
            
            opex_data = {
                'Insurance Expense': insurance_breakdown['total_amount'],
                'Repairs and Maintenance Expense': repairs_breakdown['total_amount'],
                'Taxes, Permits and Licenses Expense': taxes_permits_breakdown['total_amount'],
                'Salaries and Wages': salaries_breakdown['total_amount'],
                'Tax Expense': tax_breakdown['total_amount']
            }
            
            # Store account details for response
            account_details = {
                'Insurance Expense': insurance_breakdown['account_details'],
                'Repairs and Maintenance Expense': repairs_breakdown['account_details'],
                'Taxes, Permits and Licenses Expense': taxes_permits_breakdown['account_details'],
                'Salaries and Wages': salaries_breakdown['account_details'],
                'Tax Expense': tax_breakdown['account_details']
            }
            
            # Calculate total OPEX
            total_opex = sum(opex_data.values())
            
            # Calculate percentages and include account details
            opex_breakdown = []
            for account_type, amount in opex_data.items():
                percentage = (amount / total_opex * 100) if total_opex > 0 else 0
                opex_breakdown.append({
                    'account_type': account_type,
                    'amount': amount,
                    'percentage': round(percentage, 2),
                    'account_details': account_details[account_type]
                })
            
            # Sort by amount descending
            opex_breakdown.sort(key=lambda x: x['amount'], reverse=True)
            
            return Response({
                'opex_breakdown': opex_breakdown,
                'total_opex': total_opex,
                'summary': {
                    'total_categories': len(opex_breakdown),
                    'largest_category': opex_breakdown[0] if opex_breakdown else None,
                    'smallest_category': opex_breakdown[-1] if opex_breakdown else None
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch OPEX data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
