
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import TruckingAccount, Driver, Route, Truck, TruckType, AccountType, LoadType
import pandas as pd
import re
from datetime import datetime, date

# Helper functions for load validation and cleaning
# Update the INVALID_LOADS set to be more comprehensive
INVALID_LOADS = {
    'sa', 'hw', 'on', 'daily', 'the', 'and', 'or', 'but', 'in', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'up', 'down', 'out', 'off', 'over', 'under',
    'lro', 'liters', 'fuel', 'oil', 'ug', 'ni', 'mag', 'para', 'additional',
    'transport', 'goods', 'items', 'load', 'delivery', 'pickup', 'mao',
    'transfer', 'pundo', 'tangke', 'bugas', 'humay', 'buug'
}

def is_valid_load(load_value, valid_load_types=None):
    """Enhanced validation for load values - checks against LoadType model"""
    if not load_value or len(load_value.strip()) < 2:
        return False
    
    load_clean = load_value.strip()
    
    # Check if it's all digits
    if load_clean.isdigit():
        return False
    
    # If valid_load_types is provided, use it (from database)
    if valid_load_types is not None:
        # Case-insensitive matching against database load types
        load_lower = load_clean.lower()
        for load_type in valid_load_types:
            if load_type.lower() == load_lower:
                return True
        return False
    
    # Fallback: Known valid loads (for backward compatibility)
    valid_loads = {
        'strike', 'cement', 'cemento', 'rh holcim', 'backload cdo'
    }
    
    # Check if it's a known valid load
    if load_clean.lower() in valid_loads:
        return True
    
    # REJECT everything else
    return False

def standardize_plate_number(plate_number):
    """Standardize plate number format by removing spaces, hyphens, and converting to uppercase"""
    if not plate_number:
        return None
    
    # Convert to string and clean
    plate_clean = str(plate_number).strip()
    
    # Remove all spaces, hyphens, and convert to uppercase
    standardized = plate_clean.replace(' ', '').replace('-', '').upper()
    
    return standardized if standardized else None

def clean_load_value(load_value, valid_load_types=None):
    """Enhanced cleaning for load values - matches against LoadType model"""
    if not load_value:
        return None
    
    load_clean = str(load_value).strip()
    
    # If valid_load_types is provided, find the best match from database
    if valid_load_types is not None:
        load_lower = load_clean.lower()
        # Try exact match first
        for load_type in valid_load_types:
            if load_type.lower() == load_lower:
                return load_type  # Return the exact name from database
        
        # Try partial match (in case there are extra words)
        for load_type in valid_load_types:
            if load_type.lower() in load_lower or load_lower in load_type.lower():
                return load_type
        
        return None
    
    # Fallback: Special cases (for backward compatibility)
    special_cases = {
        'backload cdo': 'Backload CDO',
        'rh holcim': 'RH Holcim',
        'strike': 'Strike',
        'cement': 'Cement',
        'cemento': 'Cemento'
    }
    
    # First check if it's a direct match
    if load_clean.lower() in special_cases:
        return special_cases[load_clean.lower()]
    
    # For case-sensitive variations, try to find a match
    for key, value in special_cases.items():
        if load_clean.lower() == key.lower():
            return value
    
    # If not a direct match, return None
    return None

class TruckingAccountPreviewView(APIView):
    """
    POST: Upload Excel file and preview parsed data without saving to database
    """
    def post(self, request):
        try:
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            file = request.FILES['file']
            
            # Try reading Excel file without skipping rows first (for newledger.xlsx format)
            # If that fails or columns don't match expected format, try with skiprows=7 for backward compatibility
            try:
                df = pd.read_excel(file)
                # Check if we have expected columns for new format
                df.columns = df.columns.str.strip()
                has_new_format = any('account' in col.lower() for col in df.columns) and \
                               any('type' in col.lower() and 'account' not in col.lower() and 'item' not in col.lower() for col in df.columns)
                
                if not has_new_format:
                    # Reset file pointer and try with skiprows
                    file.seek(0)
                    df = pd.read_excel(file, skiprows=7)
            except:
                # If reading fails, try with skiprows for backward compatibility
                file.seek(0)
                df = pd.read_excel(file, skiprows=7)
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Remove rows with 'Total for' in ANY column BEFORE parsing (PREVIEW VIEW)
            # This must happen early to avoid processing these rows
            df = df[~df.astype(str).apply(lambda x: x.str.contains('Total for', case=False, na=False)).any(axis=1)]
            
            # Function to parse Account column into components (PREVIEW VIEW)
            def parse_account_column(account_value):
                """Parse Account column to extract Account_Number, Account_Type, Truck_type, Plate_number"""
                if pd.isna(account_value) or account_value == '':
                    return None, None, None, None
                
                account_str = str(account_value).strip()
                
                # Skip "Total for" rows
                if 'Total for' in account_str:
                    return None, None, None, None
                
                # Split by " - " to get components
                parts = [p.strip() for p in account_str.split(' - ')]
                
                if len(parts) < 2:
                    # If format is different, try to extract account number
                    account_number_match = re.match(r'^(\d+)', account_str)
                    if account_number_match:
                        return account_number_match.group(1), None, None, None
                    return None, None, None, None
                
                account_number = parts[0] if parts[0].isdigit() else None
                account_type = None
                truck_type = None
                plate_number = None
                
                # Account type is usually the second part
                if len(parts) > 1:
                    account_type = parts[1]
                
                # Look for truck type in subsequent parts (common patterns: Trailer, Forward, 10-wheeler)
                # Note: "Trucking" is NOT a truck type, it's an account type descriptor
                truck_type_keywords = ['Trailer', 'Forward', '10-wheeler']
                for part in parts[2:]:
                    if any(keyword in part for keyword in truck_type_keywords):
                        truck_type = part
                        break
                
                # Look for plate number pattern (e.g., "KGJ 765", "NGS-4340", "NGS - 4340", "MVG 515", "TEMP 151005", "1101-939583")
                # Pattern 1: Letters followed by numbers (with optional spaces/hyphens between them)
                # This handles: "NGS-4340", "NGS 4340", "NGS - 4340", "KGJ 765"
                plate_pattern1 = r'([A-Z]{2,4}[\s\-]*\d{3,6})'
                # Pattern 2: Numbers followed by numbers (with optional hyphens/spaces) - more flexible
                # This handles: "1101-939583", "1101 939583"
                plate_pattern2 = r'(\d{3,4}[\s\-]*\d{3,9})'
                # Pattern 3: More flexible pattern for alphanumeric plates
                # This handles: "TEMP151005", "TEMP 151005"
                plate_pattern3 = r'([A-Z0-9]{4,12})'
                
                # Search in the entire account string, not just parts - more reliable
                account_upper = account_str.upper()
                
                # Try pattern 1 first (letters + numbers)
                plate_match = re.search(plate_pattern1, account_upper)
                if plate_match:
                    plate_number = plate_match.group(1).replace(' ', '').replace('-', '').upper()
                else:
                    # Try pattern 2 (numbers + numbers)
                    plate_match = re.search(plate_pattern2, account_upper)
                    if plate_match:
                        plate_number = plate_match.group(1).replace(' ', '').replace('-', '').upper()
                    else:
                        # Try pattern 3 (any alphanumeric sequence that looks like a plate)
                        plate_match = re.search(plate_pattern3, account_upper)
                        if plate_match:
                            potential_plate = plate_match.group(1).replace(' ', '').replace('-', '').upper()
                            # Only use if it has at least 3 digits (to avoid false positives)
                            if sum(c.isdigit() for c in potential_plate) >= 3:
                                plate_number = potential_plate
                
                return account_number, account_type, truck_type, plate_number
            
            # Find and parse Account column if it exists
            account_col = None
            for col in df.columns:
                col_lower = col.lower().strip()
                # Look for column that contains "account" but not "number" or "type"
                if 'account' in col_lower and 'number' not in col_lower and 'type' not in col_lower:
                    account_col = col
                    break
                # Also check for exact match
                if col_lower == 'account':
                    account_col = col
                    break
            
            if account_col:
                # Parse Account column and create new columns
                parsed_data = df[account_col].apply(parse_account_column)
                df['account_number'] = parsed_data.apply(lambda x: x[0] if x and x[0] else None)
                df['account_type'] = parsed_data.apply(lambda x: x[1] if x and x[1] else None)
                df['truck_type'] = parsed_data.apply(lambda x: x[2] if x and x[2] else None)
                # Store the parsed plate number - keep it as-is for now, will be normalized during validation
                # The parse_account_column already normalizes it (removes spaces/hyphens and uppercases)
                df['plate_number'] = parsed_data.apply(lambda x: x[3] if x and x[3] else None)
                
                # Remove the original Account column - it should not be uploaded (PREVIEW VIEW)
                df = df.drop(columns=[account_col], errors='ignore')
            
            # Helper function to extract plate number from any text using the same patterns
            def extract_plate_from_text(text_value):
                """Extract plate number from any text value using the same patterns as parse_account_column"""
                if pd.isna(text_value) or text_value == '':
                    return None
                
                text_str = str(text_value).strip()
                text_upper = text_str.upper()
                
                # Pattern 1: Letters followed by numbers (with optional spaces/hyphens between them)
                plate_pattern1 = r'([A-Z]{2,4}[\s\-]*\d{3,6})'
                # Pattern 2: Numbers followed by numbers (with REQUIRED separator)
                plate_pattern2 = r'(\d{3,4}[\s\-]+\d{3,9})'
                # Pattern 3: More flexible pattern for alphanumeric plates
                plate_pattern3 = r'([A-Z0-9]{4,12})'
                
                # Try pattern 1 first (letters + numbers)
                plate_match = re.search(plate_pattern1, text_upper)
                if plate_match:
                    return plate_match.group(1).replace(' ', '').replace('-', '').upper()
                
                # Try pattern 2 (numbers + numbers with separator)
                all_matches = re.findall(plate_pattern2, text_upper)
                if all_matches:
                    return all_matches[-1].replace(' ', '').replace('-', '').upper()
                
                # Try pattern 3 (any alphanumeric sequence that looks like a plate)
                all_matches = re.findall(plate_pattern3, text_upper)
                if all_matches:
                    potential_plates = [m for m in all_matches if sum(c.isdigit() for c in m) >= 3]
                    if potential_plates:
                        return potential_plates[-1].replace(' ', '').replace('-', '').upper()
                
                return None
            
            # If plate_number is None for any row, search ALL other columns for plate numbers
            if 'plate_number' in df.columns:
                # Find rows where plate_number is None
                missing_plate_mask = df['plate_number'].isna() | (df['plate_number'] == '') | (df['plate_number'] == None)
                
                if missing_plate_mask.any():
                    # Search in ALL other columns (skip plate_number, account_number, account_type, truck_type)
                    columns_to_search = []
                    priority_columns = []
                    other_columns = []
                    
                    for col in df.columns:
                        col_lower = col.lower().strip()
                        # Skip columns we've already processed
                        if col in ['plate_number', 'account_number', 'account_type', 'truck_type']:
                            continue
                        # Priority columns: Remarks, Description, unnamed columns
                        if 'remark' in col_lower or 'description' in col_lower or 'unnamed' in col_lower:
                            priority_columns.append(col)
                        else:
                            other_columns.append(col)
                    
                    # Combine: priority columns first, then other columns
                    columns_to_search = priority_columns + other_columns
                    
                    # For each row with missing plate_number, search the columns
                    for idx in df[missing_plate_mask].index:
                        for col in columns_to_search:
                            if col in df.columns:
                                plate_from_col = extract_plate_from_text(df.at[idx, col])
                                if plate_from_col:
                                    df.at[idx, 'plate_number'] = plate_from_col
                                    break  # Found a plate number, move to next row
            
            # Validate account_type against /api/v1/account-types/ endpoint (PREVIEW VIEW)
            # Get valid account types from AccountType model
            valid_account_types = set(AccountType.objects.values_list('name', flat=True))
            
            if 'account_type' in df.columns:
                def validate_account_type(account_type_value):
                    if pd.isna(account_type_value) or account_type_value == '' or account_type_value is None:
                        return None
                    account_type_str = str(account_type_value).strip()
                    # Check if it's a valid account type (case-insensitive)
                    for valid_type in valid_account_types:
                        if account_type_str.lower() == valid_type.lower():
                            return valid_type
                    # If not found, return None (invalid account type - not in endpoint)
                    return None
                
                df['account_type'] = df['account_type'].apply(validate_account_type)
                
                # Filter out rows with invalid account types (None or empty) - PREVIEW VIEW
                # Only keep rows where account_type is valid (not None and not empty)
                df = df[df['account_type'].notna() & (df['account_type'] != '')]
            
            # Validate truck_type and plate_number against /api/v1/trucks/ endpoint (PREVIEW VIEW)
            # Get valid trucks from Truck model
            valid_trucks = Truck.objects.select_related('truck_type').all()
            
            # Standardize plate number function - removes spaces and hyphens for comparison
            def standardize_plate(plate_str):
                if pd.isna(plate_str) or plate_str == '' or plate_str is None:
                    return None
                # Remove all spaces, hyphens, underscores, and convert to uppercase for comparison
                return str(plate_str).strip().upper().replace(' ', '').replace('-', '').replace('_', '')
            
            # Create a mapping of normalized plate_number -> (original_plate_number, truck_type_name, truck_object)
            truck_plate_map = {}
            truck_type_names = set()
            for truck in valid_trucks:
                if truck.plate_number:
                    plate_key = standardize_plate(truck.plate_number)
                    # Store original plate number, truck type, and truck object
                    truck_plate_map[plate_key] = {
                        'plate_number': truck.plate_number,  # Original format from database
                        'truck_type': truck.truck_type.name if truck.truck_type else None,
                        'truck': truck
                    }
                    if truck.truck_type:
                        truck_type_names.add(truck.truck_type.name)
            
            # Validate truck_type and plate_number - both must exist in /api/v1/trucks/
            # Always validate if plate_number or truck_type columns exist (even if empty)
            def validate_truck_data(row):
                # Get parsed plate number (may already be normalized during parsing, but normalize again to be sure)
                parsed_plate = row.get('plate_number') if 'plate_number' in df.columns else None
                plate_num_normalized = standardize_plate(parsed_plate)
                truck_type_str = str(row.get('truck_type')).strip() if 'truck_type' in df.columns and not pd.isna(row.get('truck_type')) and str(row.get('truck_type')).strip() != '' else None
                
                # If plate_number is provided, validate it exists in trucks endpoint
                if plate_num_normalized:
                    # Normalize the parsed plate again to ensure it matches (handles "1101-939583" -> "1101939583")
                    truck_data = truck_plate_map.get(plate_num_normalized)
                    
                    if truck_data:
                        # Found matching truck in endpoint
                        original_plate = truck_data['plate_number']
                        db_truck_type = truck_data['truck_type']
                        
                        # If truck_type is also provided, validate it matches the truck's type
                        if truck_type_str:
                            if db_truck_type and db_truck_type.lower() == truck_type_str.lower():
                                return db_truck_type, original_plate
                            else:
                                # Plate exists but truck_type doesn't match - still return plate with correct truck_type
                                # The truck_type from the endpoint takes precedence
                                return db_truck_type, original_plate
                        else:
                            # Only plate_number provided, return truck's type and original plate number
                            return db_truck_type, original_plate
                    else:
                        # Plate number not found in trucks endpoint - return None
                        return None, None
                elif truck_type_str:
                    # Only truck_type provided, validate it exists in any truck
                    if truck_type_str.lower() in [t.lower() for t in truck_type_names]:
                        # Return the canonical truck type name
                        for valid_type in truck_type_names:
                            if valid_type.lower() == truck_type_str.lower():
                                return valid_type, None
                    else:
                        # Truck type not found in trucks endpoint
                        return None, None
                
                # No plate or truck_type provided, keep existing values
                return row.get('truck_type') if 'truck_type' in df.columns else None, row.get('plate_number') if 'plate_number' in df.columns else None
            
            # Apply validation to each row - PREVIEW VIEW
            if 'plate_number' in df.columns or 'truck_type' in df.columns:
                validated_data = df.apply(validate_truck_data, axis=1)
                # Extract truck_type and plate_number from tuples, handling None properly
                df['truck_type'] = validated_data.apply(lambda x: x[0] if x and x[0] is not None else None)
                df['plate_number'] = validated_data.apply(lambda x: x[1] if x and x[1] is not None else None)
            
            # Map Excel columns to model fields (handle various column name formats) - PREVIEW VIEW
            # First, define columns to drop (not needed for newledger.xlsx format)
            columns_to_drop_list = []
            for col in df.columns:
                col_lower = col.lower().strip()
                # Drop columns that are not needed
                if any(keyword in col_lower for keyword in [
                    'applied to invoice', 'item code', 'item type', 'cost', 
                    'payment type', 'customer', 'supplier', 'employee', 
                    'cash account', 'check no', 'check date', 'location', 
                    'project', 'balance'
                ]):
                    # But keep if it's "Reference No." which we'll handle separately
                    if 'reference no' not in col_lower:
                        columns_to_drop_list.append(col)
            
            # Also drop "QTY", "Price", "Description" (old), "Item" if they exist as separate columns
            # (we'll use Type as description, and QTY/Price from new format if needed)
            for col in df.columns:
                col_lower = col.lower().strip()
                if col_lower == 'qty' or col_lower == 'item':
                    columns_to_drop_list.append(col)
                # Drop old "Description" if we have "Type" column (Type is the new description)
                if col_lower == 'description' and any('type' in c.lower() and 'account' not in c.lower() and 'item' not in c.lower() for c in df.columns):
                    columns_to_drop_list.append(col)
            
            column_mapping = {}
            for col in df.columns:
                # Skip columns we're dropping
                if col in columns_to_drop_list:
                    continue
                    
                col_lower = col.lower().strip()
                
                # Map Account column - will be parsed separately
                if 'account' in col_lower and 'number' not in col_lower and 'type' not in col_lower:
                    # This will be parsed, not mapped directly
                    continue
                elif 'account' in col_lower and 'number' in col_lower:
                    column_mapping[col] = 'account_number'
                elif 'account' in col_lower and 'type' in col_lower and 'account_number' not in df.columns:
                    column_mapping[col] = 'account_type'
                elif 'truck' in col_lower and 'type' in col_lower and 'truck_type' not in df.columns:
                    column_mapping[col] = 'truck_type'
                elif ('plate' in col_lower or 'truck plate' in col_lower) and 'plate_number' not in df.columns:
                    column_mapping[col] = 'plate_number'
                # Map "Type" column to "description" (new format - Type is the description)
                elif col_lower == 'type' or (col_lower == 'type' and 'item' not in col_lower):
                    column_mapping[col] = 'description'
                # Also handle old "Description" column if Type doesn't exist
                elif 'description' in col_lower and 'description' not in column_mapping.values():
                    column_mapping[col] = 'description'
                elif 'debit' in col_lower:
                    column_mapping[col] = 'debit'
                elif 'credit' in col_lower:
                    column_mapping[col] = 'credit'
                elif 'final' in col_lower and ('total' in col_lower or 'tc' in col_lower):
                    column_mapping[col] = 'final_total'
                elif 'remarks' in col_lower:
                    column_mapping[col] = 'remarks'
                # Map "RR No." to reference_number (new format)
                elif 'rr no' in col_lower or col_lower == 'rr no.':
                    column_mapping[col] = 'reference_number'
                # Also handle old "Reference No." or "Reference Number" 
                elif ('reference no' in col_lower or 'reference number' in col_lower) and 'reference_number' not in column_mapping.values():
                    column_mapping[col] = 'reference_number'
                elif 'date' in col_lower:
                    column_mapping[col] = 'date'
                elif 'quantity' in col_lower:
                    column_mapping[col] = 'quantity'
                elif 'price' in col_lower:
                    column_mapping[col] = 'price'
                elif 'driver' in col_lower:
                    column_mapping[col] = 'driver'
                elif 'route' in col_lower:
                    column_mapping[col] = 'route'
                elif 'front' in col_lower and 'load' in col_lower:
                    column_mapping[col] = 'front_load'
                elif 'back' in col_lower and 'load' in col_lower:
                    column_mapping[col] = 'back_load'
            
            # If no description column was found, check Unnamed columns for description-like data
            if 'description' not in column_mapping.values():
                for col in df.columns:
                    if col in columns_to_drop_list:
                        continue
                    if 'unnamed' in col.lower():
                        # Check if this column contains description-like data
                        # Sample a few non-null values to determine if it's a description column
                        sample_values = df[col].dropna().astype(str).head(10).tolist()
                        # Check if values contain common description keywords
                        description_keywords = ['beginning balance', 'receive inventory', 'inventory withdrawal', 'funds', 'transfer']
                        if any(any(keyword in str(val).lower() for keyword in description_keywords) for val in sample_values):
                            column_mapping[col] = 'description'
                            break
            
            # Drop unwanted columns BEFORE renaming
            df = df.drop(columns=columns_to_drop_list, errors='ignore')
            
            # Rename columns
            df = df.rename(columns=column_mapping)
            
            # Handle "Beginning Balance" - set ALL numeric fields to 0 (but don't delete the row)
            # Search ALL columns for "Beginning Balance" text BEFORE removing Unnamed columns
            # This ensures we catch "Beginning Balance" even if it's in an "Unnamed" column
            beginning_balance_mask = df.astype(str).apply(lambda x: x.str.contains('Beginning Balance', case=False, na=False)).any(axis=1)
            
            # Set all numeric/decimal fields to 0
            # Use original column names first, then mapped names
            numeric_field_names = ['debit', 'credit', 'final_total', 'Debit', 'Credit', 'Final Total', 'Final Total', 'QTY (Fuel)', 'Unit Cost']
            for field in numeric_field_names:
                if field in df.columns:
                    # Ensure we convert to numeric first, then set to 0
                    df[field] = pd.to_numeric(df[field], errors='coerce')
                    df.loc[beginning_balance_mask, field] = 0
            
            # Remove any remaining Account-related columns that aren't the parsed ones (Account, Account.1, etc.) - PREVIEW VIEW
            # But only drop if they exist and haven't been mapped yet
            columns_to_drop = [col for col in df.columns if col.lower().startswith('account') 
                              and col.lower() not in ['account_number', 'account_type'] 
                              and col not in column_mapping]
            df = df.drop(columns=columns_to_drop, errors='ignore')
            
            # Remove any Unnamed columns - PREVIEW VIEW (but keep description if it was mapped from Unnamed)
            columns_to_drop = [col for col in df.columns if 'unnamed' in col.lower() and col not in column_mapping]
            df = df.drop(columns=columns_to_drop, errors='ignore')
            
            # Drop old "Reference No." if we've mapped "RR No." to reference_number
            if 'reference_number' in column_mapping.values():
                # Find which column was mapped to reference_number
                mapped_ref_col = [col for col, mapped in column_mapping.items() if mapped == 'reference_number']
                if mapped_ref_col:
                    # Drop other reference columns that weren't mapped
                    ref_cols_to_drop = [col for col in df.columns 
                                       if ('reference' in col.lower() or 'rr no' in col.lower()) 
                                       and col not in mapped_ref_col 
                                       and col not in column_mapping]
                    df = df.drop(columns=ref_cols_to_drop, errors='ignore')
            
            # Handle "Beginning Balance" again after column mapping (to catch mapped column names)
            beginning_balance_mask = df.astype(str).apply(lambda x: x.str.contains('Beginning Balance', case=False, na=False)).any(axis=1)
            numeric_fields = ['debit', 'credit', 'final_total', 'quantity', 'price']
            for field in numeric_fields:
                if field in df.columns:
                    # Ensure we convert to numeric first, then set to 0
                    df[field] = pd.to_numeric(df[field], errors='coerce')
                    df.loc[beginning_balance_mask, field] = 0
            
            # Get valid drivers from database - PREVIEW VIEW
            valid_drivers = set(Driver.objects.values_list('name', flat=True))
            
            # Get valid routes from database - PREVIEW VIEW
            valid_routes = set(Route.objects.values_list('name', flat=True))
            
            # Include the same enhanced parsing functions here - PREVIEW VIEW
            def extract_driver_from_remarks(remarks):
                if pd.isna(remarks) or remarks is None:
                    return None
                remarks_str = str(remarks)
                
                # Get valid drivers from database (case-insensitive matching)
                def is_valid_driver(driver_name):
                    """Check if driver exists in database (case-insensitive)"""
                    if not driver_name:
                        return None
                    driver_clean = str(driver_name).strip()
                    for valid_driver in valid_drivers:
                        if driver_clean.lower() == valid_driver.lower():
                            return valid_driver  # Return the canonical name from database
                    return None  # Driver not in database
                
                # Known drivers list - only for pattern matching, then validate against database
                known_driver_patterns = [
                    'Edgardo Agapay', 'Romel Bantilan', 'Reynaldo Rizalda', 'Francis Ariglado',
                    'Roque Oling', 'Pablo Hamo', 'Albert Saavedra', 'Jimmy Oclarit', 'Nicanor',
                    'Arnel Duhilag', 'Benjamin Aloso', 'Roger', 'Joseph Bahan', 'Doming',
                    'Jun2x Campaña', 'Jun2x Toledo', 'Ronie Babanto'
                ]
                
                # Pattern 1: Check for known drivers first (exact match) - then validate against database
                for driver_pattern in known_driver_patterns:
                    if driver_pattern in remarks_str:
                        validated = is_valid_driver(driver_pattern)
                        if validated:
                            return validated
                
                # Pattern 2: Handle multiple drivers with "/" (e.g., "Jimmy Oclarit/Romel Bantilan")
                # Look for pattern: "Name1/Name2:" before route
                multi_driver_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*):'
                multi_match = re.search(multi_driver_pattern, remarks_str)
                if multi_match:
                    driver1 = multi_match.group(1).strip()
                    driver2 = multi_match.group(2).strip()
                    # Validate both against database
                    validated1 = is_valid_driver(driver1)
                    validated2 = is_valid_driver(driver2)
                    if validated1 and validated2:
                        return f"{validated1}/{validated2}"
                    elif validated1:
                        return validated1
                    elif validated2:
                        return validated2
                
                # Pattern 3: Extract driver from "LRO: XXLiters Fuel and Oil [DRIVER]:"
                # This handles cases like "LRO: 140Liters Fuel and Oil Roque Oling:"
                lro_pattern = r'LRO:\s*\d+Liters\s+Fuel\s+and\s+Oil\s+(?:[A-Z]+-\d+\s+)?([A-Za-z\s]+?)(?::|;)'
                lro_match = re.search(lro_pattern, remarks_str)
                if lro_match:
                    potential_driver = lro_match.group(1).strip()
                    # Clean up and validate
                    if len(potential_driver) > 2 and not any(word in potential_driver.lower() for word in ['lro', 'liters', 'fuel', 'oil']):
                        # Validate against database
                        validated = is_valid_driver(potential_driver)
                        if validated:
                            return validated
                
                # Pattern 4: Look for "Name:" pattern (but filter out routes and common words)
                name_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+):'
                matches = re.finditer(name_pattern, remarks_str)
                for match in matches:
                    potential_driver = match.group(1).strip()
                    # Skip if it looks like a route
                    if any(route_word in potential_driver.upper() for route_word in ['PAG-', 'CDO', 'ILIGAN', 'STRIKE']):
                        continue
                    # Skip common non-driver words
                    if any(word in potential_driver.lower() for word in ['lro', 'liters', 'fuel', 'oil', 'deliver', 'transfer']):
                        continue
                    # Validate against database
                    validated = is_valid_driver(potential_driver)
                    if validated:
                        return validated
                
                return None

            def extract_route_from_remarks(remarks):
                if pd.isna(remarks) or remarks is None:
                    return None
                remarks_str = str(remarks)
                
                # Get valid routes from database (case-insensitive matching)
                def is_valid_route(route_name):
                    """Check if route exists in database (case-insensitive)"""
                    if not route_name:
                        return None
                    route_clean = str(route_name).strip()
                    for valid_route in valid_routes:
                        if route_clean.upper() == valid_route.upper():
                            return valid_route  # Return the canonical name from database
                    return None  # Route not in database
                
                # Pattern 1: Look for route with colon after it (e.g., "PAG-ILIGAN:" or "CDO-LNO:")
                # This pattern matches: [A-Z]+-[A-Z]+ or any route format followed by colon
                # First, try to match any route from database that appears with a colon
                for route in valid_routes:
                    # Escape special regex characters in route name
                    route_escaped = re.escape(route)
                    pattern = rf'{route_escaped}\s*:'
                    match = re.search(pattern, remarks_str, re.IGNORECASE)
                    if match:
                        validated = is_valid_route(route)
                        if validated:
                            return validated
                
                # Pattern 2: Look for routes in specific contexts (after driver name or plate number)
                # E.g., "Juan Dela Cruz: CDO-LNO:" or "LAH-2577: CDO-LNO:"
                # Match pattern: ": [ROUTE]:" where ROUTE can be various formats
                context_pattern = r':\s*([A-Z0-9]+(?:-[A-Z0-9]+)+|[A-Z\s]+?)\s*:'
                matches = re.finditer(context_pattern, remarks_str, re.IGNORECASE)
                for match in matches:
                    potential_route = match.group(1).strip()
                    # Skip if it looks like a driver name (has lowercase letters in middle)
                    if re.search(r'[a-z]', potential_route) and len(potential_route.split()) > 1:
                        continue
                    validated = is_valid_route(potential_route)
                    if validated:
                        return validated
                
                # Pattern 3: Check for routes anywhere in the text (case-insensitive)
                # This is a fallback - check if any route name appears in the text
                for route in valid_routes:
                    route_escaped = re.escape(route)
                    # Match route as whole word or with word boundaries
                    pattern = rf'\b{route_escaped}\b'
                    if re.search(pattern, remarks_str, re.IGNORECASE):
                        validated = is_valid_route(route)
                        if validated:
                            return validated
                
                return None

            
            def extract_loads_from_remarks(remarks):
                """
                Extract front and back loads ONLY if they appear in a slash pattern, e.g. 'Strike/Cement'.
                Ignores all other forms such as 'deliver ug cemento' or 'backload humay'.
                Validates against LoadType database.
                """
                if pd.isna(remarks) or remarks is None:
                    return None, None
                remarks_str = str(remarks)

                front_load = None
                back_load = None
                
                # Get valid load types from database
                valid_load_types = [lt.name for lt in LoadType.objects.all()]

                # Helper function to clean load value - remove route names, delivery words, etc.
                def clean_load_extracted(load_str):
                    """Clean extracted load value by removing route names and delivery words"""
                    if not load_str:
                        return None
                    
                    cleaned = str(load_str).strip()
                    
                    # Remove route indicators (PAG-, DUMINGAG, etc.)
                    route_patterns = [
                        r'\bPAG-[A-Z]+\b',
                        r'\bDUMINGAG\b',
                        r'\bDIMATALING\b',
                        r'\bCDO\b',
                        r'\bILIGAN\b',
                        r'\bOPEX\b',
                        r'\bPAGADIAN\b'
                    ]
                    for pattern in route_patterns:
                        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
                    
                    # Remove delivery/action words
                    delivery_words = [
                        r'\bdeliver\b',
                        r'\bDeliver\b',
                        r'\bDELIVER\b',
                        r'\bpara\b',
                        r'\bPara\b',
                        r'\bsa\b',
                        r'\bto\b',
                        r'\bug\b',
                        r'\bni\b',
                        r'\bmao\b'
                    ]
                    for word in delivery_words:
                        cleaned = re.sub(word, '', cleaned, flags=re.IGNORECASE)
                    
                    # Remove numbers and special characters at the end
                    cleaned = re.sub(r'[:\.,;]+$', '', cleaned)
                    cleaned = re.sub(r'\s+\+\d+.*$', '', cleaned)  # Remove "+165ltrs" etc.
                    cleaned = re.sub(r'\s+\d+.*$', '', cleaned)  # Remove trailing numbers
                    
                    # Clean up multiple spaces
                    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                    
                    return cleaned if cleaned else None

                # Helper function to get Strike load type from database
                def get_strike_load():
                    """Get Strike load type from database, case-insensitive"""
                    strike_load = next((lt for lt in valid_load_types if lt.lower() == 'strike'), None)
                    return strike_load if strike_load else 'Strike'  # Fallback to 'Strike' if not in DB
                
                # Helper function to handle single load with default to Strike
                def handle_single_load(front, back):
                    """Handle case where one load is valid and other is missing - default missing to Strike"""
                    front_valid = front and is_valid_load(front, valid_load_types)
                    back_valid = back and is_valid_load(back, valid_load_types)
                    
                    if front_valid and back_valid:
                        # Both valid - return both
                        return clean_load_value(front, valid_load_types), clean_load_value(back, valid_load_types)
                    elif front_valid and not back_valid:
                        # Front valid, back missing/invalid - set back to "Strike"
                        strike_load = get_strike_load()
                        return clean_load_value(front, valid_load_types), strike_load
                    elif back_valid and not front_valid:
                        # Back valid, front missing/invalid - set front to "Strike"
                        strike_load = get_strike_load()
                        return strike_load, clean_load_value(back, valid_load_types)
                    return None, None

                # Pattern 1: "load1/load2:" - with trailing colon (most common)
                # Examples: "Strike/Cement:", "RH Holcim/Cement:", "RH Holcim/Backload CDO:", "Strike/cemento:"
                load_pattern_with_colon = r':\s*([A-Za-z\s]+)/([A-Za-z\s]+):'
                match = re.search(load_pattern_with_colon, remarks_str)
                if match:
                    potential_front = clean_load_extracted(match.group(1))
                    potential_back = clean_load_extracted(match.group(2))
                    result = handle_single_load(potential_front, potential_back)
                    if result[0] and result[1]:
                        return result

                # Pattern 2: "load1/load2" at end of string (no trailing colon)
                # Examples: "Strike/Cement", "Cement/Backload CDO"
                load_pattern_end = r':\s*([A-Za-z\s]+)/([A-Za-z\s]+)\s*$'
                match = re.search(load_pattern_end, remarks_str)
                if match:
                    potential_front = clean_load_extracted(match.group(1))
                    potential_back = clean_load_extracted(match.group(2))
                    result = handle_single_load(potential_front, potential_back)
                    if result[0] and result[1]:
                        return result

                # Pattern 3: "load1/load2" followed by text (no colon, but with separator words)
                # Examples: "Strike/Cement deliver to caluma", "Strike/Cement +120ltrs", "RH Holcim/Cement DUMINGAG Deliver"
                load_pattern_with_text = r':\s*([A-Za-z\s]+)/([A-Za-z\s]+?)(?:\s+(?:deliver|Deliver|DELIVER|para|Para|sa|to|ug|\+|:|\d|DUMINGAG|DIMATALING|PAG-|$))'
                match = re.search(load_pattern_with_text, remarks_str, re.IGNORECASE)
                if match:
                    potential_front = clean_load_extracted(match.group(1))
                    potential_back = clean_load_extracted(match.group(2))
                    result = handle_single_load(potential_front, potential_back)
                    if result[0] and result[1]:
                        return result

                # Pattern 4: "load1/load2" anywhere in the string with word boundaries
                # Examples: "PAG-ILIGAN: Strike/Cement: additional notes"
                load_pattern_general = r'\b([A-Za-z\s]{3,})/([A-Za-z\s]{3,})\b'
                match = re.search(load_pattern_general, remarks_str)
                if match:
                    potential_front = clean_load_extracted(match.group(1))
                    potential_back = clean_load_extracted(match.group(2))

                    # Make sure neither part looks like a route or driver name
                    route_indicators = ['PAG-', 'CDO', 'ILIGAN', 'OPEX', 'PAGADIAN', 'DUMINGAG', 'DIMATALING']
                    is_route = any(indicator in (potential_front or '').upper() or indicator in (potential_back or '').upper()
                                for indicator in route_indicators)

                    if not is_route:
                        result = handle_single_load(potential_front, potential_back)
                        if result[0] and result[1]:
                            return result

                # No slash pattern found - return None for both
                return None, None

            # Convert driver, route, front_load, back_load columns to object type to avoid dtype warnings
            if 'driver' in df.columns:
                df['driver'] = df['driver'].astype('object')
            if 'route' in df.columns:
                df['route'] = df['route'].astype('object')
            if 'front_load' in df.columns:
                df['front_load'] = df['front_load'].astype('object')
            if 'back_load' in df.columns:
                df['back_load'] = df['back_load'].astype('object')
            
            # Validate drivers against database - only keep drivers that exist in database (PREVIEW VIEW)
            if 'driver' in df.columns:
                # Get valid drivers from database (case-insensitive matching)
                valid_drivers_db = set(Driver.objects.values_list('name', flat=True))
                
                def validate_driver(driver_value):
                    """Validate driver exists in database (case-insensitive)"""
                    if pd.isna(driver_value) or driver_value == '' or driver_value is None:
                        return None  # Empty driver is allowed
                    driver_str = str(driver_value).strip()
                    # Check if it's a valid driver (case-insensitive)
                    for valid_driver in valid_drivers_db:
                        if driver_str.lower() == valid_driver.lower():
                            return valid_driver  # Return canonical name from database
                    # Invalid driver - return None (but don't filter row, just clear driver)
                    return None
                
                # Validate existing driver column values
                df['driver'] = df['driver'].apply(validate_driver)
            
            # Validate load types against database - only keep loads that exist in database (PREVIEW VIEW)
            if 'front_load' in df.columns or 'back_load' in df.columns:
                # Get valid load types from database (case-insensitive matching)
                valid_load_types_db = set(LoadType.objects.values_list('name', flat=True))
                
                def validate_load_type(load_value):
                    """Validate load type exists in database (case-insensitive)"""
                    if pd.isna(load_value) or load_value == '' or load_value is None:
                        return None  # Empty load is allowed
                    load_str = str(load_value).strip()
                    # Clean the load value first
                    load_cleaned = clean_load_value(load_str, valid_load_types_db)
                    if load_cleaned:
                        # Check if it's a valid load type (case-insensitive)
                        for valid_load in valid_load_types_db:
                            if load_cleaned.lower() == valid_load.lower():
                                return valid_load  # Return canonical name from database
                    # Invalid load - return None (but don't filter row, just clear load)
                    return None
                
                # Validate existing load column values
                if 'front_load' in df.columns:
                    df['front_load'] = df['front_load'].apply(validate_load_type)
                if 'back_load' in df.columns:
                    df['back_load'] = df['back_load'].apply(validate_load_type)
            
            # Apply parsing to extract driver, route, front_load, back_load from remarks
            # Always extract from remarks to override any existing values
            if 'remarks' in df.columns:
                # Get valid load types for validation after extraction (PREVIEW VIEW)
                valid_load_types_db_after_extraction = set(LoadType.objects.values_list('name', flat=True))
                
                for index, row in df.iterrows():
                    # Always extract driver from remarks if available
                    extracted_driver = extract_driver_from_remarks(row.get('remarks'))
                    if extracted_driver:
                        df.at[index, 'driver'] = extracted_driver
                    
                    # Always extract route from remarks if available
                    extracted_route = extract_route_from_remarks(row.get('remarks'))
                    if extracted_route:
                        df.at[index, 'route'] = extracted_route
                    
                    # Only extract loads if BOTH driver AND route are present
                    # This prevents extracting maintenance items like "Fan Belt/Grease" as loads
                    if extracted_driver and extracted_route:
                        extracted_front, extracted_back = extract_loads_from_remarks(row.get('remarks'))
                        if extracted_front:
                            # Clean the front load value and validate against database
                            cleaned_front = clean_load_value(extracted_front, valid_load_types_db_after_extraction)
                            if cleaned_front:
                                # Validate against database
                                for valid_load in valid_load_types_db_after_extraction:
                                    if cleaned_front.lower() == valid_load.lower():
                                        df.at[index, 'front_load'] = valid_load  # Use canonical name from database
                                        break
                        if extracted_back:
                            # Clean the back load value and validate against database
                            cleaned_back = clean_load_value(extracted_back, valid_load_types_db_after_extraction)
                            if cleaned_back:
                                # Validate against database
                                for valid_load in valid_load_types_db_after_extraction:
                                    if cleaned_back.lower() == valid_load.lower():
                                        df.at[index, 'back_load'] = valid_load  # Use canonical name from database
                                        break
            
            # Calculate final_total from Debit and Credit if final_total column doesn't exist
            if 'debit' in df.columns and 'credit' in df.columns:
                # Convert to numeric, handling NaN values
                df['debit'] = pd.to_numeric(df['debit'], errors='coerce').fillna(0)
                df['credit'] = pd.to_numeric(df['credit'], errors='coerce').fillna(0)
                
                # If final_total column doesn't exist, create it from debit - credit
                if 'final_total' not in df.columns:
                    df['final_total'] = df['debit'] - df['credit']
                else:
                    # If final_total exists but is NaN/empty, calculate from debit - credit
                    df['final_total'] = pd.to_numeric(df['final_total'], errors='coerce')
                    df['final_total'] = df['final_total'].fillna(df['debit'] - df['credit'])
            
            # For Hauling Income accounts, ensure final_total is positive (use abs if negative)
            if 'account_type' in df.columns and 'final_total' in df.columns:
                hauling_income_mask = df['account_type'].astype(str).str.contains('Hauling Income', case=False, na=False)
                # Apply abs() to make positive if negative
                df.loc[hauling_income_mask, 'final_total'] = df.loc[hauling_income_mask, 'final_total'].apply(lambda x: abs(x) if x < 0 else x)
            
            # Define desired column order for preview
            desired_column_order = [
                'account_number',
                'account_type',
                'truck_type',
                'plate_number',
                'description',
                'debit',
                'credit',
                'final_total',
                'remarks',
                'reference_number',
                'date',
                'quantity',
                'price',
                'driver',
                'route',
                'front_load',
                'back_load'
            ]
            
            # Reorder DataFrame columns: desired order first, then any remaining columns
            existing_columns = list(df.columns)
            ordered_columns = [col for col in desired_column_order if col in existing_columns]
            remaining_columns = [col for col in existing_columns if col not in desired_column_order]
            df = df[ordered_columns + remaining_columns]
            
            # Convert to list of dictionaries for preview - show ALL columns
            preview_data = []
            parsing_stats = {
                'drivers_extracted': 0,
                'routes_extracted': 0,
                'loads_extracted': 0,
                'total_rows': len(df)
            }
            
            def safe_convert(value, default=None):
                """Safely convert value, handling NaN and None"""
                if pd.isna(value) or value is None:
                    return default
                if isinstance(value, (int, float)):
                    if pd.isna(value):
                        return default
                    return value
                return str(value) if value != '' else default
            
            for index, row in df.iterrows():
                # Skip completely empty rows
                if row.isnull().all():
                    continue
                
                if row.get('driver') and row.get('driver') != '':
                    parsing_stats['drivers_extracted'] += 1
                if row.get('route') and row.get('route') != '':
                    parsing_stats['routes_extracted'] += 1
                if row.get('front_load') and row.get('front_load') != '':
                    parsing_stats['loads_extracted'] += 1
                
                # Create row data with columns in desired order
                row_data = {'row_number': index + 1}
                
                # Add columns in the desired order first
                for col in desired_column_order:
                    if col in df.columns:
                        row_data[col] = safe_convert(row.get(col))
                
                # Then add any remaining columns that weren't in the desired order
                for col in df.columns:
                    if col not in desired_column_order:
                        row_data[col] = safe_convert(row.get(col))
                
                preview_data.append(row_data)
            
            response_data = {
                'preview_data': preview_data,  # Show all rows for preview
                'parsing_stats': parsing_stats,
                'message': f'Preview generated for {len(preview_data)} rows',
                'total_rows': len(preview_data)
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to generate preview: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TruckingAccountUploadView(APIView):
    """
    POST: Upload Excel file and bulk create trucking accounts with automatic parsing
    """
    def post(self, request):
        try:
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            file = request.FILES['file']
            
            # Try reading Excel file without skipping rows first (for newledger.xlsx format)
            # If that fails or columns don't match expected format, try with skiprows=7 for backward compatibility
            try:
                df = pd.read_excel(file)
                # Check if we have expected columns for new format
                df.columns = df.columns.str.strip()
                has_new_format = any('account' in col.lower() for col in df.columns) and \
                               any('type' in col.lower() and 'account' not in col.lower() and 'item' not in col.lower() for col in df.columns)
                
                if not has_new_format:
                    # Reset file pointer and try with skiprows
                    file.seek(0)
                    df = pd.read_excel(file, skiprows=7)
            except:
                # If reading fails, try with skiprows for backward compatibility
                file.seek(0)
                df = pd.read_excel(file, skiprows=7)
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Remove rows with 'Total for' in ANY column BEFORE parsing (UPLOAD VIEW)
            # This must happen early to avoid processing these rows
            df = df[~df.astype(str).apply(lambda x: x.str.contains('Total for', case=False, na=False)).any(axis=1)]
            
            # Function to parse Account column into components
            def parse_account_column(account_value):
                """Parse Account column to extract Account_Number, Account_Type, Truck_type, Plate_number"""
                if pd.isna(account_value) or account_value == '':
                    return None, None, None, None
                
                account_str = str(account_value).strip()
                
                # Skip "Total for" rows
                if 'Total for' in account_str:
                    return None, None, None, None
                
                # Split by " - " to get components
                parts = [p.strip() for p in account_str.split(' - ')]
                
                if len(parts) < 2:
                    # If format is different, try to extract account number
                    account_number_match = re.match(r'^(\d+)', account_str)
                    if account_number_match:
                        return account_number_match.group(1), None, None, None
                    return None, None, None, None
                
                account_number = parts[0] if parts[0].isdigit() else None
                account_type = None
                truck_type = None
                plate_number = None
                
                # Account type is usually the second part
                if len(parts) > 1:
                    account_type = parts[1]
                
                # Look for truck type in subsequent parts (common patterns: Trailer, Forward, 10-wheeler)
                # Note: "Trucking" is NOT a truck type, it's an account type descriptor
                truck_type_keywords = ['Trailer', 'Forward', '10-wheeler']
                for part in parts[2:]:
                    if any(keyword in part for keyword in truck_type_keywords):
                        truck_type = part
                        break
                
                # Look for plate number pattern (e.g., "KGJ 765", "NGS-4340", "NGS - 4340", "MVG 515", "TEMP 151005", "1101-939583")
                # Pattern 1: Letters followed by numbers (with optional spaces/hyphens between them)
                # This handles: "NGS-4340", "NGS 4340", "NGS - 4340", "KGJ 765"
                plate_pattern1 = r'([A-Z]{2,4}[\s\-]*\d{3,6})'
                # Pattern 2: Numbers followed by numbers (with optional hyphens/spaces) - more flexible
                # This handles: "1101-939583", "1101 939583"
                plate_pattern2 = r'(\d{3,4}[\s\-]*\d{3,9})'
                # Pattern 3: More flexible pattern for alphanumeric plates
                # This handles: "TEMP151005", "TEMP 151005"
                plate_pattern3 = r'([A-Z0-9]{4,12})'
                
                # Search in the entire account string, not just parts - more reliable
                account_upper = account_str.upper()
                
                # Try pattern 1 first (letters + numbers)
                plate_match = re.search(plate_pattern1, account_upper)
                if plate_match:
                    plate_number = plate_match.group(1).replace(' ', '').replace('-', '').upper()
                else:
                    # Try pattern 2 (numbers + numbers)
                    plate_match = re.search(plate_pattern2, account_upper)
                    if plate_match:
                        plate_number = plate_match.group(1).replace(' ', '').replace('-', '').upper()
                    else:
                        # Try pattern 3 (any alphanumeric sequence that looks like a plate)
                        plate_match = re.search(plate_pattern3, account_upper)
                        if plate_match:
                            potential_plate = plate_match.group(1).replace(' ', '').replace('-', '').upper()
                            # Only use if it has at least 3 digits (to avoid false positives)
                            if sum(c.isdigit() for c in potential_plate) >= 3:
                                plate_number = potential_plate
                
                return account_number, account_type, truck_type, plate_number
            
            # Find and parse Account column if it exists
            account_col = None
            for col in df.columns:
                col_lower = col.lower().strip()
                # Look for column that contains "account" but not "number" or "type"
                if 'account' in col_lower and 'number' not in col_lower and 'type' not in col_lower:
                    account_col = col
                    break
                # Also check for exact match
                if col_lower == 'account':
                    account_col = col
                    break
            
            if account_col:
                # Parse Account column and create new columns
                parsed_data = df[account_col].apply(parse_account_column)
                df['account_number'] = parsed_data.apply(lambda x: x[0] if x else None)
                df['account_type'] = parsed_data.apply(lambda x: x[1] if x else None)
                df['truck_type'] = parsed_data.apply(lambda x: x[2] if x else None)
                # Store the parsed plate number (it's already normalized in parse_account_column)
                # But keep the original format for now - we'll normalize during validation
                df['plate_number'] = parsed_data.apply(lambda x: x[3] if x else None)
                
                # Remove the original Account column - it should not be uploaded (UPLOAD VIEW)
                df = df.drop(columns=[account_col], errors='ignore')
            
            # Helper function to extract plate number from any text using the same patterns
            def extract_plate_from_text(text_value):
                """Extract plate number from any text value using the same patterns as parse_account_column"""
                if pd.isna(text_value) or text_value == '':
                    return None
                
                text_str = str(text_value).strip()
                text_upper = text_str.upper()
                
                # Pattern 1: Letters followed by numbers (with optional spaces/hyphens between them)
                plate_pattern1 = r'([A-Z]{2,4}[\s\-]*\d{3,6})'
                # Pattern 2: Numbers followed by numbers (with REQUIRED separator)
                plate_pattern2 = r'(\d{3,4}[\s\-]+\d{3,9})'
                # Pattern 3: More flexible pattern for alphanumeric plates
                plate_pattern3 = r'([A-Z0-9]{4,12})'
                
                # Try pattern 1 first (letters + numbers)
                plate_match = re.search(plate_pattern1, text_upper)
                if plate_match:
                    return plate_match.group(1).replace(' ', '').replace('-', '').upper()
                
                # Try pattern 2 (numbers + numbers with separator)
                all_matches = re.findall(plate_pattern2, text_upper)
                if all_matches:
                    return all_matches[-1].replace(' ', '').replace('-', '').upper()
                
                # Try pattern 3 (any alphanumeric sequence that looks like a plate)
                all_matches = re.findall(plate_pattern3, text_upper)
                if all_matches:
                    potential_plates = [m for m in all_matches if sum(c.isdigit() for c in m) >= 3]
                    if potential_plates:
                        return potential_plates[-1].replace(' ', '').replace('-', '').upper()
                
                return None
            
            # If plate_number is None for any row, search ALL other columns for plate numbers
            if 'plate_number' in df.columns:
                # Find rows where plate_number is None
                missing_plate_mask = df['plate_number'].isna() | (df['plate_number'] == '') | (df['plate_number'] == None)
                
                if missing_plate_mask.any():
                    # Search in ALL other columns (skip plate_number, account_number, account_type, truck_type)
                    columns_to_search = []
                    priority_columns = []
                    other_columns = []
                    
                    for col in df.columns:
                        col_lower = col.lower().strip()
                        # Skip columns we've already processed
                        if col in ['plate_number', 'account_number', 'account_type', 'truck_type']:
                            continue
                        # Priority columns: Remarks, Description, unnamed columns
                        if 'remark' in col_lower or 'description' in col_lower or 'unnamed' in col_lower:
                            priority_columns.append(col)
                        else:
                            other_columns.append(col)
                    
                    # Combine: priority columns first, then other columns
                    columns_to_search = priority_columns + other_columns
                    
                    # For each row with missing plate_number, search the columns
                    for idx in df[missing_plate_mask].index:
                        for col in columns_to_search:
                            if col in df.columns:
                                plate_from_col = extract_plate_from_text(df.at[idx, col])
                                if plate_from_col:
                                    df.at[idx, 'plate_number'] = plate_from_col
                                    break  # Found a plate number, move to next row
            
            # Validate account_type against /api/v1/account-types/ endpoint (UPLOAD VIEW)
            # Get valid account types from AccountType model
            valid_account_types = set(AccountType.objects.values_list('name', flat=True))
            
            if 'account_type' in df.columns:
                def validate_account_type(account_type_value):
                    if pd.isna(account_type_value) or account_type_value == '' or account_type_value is None:
                        return None
                    account_type_str = str(account_type_value).strip()
                    # Check if it's a valid account type (case-insensitive)
                    for valid_type in valid_account_types:
                        if account_type_str.lower() == valid_type.lower():
                            return valid_type
                    # If not found, return None (invalid account type - not in endpoint)
                    return None
                
                df['account_type'] = df['account_type'].apply(validate_account_type)
                
                # Filter out rows with invalid account types (None or empty) - UPLOAD VIEW
                # Only keep rows where account_type is valid (not None and not empty)
                df = df[df['account_type'].notna() & (df['account_type'] != '')]
            
            # Validate truck_type and plate_number against /api/v1/trucks/ endpoint (UPLOAD VIEW)
            # Get valid trucks from Truck model
            valid_trucks = Truck.objects.select_related('truck_type').all()
            
            # Standardize plate number function - removes spaces and hyphens for comparison
            def standardize_plate(plate_str):
                if pd.isna(plate_str) or plate_str == '' or plate_str is None:
                    return None
                # Remove all spaces, hyphens, underscores, and convert to uppercase for comparison
                return str(plate_str).strip().upper().replace(' ', '').replace('-', '').replace('_', '')
            
            # Create a mapping of normalized plate_number -> (original_plate_number, truck_type_name, truck_object)
            truck_plate_map = {}
            truck_type_names = set()
            for truck in valid_trucks:
                if truck.plate_number:
                    plate_key = standardize_plate(truck.plate_number)
                    # Store original plate number, truck type, and truck object
                    truck_plate_map[plate_key] = {
                        'plate_number': truck.plate_number,  # Original format from database
                        'truck_type': truck.truck_type.name if truck.truck_type else None,
                        'truck': truck
                    }
                    if truck.truck_type:
                        truck_type_names.add(truck.truck_type.name)
            
            # Validate truck_type and plate_number - both must exist in /api/v1/trucks/
            # Always validate if plate_number or truck_type columns exist (even if empty)
            def validate_truck_data(row):
                # Get parsed plate number (may already be normalized during parsing, but normalize again to be sure)
                parsed_plate = row.get('plate_number') if 'plate_number' in df.columns else None
                plate_num_normalized = standardize_plate(parsed_plate)
                truck_type_str = str(row.get('truck_type')).strip() if 'truck_type' in df.columns and not pd.isna(row.get('truck_type')) and str(row.get('truck_type')).strip() != '' else None
                
                # If plate_number is provided, validate it exists in trucks endpoint
                if plate_num_normalized:
                    # Normalize the parsed plate again to ensure it matches (handles "1101-939583" -> "1101939583")
                    truck_data = truck_plate_map.get(plate_num_normalized)
                    
                    if truck_data:
                        # Found matching truck in endpoint
                        original_plate = truck_data['plate_number']
                        db_truck_type = truck_data['truck_type']
                        
                        # If truck_type is also provided, validate it matches the truck's type
                        if truck_type_str:
                            if db_truck_type and db_truck_type.lower() == truck_type_str.lower():
                                return db_truck_type, original_plate
                            else:
                                # Plate exists but truck_type doesn't match - still return plate with correct truck_type
                                # The truck_type from the endpoint takes precedence
                                return db_truck_type, original_plate
                        else:
                            # Only plate_number provided, return truck's type and original plate number
                            return db_truck_type, original_plate
                    else:
                        # Plate number not found in trucks endpoint - return None
                        return None, None
                elif truck_type_str:
                    # Only truck_type provided, validate it exists in any truck
                    if truck_type_str.lower() in [t.lower() for t in truck_type_names]:
                        # Return the canonical truck type name
                        for valid_type in truck_type_names:
                            if valid_type.lower() == truck_type_str.lower():
                                return valid_type, None
                    else:
                        # Truck type not found in trucks endpoint
                        return None, None
                
                # No plate or truck_type provided, keep existing values
                return row.get('truck_type') if 'truck_type' in df.columns else None, row.get('plate_number') if 'plate_number' in df.columns else None
            
            # Apply validation to each row - UPLOAD VIEW
            if 'plate_number' in df.columns or 'truck_type' in df.columns:
                validated_data = df.apply(validate_truck_data, axis=1)
                # Extract truck_type and plate_number from tuples, handling None properly
                df['truck_type'] = validated_data.apply(lambda x: x[0] if x and x[0] is not None else None)
                df['plate_number'] = validated_data.apply(lambda x: x[1] if x and x[1] is not None else None)
            
            # Map Excel columns to model fields (handle various column name formats) - UPLOAD VIEW
            # First, define columns to drop (not needed for newledger.xlsx format)
            columns_to_drop_list = []
            for col in df.columns:
                col_lower = col.lower().strip()
                # Drop columns that are not needed
                if any(keyword in col_lower for keyword in [
                    'applied to invoice', 'item code', 'item type', 'cost', 
                    'payment type', 'customer', 'supplier', 'employee', 
                    'cash account', 'check no', 'check date', 'location', 
                    'project', 'balance'
                ]):
                    # But keep if it's "Reference No." which we'll handle separately
                    if 'reference no' not in col_lower:
                        columns_to_drop_list.append(col)
            
            # Also drop "QTY", "Price", "Description" (old), "Item" if they exist as separate columns
            # (we'll use Type as description, and QTY/Price from new format if needed)
            for col in df.columns:
                col_lower = col.lower().strip()
                if col_lower == 'qty' or col_lower == 'item':
                    columns_to_drop_list.append(col)
                # Drop old "Description" if we have "Type" column (Type is the new description)
                if col_lower == 'description' and any('type' in c.lower() and 'account' not in c.lower() and 'item' not in c.lower() for c in df.columns):
                    columns_to_drop_list.append(col)
            
            column_mapping = {}
            for col in df.columns:
                # Skip columns we're dropping
                if col in columns_to_drop_list:
                    continue
                    
                col_lower = col.lower().strip()
                
                # Map Account column - will be parsed separately
                if 'account' in col_lower and 'number' not in col_lower and 'type' not in col_lower:
                    # This will be parsed, not mapped directly
                    continue
                elif 'account' in col_lower and 'number' in col_lower:
                    column_mapping[col] = 'account_number'
                elif 'account' in col_lower and 'type' in col_lower and 'account_number' not in df.columns:
                    column_mapping[col] = 'account_type'
                elif 'truck' in col_lower and 'type' in col_lower and 'truck_type' not in df.columns:
                    column_mapping[col] = 'truck_type'
                elif ('plate' in col_lower or 'truck plate' in col_lower) and 'plate_number' not in df.columns:
                    column_mapping[col] = 'plate_number'
                # Map "Type" column to "description" (new format - Type is the description)
                elif col_lower == 'type' or (col_lower == 'type' and 'item' not in col_lower):
                    column_mapping[col] = 'description'
                # Also handle old "Description" column if Type doesn't exist
                elif 'description' in col_lower and 'description' not in column_mapping.values():
                    column_mapping[col] = 'description'
                elif 'debit' in col_lower:
                    column_mapping[col] = 'debit'
                elif 'credit' in col_lower:
                    column_mapping[col] = 'credit'
                elif 'final' in col_lower and ('total' in col_lower or 'tc' in col_lower):
                    column_mapping[col] = 'final_total'
                elif 'remarks' in col_lower:
                    column_mapping[col] = 'remarks'
                # Map "RR No." to reference_number (new format)
                elif 'rr no' in col_lower or col_lower == 'rr no.':
                    column_mapping[col] = 'reference_number'
                # Also handle old "Reference No." or "Reference Number" 
                elif ('reference no' in col_lower or 'reference number' in col_lower) and 'reference_number' not in column_mapping.values():
                    column_mapping[col] = 'reference_number'
                elif 'date' in col_lower:
                    column_mapping[col] = 'date'
                elif 'quantity' in col_lower:
                    column_mapping[col] = 'quantity'
                elif 'price' in col_lower:
                    column_mapping[col] = 'price'
                elif 'driver' in col_lower:
                    column_mapping[col] = 'driver'
                elif 'route' in col_lower:
                    column_mapping[col] = 'route'
                elif 'front' in col_lower and 'load' in col_lower:
                    column_mapping[col] = 'front_load'
                elif 'back' in col_lower and 'load' in col_lower:
                    column_mapping[col] = 'back_load'
            
            # If no description column was found, check Unnamed columns for description-like data
            if 'description' not in column_mapping.values():
                for col in df.columns:
                    if col in columns_to_drop_list:
                        continue
                    if 'unnamed' in col.lower():
                        # Check if this column contains description-like data
                        # Sample a few non-null values to determine if it's a description column
                        sample_values = df[col].dropna().astype(str).head(10).tolist()
                        # Check if values contain common description keywords
                        description_keywords = ['beginning balance', 'receive inventory', 'inventory withdrawal', 'funds', 'transfer']
                        if any(any(keyword in str(val).lower() for keyword in description_keywords) for val in sample_values):
                            column_mapping[col] = 'description'
                            break
            
            # Drop unwanted columns BEFORE renaming
            df = df.drop(columns=columns_to_drop_list, errors='ignore')
            
            # Rename columns
            df = df.rename(columns=column_mapping)
            
            # Handle "Beginning Balance" - set ALL numeric fields to 0 (but don't delete the row)
            # Search ALL columns for "Beginning Balance" text BEFORE removing Unnamed columns
            # This ensures we catch "Beginning Balance" even if it's in an "Unnamed" column
            beginning_balance_mask = df.astype(str).apply(lambda x: x.str.contains('Beginning Balance', case=False, na=False)).any(axis=1)
            
            # Set all numeric/decimal fields to 0
            # Use original column names first, then mapped names
            numeric_field_names = ['debit', 'credit', 'final_total', 'Debit', 'Credit', 'Final Total', 'Final Total', 'QTY (Fuel)', 'Unit Cost']
            for field in numeric_field_names:
                if field in df.columns:
                    # Ensure we convert to numeric first, then set to 0
                    df[field] = pd.to_numeric(df[field], errors='coerce')
                    df.loc[beginning_balance_mask, field] = 0
            
            # Remove any remaining Account-related columns that aren't the parsed ones (Account, Account.1, etc.) - UPLOAD VIEW
            # But only drop if they exist and haven't been mapped yet
            columns_to_drop = [col for col in df.columns if col.lower().startswith('account') 
                              and col.lower() not in ['account_number', 'account_type'] 
                              and col not in column_mapping]
            df = df.drop(columns=columns_to_drop, errors='ignore')
            
            # Remove any Unnamed columns - UPLOAD VIEW (but keep description if it was mapped from Unnamed)
            columns_to_drop = [col for col in df.columns if 'unnamed' in col.lower() and col not in column_mapping]
            df = df.drop(columns=columns_to_drop, errors='ignore')
            
            # Drop old "Reference No." if we've mapped "RR No." to reference_number
            if 'reference_number' in column_mapping.values():
                # Find which column was mapped to reference_number
                mapped_ref_col = [col for col, mapped in column_mapping.items() if mapped == 'reference_number']
                if mapped_ref_col:
                    # Drop other reference columns that weren't mapped
                    ref_cols_to_drop = [col for col in df.columns 
                                       if ('reference' in col.lower() or 'rr no' in col.lower()) 
                                       and col not in mapped_ref_col 
                                       and col not in column_mapping]
                    df = df.drop(columns=ref_cols_to_drop, errors='ignore')
            
            # Handle "Beginning Balance" again after column mapping (to catch mapped column names)
            beginning_balance_mask = df.astype(str).apply(lambda x: x.str.contains('Beginning Balance', case=False, na=False)).any(axis=1)
            numeric_fields = ['debit', 'credit', 'final_total', 'quantity', 'price']
            for field in numeric_fields:
                if field in df.columns:
                    # Ensure we convert to numeric first, then set to 0
                    df[field] = pd.to_numeric(df[field], errors='coerce')
                    df.loc[beginning_balance_mask, field] = 0
            
            # Get valid routes from database - UPLOAD VIEW (before parsing functions)
            valid_routes_upload = set(Route.objects.values_list('name', flat=True))
            
            # Enhanced parsing functions based on the image data patterns - UPLOAD VIEW
            def extract_driver_from_remarks(remarks):
                if pd.isna(remarks) or remarks is None:
                    return None
                remarks_str = str(remarks)
                
                # Known drivers list
                drivers = [
                    'Edgardo Agapay', 'Romel Bantilan', 'Reynaldo Rizalda', 'Francis Ariglado',
                    'Roque Oling', 'Pablo Hamo', 'Albert Saavedra', 'Jimmy Oclarit', 'Nicanor',
                    'Arnel Duhilag', 'Benjamin Aloso', 'Roger', 'Joseph Bahan', 'Doming',
                    'Jun2x Campaña', 'Jun2x Toledo', 'Ronie Babanto'
                ]
                
                # Pattern 1: Check for known drivers first (exact match)
                for driver in drivers:
                    if driver in remarks_str:
                        return driver
                
                # Pattern 2: Handle multiple drivers with "/" (e.g., "Jimmy Oclarit/Romel Bantilan")
                # Look for pattern: "Name1/Name2:" before route
                multi_driver_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*):'
                multi_match = re.search(multi_driver_pattern, remarks_str)
                if multi_match:
                    driver1 = multi_match.group(1).strip()
                    driver2 = multi_match.group(2).strip()
                    # Verify at least one is a known driver
                    for driver in drivers:
                        if driver in driver1 or driver in driver2:
                            return f"{driver1}/{driver2}"
                
                # Pattern 3: Extract driver from "LRO: XXLiters Fuel and Oil [DRIVER]:"
                # This handles cases like "LRO: 140Liters Fuel and Oil Roque Oling:"
                lro_pattern = r'LRO:\s*\d+Liters\s+Fuel\s+and\s+Oil\s+(?:[A-Z]+-\d+\s+)?([A-Za-z\s]+?)(?::|;)'
                lro_match = re.search(lro_pattern, remarks_str)
                if lro_match:
                    potential_driver = lro_match.group(1).strip()
                    # Clean up and validate
                    if len(potential_driver) > 2 and not any(word in potential_driver.lower() for word in ['lro', 'liters', 'fuel', 'oil']):
                        # Check if it's a known driver or looks like a name
                        for driver in drivers:
                            if driver.lower() in potential_driver.lower():
                                return driver
                        # If not known but looks like a name (2+ words), return it
                        if len(potential_driver.split()) >= 2:
                            return potential_driver
                
                # Pattern 4: Look for "Name:" pattern (but filter out routes and common words)
                name_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+):'
                matches = re.finditer(name_pattern, remarks_str)
                for match in matches:
                    potential_driver = match.group(1).strip()
                    # Skip if it looks like a route
                    if any(route_word in potential_driver.upper() for route_word in ['PAG-', 'CDO', 'ILIGAN', 'STRIKE']):
                        continue
                    # Skip common non-driver words
                    if any(word in potential_driver.lower() for word in ['lro', 'liters', 'fuel', 'oil', 'deliver', 'transfer']):
                        continue
                    # Check if it's a known driver
                    for driver in drivers:
                        if driver.lower() == potential_driver.lower():
                            return driver
                    # If it has 2+ words and looks like a name, return it
                    if len(potential_driver.split()) >= 2:
                        return potential_driver
                
                return None

            def extract_route_from_remarks(remarks):
                if pd.isna(remarks) or remarks is None:
                    return None
                remarks_str = str(remarks)
                
                # Get valid routes from database (case-insensitive matching)
                def is_valid_route(route_name):
                    """Check if route exists in database (case-insensitive)"""
                    if not route_name:
                        return None
                    route_clean = str(route_name).strip()
                    for valid_route in valid_routes_upload:
                        if route_clean.upper() == valid_route.upper():
                            return valid_route  # Return the canonical name from database
                    return None  # Route not in database
                
                # Pattern 1: Look for route with colon after it (e.g., "PAG-ILIGAN:" or "CDO-LNO:")
                # This pattern matches: [A-Z]+-[A-Z]+ or any route format followed by colon
                # First, try to match any route from database that appears with a colon
                for route in valid_routes_upload:
                    # Escape special regex characters in route name
                    route_escaped = re.escape(route)
                    pattern = rf'{route_escaped}\s*:'
                    match = re.search(pattern, remarks_str, re.IGNORECASE)
                    if match:
                        validated = is_valid_route(route)
                        if validated:
                            return validated
                
                # Pattern 2: Look for routes in specific contexts (after driver name or plate number)
                # E.g., "Juan Dela Cruz: CDO-LNO:" or "LAH-2577: CDO-LNO:"
                # Match pattern: ": [ROUTE]:" where ROUTE can be various formats
                context_pattern = r':\s*([A-Z0-9]+(?:-[A-Z0-9]+)+|[A-Z\s]+?)\s*:'
                matches = re.finditer(context_pattern, remarks_str, re.IGNORECASE)
                for match in matches:
                    potential_route = match.group(1).strip()
                    # Skip if it looks like a driver name (has lowercase letters in middle)
                    if re.search(r'[a-z]', potential_route) and len(potential_route.split()) > 1:
                        continue
                    validated = is_valid_route(potential_route)
                    if validated:
                        return validated
                
                # Pattern 3: Check for routes anywhere in the text (case-insensitive)
                # This is a fallback - check if any route name appears in the text
                for route in valid_routes_upload:
                    route_escaped = re.escape(route)
                    # Match route as whole word or with word boundaries
                    pattern = rf'\b{route_escaped}\b'
                    if re.search(pattern, remarks_str, re.IGNORECASE):
                        validated = is_valid_route(route)
                        if validated:
                            return validated
                
                return None

            def extract_loads_from_remarks(remarks):
                """
                Extract front and back loads ONLY if they appear in a slash pattern, e.g. 'Strike/Cement'.
                Ignores all other forms such as 'deliver ug cemento' or 'backload humay'.
                Validates against LoadType database.
                """
                if pd.isna(remarks) or remarks is None:
                    return None, None
                remarks_str = str(remarks)

                front_load = None
                back_load = None
                
                # Get valid load types from database
                valid_load_types = [lt.name for lt in LoadType.objects.all()]

                # Helper function to clean load value - remove route names, delivery words, etc.
                def clean_load_extracted(load_str):
                    """Clean extracted load value by removing route names and delivery words"""
                    if not load_str:
                        return None
                    
                    cleaned = str(load_str).strip()
                    
                    # Remove route indicators (PAG-, DUMINGAG, etc.)
                    route_patterns = [
                        r'\bPAG-[A-Z]+\b',
                        r'\bDUMINGAG\b',
                        r'\bDIMATALING\b',
                        r'\bCDO\b',
                        r'\bILIGAN\b',
                        r'\bOPEX\b',
                        r'\bPAGADIAN\b'
                    ]
                    for pattern in route_patterns:
                        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
                    
                    # Remove delivery/action words
                    delivery_words = [
                        r'\bdeliver\b',
                        r'\bDeliver\b',
                        r'\bDELIVER\b',
                        r'\bpara\b',
                        r'\bPara\b',
                        r'\bsa\b',
                        r'\bto\b',
                        r'\bug\b',
                        r'\bni\b',
                        r'\bmao\b'
                    ]
                    for word in delivery_words:
                        cleaned = re.sub(word, '', cleaned, flags=re.IGNORECASE)
                    
                    # Remove numbers and special characters at the end
                    cleaned = re.sub(r'[:\.,;]+$', '', cleaned)
                    cleaned = re.sub(r'\s+\+\d+.*$', '', cleaned)  # Remove "+165ltrs" etc.
                    cleaned = re.sub(r'\s+\d+.*$', '', cleaned)  # Remove trailing numbers
                    
                    # Clean up multiple spaces
                    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                    
                    return cleaned if cleaned else None

                # Helper function to get Strike load type from database
                def get_strike_load():
                    """Get Strike load type from database, case-insensitive"""
                    strike_load = next((lt for lt in valid_load_types if lt.lower() == 'strike'), None)
                    return strike_load if strike_load else 'Strike'  # Fallback to 'Strike' if not in DB
                
                # Helper function to handle single load with default to Strike
                def handle_single_load(front, back):
                    """Handle case where one load is valid and other is missing - default missing to Strike"""
                    front_valid = front and is_valid_load(front, valid_load_types)
                    back_valid = back and is_valid_load(back, valid_load_types)
                    
                    if front_valid and back_valid:
                        # Both valid - return both
                        return clean_load_value(front, valid_load_types), clean_load_value(back, valid_load_types)
                    elif front_valid and not back_valid:
                        # Front valid, back missing/invalid - set back to "Strike"
                        strike_load = get_strike_load()
                        return clean_load_value(front, valid_load_types), strike_load
                    elif back_valid and not front_valid:
                        # Back valid, front missing/invalid - set front to "Strike"
                        strike_load = get_strike_load()
                        return strike_load, clean_load_value(back, valid_load_types)
                    return None, None

                # Pattern 1: "load1/load2:" - with trailing colon (most common)
                # Examples: "Strike/Cement:", "RH Holcim/Cement:", "RH Holcim/Backload CDO:", "Strike/cemento:"
                load_pattern_with_colon = r':\s*([A-Za-z\s]+)/([A-Za-z\s]+):'
                match = re.search(load_pattern_with_colon, remarks_str)
                if match:
                    potential_front = clean_load_extracted(match.group(1))
                    potential_back = clean_load_extracted(match.group(2))
                    result = handle_single_load(potential_front, potential_back)
                    if result[0] and result[1]:
                        return result

                # Pattern 2: "load1/load2" at end of string (no trailing colon)
                # Examples: "Strike/Cement", "Cement/Backload CDO"
                load_pattern_end = r':\s*([A-Za-z\s]+)/([A-Za-z\s]+)\s*$'
                match = re.search(load_pattern_end, remarks_str)
                if match:
                    potential_front = clean_load_extracted(match.group(1))
                    potential_back = clean_load_extracted(match.group(2))
                    result = handle_single_load(potential_front, potential_back)
                    if result[0] and result[1]:
                        return result

                # Pattern 3: "load1/load2" followed by text (no colon, but with separator words)
                # Examples: "Strike/Cement deliver to caluma", "Strike/Cement +120ltrs", "RH Holcim/Cement DUMINGAG Deliver"
                load_pattern_with_text = r':\s*([A-Za-z\s]+)/([A-Za-z\s]+?)(?:\s+(?:deliver|Deliver|DELIVER|para|Para|sa|to|ug|\+|:|\d|DUMINGAG|DIMATALING|PAG-|$))'
                match = re.search(load_pattern_with_text, remarks_str, re.IGNORECASE)
                if match:
                    potential_front = clean_load_extracted(match.group(1))
                    potential_back = clean_load_extracted(match.group(2))
                    result = handle_single_load(potential_front, potential_back)
                    if result[0] and result[1]:
                        return result

                # Pattern 4: "load1/load2" anywhere in the string with word boundaries
                # Examples: "PAG-ILIGAN: Strike/Cement: additional notes"
                load_pattern_general = r'\b([A-Za-z\s]{3,})/([A-Za-z\s]{3,})\b'
                match = re.search(load_pattern_general, remarks_str)
                if match:
                    potential_front = clean_load_extracted(match.group(1))
                    potential_back = clean_load_extracted(match.group(2))

                    # Make sure neither part looks like a route or driver name
                    route_indicators = ['PAG-', 'CDO', 'ILIGAN', 'OPEX', 'PAGADIAN', 'DUMINGAG', 'DIMATALING']
                    is_route = any(indicator in (potential_front or '').upper() or indicator in (potential_back or '').upper()
                                for indicator in route_indicators)

                    if not is_route:
                        result = handle_single_load(potential_front, potential_back)
                        if result[0] and result[1]:
                            return result

                # No slash pattern found - return None for both
                return None, None

            # Validate drivers against database - only keep drivers that exist in database (UPLOAD VIEW)
            if 'driver' in df.columns:
                # Get valid drivers from database (case-insensitive matching)
                valid_drivers_db_upload = set(Driver.objects.values_list('name', flat=True))
                
                def validate_driver(driver_value):
                    """Validate driver exists in database (case-insensitive)"""
                    if pd.isna(driver_value) or driver_value == '' or driver_value is None:
                        return None  # Empty driver is allowed
                    driver_str = str(driver_value).strip()
                    # Check if it's a valid driver (case-insensitive)
                    for valid_driver in valid_drivers_db_upload:
                        if driver_str.lower() == valid_driver.lower():
                            return valid_driver  # Return canonical name from database
                    # Invalid driver - return None (but don't filter row, just clear driver)
                    return None
                
                # Validate existing driver column values
                df['driver'] = df['driver'].apply(validate_driver)
            
            # Validate load types against database - only keep loads that exist in database (UPLOAD VIEW)
            if 'front_load' in df.columns or 'back_load' in df.columns:
                # Get valid load types from database (case-insensitive matching)
                valid_load_types_db_upload = set(LoadType.objects.values_list('name', flat=True))
                
                def validate_load_type(load_value):
                    """Validate load type exists in database (case-insensitive)"""
                    if pd.isna(load_value) or load_value == '' or load_value is None:
                        return None  # Empty load is allowed
                    load_str = str(load_value).strip()
                    # Clean the load value first
                    load_cleaned = clean_load_value(load_str, valid_load_types_db_upload)
                    if load_cleaned:
                        # Check if it's a valid load type (case-insensitive)
                        for valid_load in valid_load_types_db_upload:
                            if load_cleaned.lower() == valid_load.lower():
                                return valid_load  # Return canonical name from database
                    # Invalid load - return None (but don't filter row, just clear load)
                    return None
                
                # Validate existing load column values
                if 'front_load' in df.columns:
                    df['front_load'] = df['front_load'].apply(validate_load_type)
                if 'back_load' in df.columns:
                    df['back_load'] = df['back_load'].apply(validate_load_type)

            # Apply parsing to extract driver, route, front_load, back_load from remarks
            # Always extract from remarks to override any existing values
            if 'remarks' in df.columns:
                # Get valid load types for validation after extraction (UPLOAD VIEW)
                valid_load_types_db_after_extraction = set(LoadType.objects.values_list('name', flat=True))
                
                for index, row in df.iterrows():
                    # Always extract driver from remarks if available
                    extracted_driver = extract_driver_from_remarks(row.get('remarks'))
                    if extracted_driver:
                        df.at[index, 'driver'] = extracted_driver
                    
                    # Always extract route from remarks if available
                    extracted_route = extract_route_from_remarks(row.get('remarks'))
                    if extracted_route:
                        df.at[index, 'route'] = extracted_route
                    
                    # Only extract loads if BOTH driver AND route are present
                    # This prevents extracting maintenance items like "Fan Belt/Grease" as loads
                    if extracted_driver and extracted_route:
                        extracted_front, extracted_back = extract_loads_from_remarks(row.get('remarks'))
                        if extracted_front:
                            # Clean the front load value and validate against database
                            cleaned_front = clean_load_value(extracted_front, valid_load_types_db_after_extraction)
                            if cleaned_front:
                                # Validate against database
                                for valid_load in valid_load_types_db_after_extraction:
                                    if cleaned_front.lower() == valid_load.lower():
                                        df.at[index, 'front_load'] = valid_load  # Use canonical name from database
                                        break
                        if extracted_back:
                            # Clean the back load value and validate against database
                            cleaned_back = clean_load_value(extracted_back, valid_load_types_db_after_extraction)
                            if cleaned_back:
                                # Validate against database
                                for valid_load in valid_load_types_db_after_extraction:
                                    if cleaned_back.lower() == valid_load.lower():
                                        df.at[index, 'back_load'] = valid_load  # Use canonical name from database
                                        break
            
            # Clean and convert data
            def clean_decimal(value):
                if pd.isna(value) or value == '' or value == 'nan':
                    return 0
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return 0
            
            # Convert numeric fields
            numeric_fields = ['debit', 'credit', 'final_total', 'quantity', 'price']
            for field in numeric_fields:
                if field in df.columns:
                    df[field] = df[field].apply(clean_decimal)
            
            # Convert date field
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            # Clean string fields
            string_fields = ['account_number', 'account_type', 'truck_type', 'plate_number', 
                           'description', 'remarks', 'reference_number', 'driver', 'route', 
                           'front_load', 'back_load']
            for field in string_fields:
                if field in df.columns:
                    df[field] = df[field].astype(str).replace('nan', '').replace('None', '')
            
            # Calculate final_total from Debit and Credit if final_total column doesn't exist
            if 'debit' in df.columns and 'credit' in df.columns:
                # Convert to numeric, handling NaN values
                df['debit'] = pd.to_numeric(df['debit'], errors='coerce').fillna(0)
                df['credit'] = pd.to_numeric(df['credit'], errors='coerce').fillna(0)
                
                # If final_total column doesn't exist, create it from debit - credit
                if 'final_total' not in df.columns:
                    df['final_total'] = df['debit'] - df['credit']
                else:
                    # If final_total exists but is NaN/empty, calculate from debit - credit
                    df['final_total'] = pd.to_numeric(df['final_total'], errors='coerce')
                    df['final_total'] = df['final_total'].fillna(df['debit'] - df['credit'])
            
            # For Hauling Income accounts, ensure final_total is positive (use abs if negative)
            if 'account_type' in df.columns and 'final_total' in df.columns:
                hauling_income_mask = df['account_type'].astype(str).str.contains('Hauling Income', case=False, na=False)
                # Apply abs() to make positive if negative
                df.loc[hauling_income_mask, 'final_total'] = df.loc[hauling_income_mask, 'final_total'].apply(lambda x: abs(x) if x < 0 else x)
            
            # Create accounts
            created_count = 0
            errors = []
            parsing_stats = {
                'drivers_extracted': 0,
                'routes_extracted': 0,
                'loads_extracted': 0
            }
            duplicate_count = 0
            batch_created_at = timezone.now()
            existing_account_map = {}

            existing_accounts = TruckingAccount.objects.all().values(
                'account_number',
                'account_type_id',
                'date',
                'created_at',
            )
            for record in existing_accounts:
                key = (
                    record['account_number'],
                    record['account_type_id'],
                    record['date'],
                )
                if key not in existing_account_map:
                    existing_account_map[key] = record['created_at']
            
            for index, row in df.iterrows():
                try:
                    # Skip rows with missing required fields
                    if pd.isna(row.get('account_number')) or row.get('account_number') == '':
                        continue
                    
                    # Track parsing statistics
                    if row.get('driver') and row.get('driver') != '':
                        parsing_stats['drivers_extracted'] += 1
                    if row.get('route') and row.get('route') != '':
                        parsing_stats['routes_extracted'] += 1
                    if row.get('front_load') and row.get('front_load') != '':
                        parsing_stats['loads_extracted'] += 1
                    
                    # Resolve Driver by name (only use existing drivers from database, don't create new ones)
                    driver_instance = None
                    route_instance = None
                    if row.get('driver') and str(row.get('driver')).strip() != '':
                        driver_name_raw = str(row.get('driver')).strip()
                        # Only use existing drivers - don't create new ones
                        driver_instance = Driver.objects.filter(name__iexact=driver_name_raw).first()
                        # If driver not found in database, set to None (entry will still be uploaded without driver)
                    if row.get('route') and str(row.get('route')).strip() != '':
                        route_name_raw = str(row.get('route')).strip()
                        existing_route = Route.objects.filter(name__iexact=route_name_raw).first()
                        route_instance = existing_route or Route.objects.create(name=route_name_raw)

                    # Resolve AccountType by name (create if not exist)
                    account_type_instance = None
                    if row.get('account_type') and str(row.get('account_type')).strip() != '':
                        account_type_name = str(row.get('account_type')).strip()
                        account_type_instance, _ = AccountType.objects.get_or_create(name=account_type_name)

                    # Normalize account number
                    raw_account_number = row.get('account_number', '')
                    if pd.isna(raw_account_number):
                        account_number_value = ''
                    else:
                        account_number_value = str(raw_account_number).strip()

                    # Normalize date value
                    account_date_value = None
                    raw_date_value = row.get('date')
                    if pd.notna(raw_date_value) and raw_date_value != '':
                        if isinstance(raw_date_value, pd.Timestamp):
                            account_date_value = raw_date_value.date()
                        elif isinstance(raw_date_value, datetime):
                            account_date_value = raw_date_value.date()
                        elif isinstance(raw_date_value, date):
                            account_date_value = raw_date_value
                        else:
                            try:
                                account_date_value = pd.to_datetime(raw_date_value).date()
                            except Exception:
                                account_date_value = None

                    dedup_key = (
                        account_number_value,
                        account_type_instance.id if account_type_instance else None,
                        account_date_value,
                    )

                    if dedup_key in existing_account_map:
                        duplicate_count += 1
                        errors.append(
                            f"Row {index + 1}: Duplicate entry detected for account {account_number_value} (original created_at {existing_account_map[dedup_key]}). Skipped."
                        )
                        continue

                    # Resolve Truck by plate number, truck type, and company
                    truck_instance = None
                    plate_number = standardize_plate_number(row.get('plate_number', ''))
                    truck_type_str = str(row.get('truck_type', '')).strip() if pd.notna(row.get('truck_type')) else ''
                    company_str = str(row.get('company', '')).strip() if pd.notna(row.get('company')) else ''
                    
                    if plate_number:
                        # Get or create TruckType if provided
                        truck_type_instance = None
                        if truck_type_str:
                            truck_type_instance, _ = TruckType.objects.get_or_create(name=truck_type_str)
                        
                        # Check if truck already exists
                        existing_truck = Truck.objects.filter(plate_number=plate_number).first()
                        
                        if existing_truck:
                            # Update existing truck if new data is provided
                            updated = False
                            if truck_type_instance and not existing_truck.truck_type:
                                existing_truck.truck_type = truck_type_instance
                                updated = True
                            elif truck_type_instance and existing_truck.truck_type and existing_truck.truck_type.name != truck_type_str:
                                existing_truck.truck_type = truck_type_instance
                                updated = True
                            
                            if company_str and not existing_truck.company:
                                existing_truck.company = company_str
                                updated = True
                            elif company_str and existing_truck.company != company_str:
                                existing_truck.company = company_str
                                updated = True
                            
                            if updated:
                                existing_truck.save()
                            
                            truck_instance = existing_truck
                        else:
                            # Create new truck
                            truck_instance = Truck.objects.create(
                                plate_number=plate_number,
                                truck_type=truck_type_instance,
                                company=company_str if company_str else None
                            )

                    # Resolve LoadType for front_load by name (only use existing loads from database, don't create new ones)
                    front_load_instance = None
                    if row.get('front_load') and str(row.get('front_load')).strip() != '':
                        front_load_raw = str(row.get('front_load')).strip()
                        front_load_cleaned = clean_load_value(front_load_raw)
                        if front_load_cleaned:
                            # Only use existing load types - don't create new ones
                            front_load_instance = LoadType.objects.filter(name__iexact=front_load_cleaned).first()
                            # If load not found in database, set to None (entry will still be uploaded without load)

                    # Resolve LoadType for back_load by name (only use existing loads from database, don't create new ones)
                    back_load_instance = None
                    if row.get('back_load') and str(row.get('back_load')).strip() != '':
                        back_load_raw = str(row.get('back_load')).strip()
                        back_load_cleaned = clean_load_value(back_load_raw)
                        if back_load_cleaned:
                            # Only use existing load types - don't create new ones
                            back_load_instance = LoadType.objects.filter(name__iexact=back_load_cleaned).first()
                            # If load not found in database, set to None (entry will still be uploaded without load)

                    # Create TruckingAccount instance
                    account = TruckingAccount(
                        account_number=account_number_value,
                        account_type=account_type_instance,
                        truck=truck_instance,
                        description=row.get('description', ''),
                        debit=row.get('debit', 0),
                        credit=row.get('credit', 0),
                        final_total=row.get('final_total', 0),
                        remarks=row.get('remarks', ''),
                        reference_number=row.get('reference_number', '') if row.get('reference_number') != '' else None,
                        date=account_date_value,
                        quantity=row.get('quantity') if not pd.isna(row.get('quantity')) and row.get('quantity') != 0 else None,
                        price=row.get('price') if not pd.isna(row.get('price')) and row.get('price') != 0 else None,
                        driver=driver_instance,
                        route=route_instance,
                        front_load=front_load_instance,
                        back_load=back_load_instance,
                    )

                    account.created_at = batch_created_at
                    
                    account.save()
                    created_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {index + 1}: {str(e)}")
                    continue
            
            return Response({
                'message': f'Successfully created {created_count} trucking accounts',
                'created_count': created_count,
                'duplicates_skipped': duplicate_count,
                'parsing_stats': parsing_stats,
                'errors': errors[:10] if errors else []  # Show first 10 errors
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TruckUploadView(APIView):
    """
    POST: Upload Excel file to bulk create/update trucks
    Expected headers: TRUCK PLATE, Truck Type, Company
    """
    def post(self, request):
        try:
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            file = request.FILES['file']
            
            # Read Excel file
            df = pd.read_excel(file)
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Map Excel columns to expected names (case-insensitive)
            column_mapping = {}
            for col in df.columns:
                col_lower = col.lower()
                if col_lower in ['truck plate', 'plate', 'plate number', 'plate_number']:
                    column_mapping[col] = 'plate_number'
                elif col_lower in ['truck type', 'truck_type', 'type']:
                    column_mapping[col] = 'truck_type'
                elif col_lower in ['company']:
                    column_mapping[col] = 'company'
            
            # Rename columns
            df = df.rename(columns=column_mapping)
            
            # Track results
            created_count = 0
            updated_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    # Get plate number (required)
                    plate_number = standardize_plate_number(row.get('plate_number', ''))
                    if not plate_number:
                        errors.append(f"Row {index + 1}: Plate number is required")
                        error_count += 1
                        continue
                    
                    # Get truck type and company (optional)
                    truck_type_str = str(row.get('truck_type', '')).strip() if pd.notna(row.get('truck_type')) else ''
                    company_str = str(row.get('company', '')).strip() if pd.notna(row.get('company')) else ''
                    
                    # Resolve TruckType if provided
                    truck_type_instance = None
                    if truck_type_str:
                        truck_type_instance, _ = TruckType.objects.get_or_create(name=truck_type_str)
                    
                    # Check if truck already exists
                    existing_truck = Truck.objects.filter(plate_number=plate_number).first()
                    
                    if existing_truck:
                        # Update existing truck
                        if truck_type_instance:
                            existing_truck.truck_type = truck_type_instance
                        if company_str:
                            existing_truck.company = company_str
                        existing_truck.save()
                        updated_count += 1
                    else:
                        # Create new truck
                        Truck.objects.create(
                            plate_number=plate_number,
                            truck_type=truck_type_instance,
                            company=company_str if company_str else None
                        )
                        created_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {index + 1}: {str(e)}")
                    error_count += 1
                    continue
            
            return Response({
                'message': f'Successfully processed {created_count + updated_count} trucks',
                'created_count': created_count,
                'updated_count': updated_count,
                'error_count': error_count,
                'errors': errors[:10] if errors else []  # Show first 10 errors
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

