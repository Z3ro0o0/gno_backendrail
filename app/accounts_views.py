from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count
from .models import TruckingAccount


class AccountsSummaryView(APIView):
    """
    GET: Get summary of all account types with totals
    """
    
    def get(self, request):
        try:
            # Get all account types with their totals from TruckingAccount
            accounts_summary = {}
            
            # Helper function to get account summary for a given account type
            def get_account_summary(account_type, display_name, color):
                records = TruckingAccount.objects.filter(account_type__name=account_type)
                totals = records.aggregate(
                    total_debit=Sum('debit'),
                    total_credit=Sum('credit'),
                    total_final=Sum('final_total'),
                    count=Count('id')
                )
                return {
                    'name': display_name,
                    'total_debit': float(totals['total_debit'] or 0),
                    'total_credit': float(totals['total_credit'] or 0),
                    'total_final': float(totals['total_final'] or 0),
                    'count': totals['count'],
                    'color': color
                }
            
            # Get summaries for each account type
            accounts_summary['repair_maintenance'] = get_account_summary(
                'Repairs and Maintenance Expense', 'Repair & Maintenance', 'blue'
            )
            
            accounts_summary['insurance'] = get_account_summary(
                'Insurance Expense', 'Insurance', 'green'
            )
            
            accounts_summary['fuel'] = get_account_summary(
                'Fuel and Oil', 'Fuel & Oil', 'orange'
            )
            
            accounts_summary['tax'] = get_account_summary(
                'Tax Expense', 'Tax Account', 'red'
            )
            
            accounts_summary['allowance'] = get_account_summary(
                'Driver\'s Allowance', 'Allowance Account', 'purple'
            )
            
            accounts_summary['income'] = get_account_summary(
                'Hauling Income', 'Income Account', 'emerald'
            )
            
            accounts_summary['salaries_wages'] = get_account_summary(
                'Salaries and Wages', 'Salaries and Wages', 'yellow'
            )
            
            accounts_summary['taxes_permits_licenses'] = get_account_summary(
                'Taxes, Permits and Licenses Expense', 'Taxes, Permits and Licenses', 'cyan'
            )
            
            # Calculate overall totals
            total_debit = sum(account['total_debit'] for account in accounts_summary.values())
            total_credit = sum(account['total_credit'] for account in accounts_summary.values())
            total_final = sum(account['total_final'] for account in accounts_summary.values())
            total_count = sum(account['count'] for account in accounts_summary.values())
            
            return Response({
                'accounts': accounts_summary,
                'summary': {
                    'total_debit': total_debit,
                    'total_credit': total_credit,
                    'total_final': total_final,
                    'total_count': total_count
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch accounts summary: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TruckingAccountSummaryView(APIView):
    """
    GET: Get account summary data from TruckingAccount model
    """
    
    def get(self, request):
        try:
            # Get all account types with their totals from TruckingAccount
            accounts_summary = {}
            
            # Helper function to get account summary for a given account type
            def get_account_summary(account_type, display_name, color):
                records = TruckingAccount.objects.filter(account_type__name=account_type)
                totals = records.aggregate(
                    total_debit=Sum('debit'),
                    total_credit=Sum('credit'),
                    total_final=Sum('final_total'),
                    count=Count('id')
                )
                return {
                    'name': display_name,
                    'total_debit': float(totals['total_debit'] or 0),
                    'total_credit': float(totals['total_credit'] or 0),
                    'total_final': float(totals['total_final'] or 0),
                    'count': totals['count'],
                    'color': color
                }
            
            # Get summaries for each account type
            accounts_summary['repair_maintenance'] = get_account_summary(
                'Repairs and Maintenance Expense', 'Repair & Maintenance', 'blue'
            )
            
            accounts_summary['insurance'] = get_account_summary(
                'Insurance Expense', 'Insurance', 'green'
            )
            
            accounts_summary['fuel'] = get_account_summary(
                'Fuel and Oil', 'Fuel & Oil', 'orange'
            )
            
            accounts_summary['tax'] = get_account_summary(
                'Tax Expense', 'Tax Account', 'red'
            )
            
            accounts_summary['allowance'] = get_account_summary(
                'Driver\'s Allowance', 'Allowance Account', 'purple'
            )
            
            accounts_summary['income'] = get_account_summary(
                'Hauling Income', 'Income Account', 'emerald'
            )
            
            accounts_summary['salaries_wages'] = get_account_summary(
                'Salaries and Wages', 'Salaries and Wages', 'yellow'
            )
            
            accounts_summary['taxes_permits_licenses'] = get_account_summary(
                'Taxes, Permits and Licenses Expense', 'Taxes, Permits and Licenses', 'cyan'
            )
            
            # Calculate overall totals
            total_debit = sum(account['total_debit'] for account in accounts_summary.values())
            total_credit = sum(account['total_credit'] for account in accounts_summary.values())
            total_final = sum(account['total_final'] for account in accounts_summary.values())
            total_count = sum(account['count'] for account in accounts_summary.values())
            
            return Response({
                'accounts': accounts_summary,
                'summary': {
                    'total_debit': total_debit,
                    'total_credit': total_credit,
                    'total_final': total_final,
                    'total_count': total_count
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch trucking accounts summary: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )