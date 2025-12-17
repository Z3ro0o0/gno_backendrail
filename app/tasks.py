"""
Celery tasks for background processing
"""
import os
import pandas as pd
import json
from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from django.db import transaction
from datetime import datetime, date
import re
from .models import (
    TruckingAccount, Driver, Route, Truck, TruckType, 
    AccountType, LoadType
)
from .trucking_upload_view import clean_load_value, is_valid_load


def normalize_account_number_for_dedup(account_number):
    """Normalize account number for duplicate detection"""
    if not account_number:
        return ''
    return str(account_number).strip().replace(' ', '').replace('-', '').upper()


def normalize_date_for_dedup(date_value):
    """Normalize date for duplicate detection"""
    if pd.isna(date_value) or date_value == '':
        return None
    try:
        if isinstance(date_value, str):
            # Try parsing different date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']:
                try:
                    return pd.to_datetime(date_value, format=fmt).date()
                except:
                    continue
        return pd.to_datetime(date_value).date()
    except:
        return None


def standardize_plate_number(plate_number):
    """Standardize plate number format"""
    if not plate_number or pd.isna(plate_number):
        return ''
    return str(plate_number).strip().replace(' ', '').replace('-', '').upper()


@shared_task(bind=True)
def process_trucking_upload(self, file_path, exclude_preview_indices=None, task_id=None):
    """
    Background task to process trucking account upload
    This includes ALL the parsing logic from the synchronous upload view
    """
    try:
        # Set initial progress
        progress_key = f'upload_progress_{task_id}'
        cache.set(progress_key, {
            'status': 'processing',
            'progress': 0,
            'total_rows': 0,
            'processed_rows': 0,
            'created_count': 0,
            'duplicate_count': 0,
            'error_count': 0,
            'errors': [],
            'message': 'Starting upload...'
        }, timeout=3600)
        
        # Read Excel file (try without skiprows first, then with skiprows=7 for backward compatibility)
        try:
            df = pd.read_excel(file_path)
            df.columns = df.columns.str.strip()
            # Check if we have expected columns for new format
            has_new_format = any('account' in col.lower() for col in df.columns) and \
                           any('type' in col.lower() and 'account' not in col.lower() and 'item' not in col.lower() for col in df.columns)
            
            if not has_new_format:
                # Reset and try with skiprows
                df = pd.read_excel(file_path, skiprows=7)
                df.columns = df.columns.str.strip()
        except:
            # If reading fails, try with skiprows for backward compatibility
            df = pd.read_excel(file_path, skiprows=7)
            df.columns = df.columns.str.strip()
        
        # Remove rows with 'Total for' in ANY column BEFORE parsing
        df = df[~df.astype(str).apply(lambda x: x.str.contains('Total for', case=False, na=False)).any(axis=1)]
        
        # Remove completely empty rows before resetting index
        df = df[~df.isnull().all(axis=1)]
        
        # Reset index to ensure sequential indices (0, 1, 2, ...) that match preview indices
        df = df.reset_index(drop=True)
        
        # Handle excluded preview indices (rows deleted in preview)
        if exclude_preview_indices:
            exclude_set = set(exclude_preview_indices)
            df = df[~df.index.isin(exclude_set)]
            df = df.reset_index(drop=True)
        
        total_rows = len(df)
        
        # Update progress
        cache.set(progress_key, {
            'status': 'processing',
            'progress': 5,
            'total_rows': total_rows,
            'processed_rows': 0,
            'created_count': 0,
            'duplicate_count': 0,
            'error_count': 0,
            'errors': [],
            'message': f'Processing {total_rows} rows...'
        }, timeout=3600)
        
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
            
            # Look for truck type in subsequent parts
            truck_type_keywords = ['Trailer', 'Forward', '10-wheeler']
            for part in parts[2:]:
                if any(keyword in part for keyword in truck_type_keywords):
                    truck_type = part
                    break
            
            # Look for plate number pattern
            plate_pattern1 = r'([A-Z]{2,4}[\s\-]*\d{3,6})'
            plate_pattern2 = r'(\d{3,4}[\s\-]*\d{3,9})'
            plate_pattern3 = r'([A-Z0-9]{4,12})'
            
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
                        # Only use if it has at least 3 digits
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
            df['plate_number'] = parsed_data.apply(lambda x: x[3] if x else None)
            # Remove the original Account column
            df = df.drop(columns=[account_col], errors='ignore')
        
        # Helper function to extract plate number from any text using the same patterns
        def extract_plate_from_text(text_value):
            """Extract plate number from any text value using the same patterns as parse_account_column"""
            if pd.isna(text_value) or text_value == '':
                return None
            
            text_str = str(text_value).strip()
            text_upper = text_str.upper()
            
            plate_pattern1 = r'([A-Z]{2,4}[\s\-]*\d{3,6})'
            plate_pattern2 = r'(\d{3,4}[\s\-]+\d{3,9})'
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
            missing_plate_mask = df['plate_number'].isna() | (df['plate_number'] == '') | (df['plate_number'] == None)
            
            if missing_plate_mask.any():
                columns_to_search = []
                priority_columns = []
                other_columns = []
                
                for col in df.columns:
                    col_lower = col.lower().strip()
                    if col in ['plate_number', 'account_number', 'account_type', 'truck_type']:
                        continue
                    if 'remark' in col_lower or 'description' in col_lower or 'unnamed' in col_lower:
                        priority_columns.append(col)
                    else:
                        other_columns.append(col)
                
                columns_to_search = priority_columns + other_columns
                
                for idx in df[missing_plate_mask].index:
                    for col in columns_to_search:
                        if col in df.columns:
                            plate_from_col = extract_plate_from_text(df.at[idx, col])
                            if plate_from_col:
                                df.at[idx, 'plate_number'] = plate_from_col
                                break
        
        # Validate account_type against database
        valid_account_types = set(AccountType.objects.values_list('name', flat=True))
        
        if 'account_type' in df.columns:
            def validate_account_type(account_type_value):
                if pd.isna(account_type_value) or account_type_value == '' or account_type_value is None:
                    return None
                account_type_str = str(account_type_value).strip()
                for valid_type in valid_account_types:
                    if account_type_str.lower() == valid_type.lower():
                        return valid_type
                return None
            
            df['account_type'] = df['account_type'].apply(validate_account_type)
            df = df[df['account_type'].notna() & (df['account_type'] != '')]
        
        # Validate truck_type and plate_number against database
        valid_trucks = Truck.objects.select_related('truck_type').all()
        
        def standardize_plate(plate_str):
            if pd.isna(plate_str) or plate_str == '' or plate_str is None:
                return None
            return str(plate_str).strip().upper().replace(' ', '').replace('-', '').replace('_', '')
        
        truck_plate_map = {}
        truck_type_names = set()
        for truck in valid_trucks:
            if truck.plate_number:
                plate_key = standardize_plate(truck.plate_number)
                truck_plate_map[plate_key] = {
                    'plate_number': truck.plate_number,
                    'truck_type': truck.truck_type.name if truck.truck_type else None,
                    'truck': truck
                }
                if truck.truck_type:
                    truck_type_names.add(truck.truck_type.name)
        
        if 'plate_number' in df.columns or 'truck_type' in df.columns:
            def validate_truck_data(row):
                parsed_plate = row.get('plate_number') if 'plate_number' in df.columns else None
                plate_num_normalized = standardize_plate(parsed_plate)
                truck_type_str = str(row.get('truck_type')).strip() if 'truck_type' in df.columns and not pd.isna(row.get('truck_type')) and str(row.get('truck_type')).strip() != '' else None
                
                if plate_num_normalized:
                    truck_data = truck_plate_map.get(plate_num_normalized)
                    if truck_data:
                        original_plate = truck_data['plate_number']
                        db_truck_type = truck_data['truck_type']
                        if truck_type_str:
                            if db_truck_type and db_truck_type.lower() == truck_type_str.lower():
                                return db_truck_type, original_plate
                            return db_truck_type, original_plate
                        return db_truck_type, original_plate
                    return None, None
                elif truck_type_str:
                    if truck_type_str.lower() in [t.lower() for t in truck_type_names]:
                        for valid_type in truck_type_names:
                            if valid_type.lower() == truck_type_str.lower():
                                return valid_type, None
                    return None, None
                return row.get('truck_type') if 'truck_type' in df.columns else None, row.get('plate_number') if 'plate_number' in df.columns else None
            
            validated_data = df.apply(validate_truck_data, axis=1)
            df['truck_type'] = validated_data.apply(lambda x: x[0] if x and x[0] is not None else None)
            df['plate_number'] = validated_data.apply(lambda x: x[1] if x and x[1] is not None else None)
        
        # Map Excel columns to model fields
        columns_to_drop_list = []
        for col in df.columns:
            col_lower = col.lower().strip()
            if any(keyword in col_lower for keyword in [
                'applied to invoice', 'item code', 'item type', 'cost', 
                'payment type', 'customer', 'supplier', 'employee', 
                'cash account', 'check no', 'check date', 'location', 
                'project', 'balance'
            ]):
                if 'reference no' not in col_lower:
                    columns_to_drop_list.append(col)
        
        for col in df.columns:
            col_lower = col.lower().strip()
            if col_lower == 'qty' or col_lower == 'item':
                columns_to_drop_list.append(col)
            if col_lower == 'description' and any('type' in c.lower() and 'account' not in c.lower() and 'item' not in c.lower() for c in df.columns):
                columns_to_drop_list.append(col)
        
        column_mapping = {}
        for col in df.columns:
            if col in columns_to_drop_list:
                continue
            col_lower = col.lower().strip()
            if 'account' in col_lower and 'number' not in col_lower and 'type' not in col_lower:
                continue
            elif 'account' in col_lower and 'number' in col_lower:
                column_mapping[col] = 'account_number'
            elif 'account' in col_lower and 'type' in col_lower and 'account_number' not in df.columns:
                column_mapping[col] = 'account_type'
            elif 'truck' in col_lower and 'type' in col_lower and 'truck_type' not in df.columns:
                column_mapping[col] = 'truck_type'
            elif ('plate' in col_lower or 'truck plate' in col_lower) and 'plate_number' not in df.columns:
                column_mapping[col] = 'plate_number'
            elif col_lower == 'type' or (col_lower == 'type' and 'item' not in col_lower):
                column_mapping[col] = 'description'
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
            elif 'rr no' in col_lower or col_lower == 'rr no.':
                column_mapping[col] = 'reference_number'
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
        
        if 'description' not in column_mapping.values():
            for col in df.columns:
                if col in columns_to_drop_list:
                    continue
                if 'unnamed' in col.lower():
                    sample_values = df[col].dropna().astype(str).head(10).tolist()
                    description_keywords = ['beginning balance', 'receive inventory', 'inventory withdrawal', 'funds', 'transfer']
                    if any(any(keyword in str(val).lower() for keyword in description_keywords) for val in sample_values):
                        column_mapping[col] = 'description'
                        break
        
        df = df.drop(columns=columns_to_drop_list, errors='ignore')
        df = df.rename(columns=column_mapping)
        
        # Handle "Beginning Balance"
        beginning_balance_mask = df.astype(str).apply(lambda x: x.str.contains('Beginning Balance', case=False, na=False)).any(axis=1)
        numeric_field_names = ['debit', 'credit', 'final_total', 'Debit', 'Credit', 'Final Total', 'QTY (Fuel)', 'Unit Cost']
        for field in numeric_field_names:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')
                df.loc[beginning_balance_mask, field] = 0
        
        columns_to_drop = [col for col in df.columns if col.lower().startswith('account') 
                          and col.lower() not in ['account_number', 'account_type'] 
                          and col not in column_mapping]
        df = df.drop(columns=columns_to_drop, errors='ignore')
        
        columns_to_drop = [col for col in df.columns if 'unnamed' in col.lower() and col not in column_mapping]
        df = df.drop(columns=columns_to_drop, errors='ignore')
        
        if 'reference_number' in column_mapping.values():
            mapped_ref_col = [col for col, mapped in column_mapping.items() if mapped == 'reference_number']
            if mapped_ref_col:
                ref_cols_to_drop = [col for col in df.columns 
                                   if ('reference' in col.lower() or 'rr no' in col.lower()) 
                                   and col not in mapped_ref_col 
                                   and col not in column_mapping]
                df = df.drop(columns=ref_cols_to_drop, errors='ignore')
        
        beginning_balance_mask = df.astype(str).apply(lambda x: x.str.contains('Beginning Balance', case=False, na=False)).any(axis=1)
        numeric_fields = ['debit', 'credit', 'final_total', 'quantity', 'price']
        for field in numeric_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')
                df.loc[beginning_balance_mask, field] = 0
        
        # Get valid routes from database
        valid_routes_upload = set(Route.objects.values_list('name', flat=True))
        
        # Enhanced parsing functions
        def extract_driver_from_remarks(remarks):
            if pd.isna(remarks) or remarks is None:
                return None
            remarks_str = str(remarks)
            
            drivers = [
                'Edgardo Agapay', 'Romel Bantilan', 'Reynaldo Rizalda', 'Francis Ariglado',
                'Roque Oling', 'Pablo Hamo', 'Albert Saavedra', 'Jimmy Oclarit', 'Nicanor',
                'Arnel Duhilag', 'Benjamin Aloso', 'Roger', 'Joseph Bahan', 'Doming',
                'Jun2x Campaña', 'Jun2x Toledo', 'Ronie Babanto'
            ]
            
            for driver in drivers:
                if driver in remarks_str:
                    return driver
            
            multi_driver_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*):'
            multi_match = re.search(multi_driver_pattern, remarks_str)
            if multi_match:
                driver1 = multi_match.group(1).strip()
                driver2 = multi_match.group(2).strip()
                for driver in drivers:
                    if driver in driver1 or driver in driver2:
                        return f"{driver1}/{driver2}"
            
            lro_pattern = r'LRO:\s*\d+Liters\s+Fuel\s+and\s+Oil\s+(?:[A-Z]+-\d+\s+)?([A-Za-z\s]+?)(?::|;)'
            lro_match = re.search(lro_pattern, remarks_str)
            if lro_match:
                potential_driver = lro_match.group(1).strip()
                if len(potential_driver) > 2 and not any(word in potential_driver.lower() for word in ['lro', 'liters', 'fuel', 'oil']):
                    for driver in drivers:
                        if driver.lower() in potential_driver.lower():
                            return driver
                    if len(potential_driver.split()) >= 2:
                        return potential_driver
            
            name_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+):'
            matches = re.finditer(name_pattern, remarks_str)
            for match in matches:
                potential_driver = match.group(1).strip()
                if any(route_word in potential_driver.upper() for route_word in ['PAG-', 'CDO', 'ILIGAN', 'STRIKE']):
                    continue
                if any(word in potential_driver.lower() for word in ['lro', 'liters', 'fuel', 'oil', 'deliver', 'transfer']):
                    continue
                for driver in drivers:
                    if driver.lower() == potential_driver.lower():
                        return driver
                if len(potential_driver.split()) >= 2:
                    return potential_driver
            
            return None
        
        def extract_route_from_remarks(remarks):
            if pd.isna(remarks) or remarks is None:
                return None
            remarks_str = str(remarks)
            
            def is_valid_route(route_name):
                if not route_name:
                    return None
                route_clean = str(route_name).strip()
                for valid_route in valid_routes_upload:
                    if route_clean.upper() == valid_route.upper():
                        return valid_route
                return None
            
            for route in valid_routes_upload:
                route_escaped = re.escape(route)
                pattern = rf'{route_escaped}\s*:'
                match = re.search(pattern, remarks_str, re.IGNORECASE)
                if match:
                    validated = is_valid_route(route)
                    if validated:
                        return validated
            
            context_pattern = r':\s*([A-Z0-9]+(?:-[A-Z0-9]+)+|[A-Z\s]+?)\s*:'
            matches = re.finditer(context_pattern, remarks_str, re.IGNORECASE)
            for match in matches:
                potential_route = match.group(1).strip()
                if re.search(r'[a-z]', potential_route) and len(potential_route.split()) > 1:
                    continue
                validated = is_valid_route(potential_route)
                if validated:
                    return validated
            
            for route in valid_routes_upload:
                route_escaped = re.escape(route)
                pattern = rf'\b{route_escaped}\b'
                if re.search(pattern, remarks_str, re.IGNORECASE):
                    validated = is_valid_route(route)
                    if validated:
                        return validated
            
            return None
        
        def extract_loads_from_remarks(remarks):
            if pd.isna(remarks) or remarks is None:
                return None, None
            remarks_str = str(remarks)
            
            front_load = None
            back_load = None
            
            valid_load_types = [lt.name for lt in LoadType.objects.all()]
            
            def clean_load_extracted(load_str):
                if not load_str:
                    return None
                cleaned = str(load_str).strip()
                route_patterns = [
                    r'\bPAG-[A-Z]+\b', r'\bDUMINGAG\b', r'\bDIMATALING\b',
                    r'\bCDO\b', r'\bILIGAN\b', r'\bOPEX\b', r'\bPAGADIAN\b'
                ]
                for pattern in route_patterns:
                    cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
                delivery_words = [
                    r'\bdeliver\b', r'\bDeliver\b', r'\bDELIVER\b', r'\bpara\b',
                    r'\bPara\b', r'\bsa\b', r'\bto\b', r'\bug\b', r'\bni\b', r'\bmao\b'
                ]
                for word in delivery_words:
                    cleaned = re.sub(word, '', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'[:\.,;]+$', '', cleaned)
                cleaned = re.sub(r'\s+\+\d+.*$', '', cleaned)
                cleaned = re.sub(r'\s+\d+.*$', '', cleaned)
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                return cleaned if cleaned else None
            
            def get_strike_load():
                strike_load = next((lt for lt in valid_load_types if lt.lower() == 'strike'), None)
                return strike_load if strike_load else 'Strike'
            
            def handle_single_load(front, back):
                front_valid = front and is_valid_load(front, valid_load_types)
                back_valid = back and is_valid_load(back, valid_load_types)
                
                if front_valid and back_valid:
                    return clean_load_value(front, valid_load_types), clean_load_value(back, valid_load_types)
                elif front_valid and not back_valid:
                    strike_load = get_strike_load()
                    return clean_load_value(front, valid_load_types), strike_load
                elif back_valid and not front_valid:
                    strike_load = get_strike_load()
                    return strike_load, clean_load_value(back, valid_load_types)
                return None, None
            
            load_pattern_with_colon = r':\s*([A-Za-z\s]+)/([A-Za-z\s]+):'
            match = re.search(load_pattern_with_colon, remarks_str)
            if match:
                potential_front = clean_load_extracted(match.group(1))
                potential_back = clean_load_extracted(match.group(2))
                result = handle_single_load(potential_front, potential_back)
                if result[0] and result[1]:
                    return result
            
            load_pattern_end = r':\s*([A-Za-z\s]+)/([A-Za-z\s]+)\s*$'
            match = re.search(load_pattern_end, remarks_str)
            if match:
                potential_front = clean_load_extracted(match.group(1))
                potential_back = clean_load_extracted(match.group(2))
                result = handle_single_load(potential_front, potential_back)
                if result[0] and result[1]:
                    return result
            
            load_pattern_with_text = r':\s*([A-Za-z\s]+)/([A-Za-z\s]+?)(?:\s+(?:deliver|Deliver|DELIVER|para|Para|sa|to|ug|\+|:|\d|DUMINGAG|DIMATALING|PAG-|$))'
            match = re.search(load_pattern_with_text, remarks_str, re.IGNORECASE)
            if match:
                potential_front = clean_load_extracted(match.group(1))
                potential_back = clean_load_extracted(match.group(2))
                result = handle_single_load(potential_front, potential_back)
                if result[0] and result[1]:
                    return result
            
            load_pattern_general = r'\b([A-Za-z\s]{3,})/([A-Za-z\s]{3,})\b'
            match = re.search(load_pattern_general, remarks_str)
            if match:
                potential_front = clean_load_extracted(match.group(1))
                potential_back = clean_load_extracted(match.group(2))
                route_indicators = ['PAG-', 'CDO', 'ILIGAN', 'OPEX', 'PAGADIAN', 'DUMINGAG', 'DIMATALING']
                is_route = any(indicator in (potential_front or '').upper() or indicator in (potential_back or '').upper()
                            for indicator in route_indicators)
                if not is_route:
                    result = handle_single_load(potential_front, potential_back)
                    if result[0] and result[1]:
                        return result
            
            return None, None
        
        # Validate drivers against database
        if 'driver' in df.columns:
            valid_drivers_db_upload = set(Driver.objects.values_list('name', flat=True))
            
            def validate_driver(driver_value):
                if pd.isna(driver_value) or driver_value == '' or driver_value is None:
                    return None
                driver_str = str(driver_value).strip()
                for valid_driver in valid_drivers_db_upload:
                    if driver_str.lower() == valid_driver.lower():
                        return valid_driver
                return None
            
            df['driver'] = df['driver'].apply(validate_driver)
        
        # Validate load types against database
        if 'front_load' in df.columns or 'back_load' in df.columns:
            valid_load_types_db_upload = set(LoadType.objects.values_list('name', flat=True))
            
            def validate_load_type(load_value):
                if pd.isna(load_value) or load_value == '' or load_value is None:
                    return None
                load_str = str(load_value).strip()
                load_cleaned = clean_load_value(load_str, valid_load_types_db_upload)
                if load_cleaned:
                    for valid_load in valid_load_types_db_upload:
                        if load_cleaned.lower() == valid_load.lower():
                            return valid_load
                return None
            
            if 'front_load' in df.columns:
                df['front_load'] = df['front_load'].apply(validate_load_type)
            if 'back_load' in df.columns:
                df['back_load'] = df['back_load'].apply(validate_load_type)
        
        # Apply parsing to extract driver, route, front_load, back_load from remarks
        if 'remarks' in df.columns:
            valid_load_types_db_after_extraction = set(LoadType.objects.values_list('name', flat=True))
            
            for index, row in df.iterrows():
                extracted_driver = extract_driver_from_remarks(row.get('remarks'))
                if extracted_driver:
                    df.at[index, 'driver'] = extracted_driver
                
                extracted_route = extract_route_from_remarks(row.get('remarks'))
                if extracted_route:
                    df.at[index, 'route'] = extracted_route
                
                if extracted_driver and extracted_route:
                    extracted_front, extracted_back = extract_loads_from_remarks(row.get('remarks'))
                    if extracted_front:
                        cleaned_front = clean_load_value(extracted_front, valid_load_types_db_after_extraction)
                        if cleaned_front:
                            for valid_load in valid_load_types_db_after_extraction:
                                if cleaned_front.lower() == valid_load.lower():
                                    df.at[index, 'front_load'] = valid_load
                                    break
                    if extracted_back:
                        cleaned_back = clean_load_value(extracted_back, valid_load_types_db_after_extraction)
                        if cleaned_back:
                            for valid_load in valid_load_types_db_after_extraction:
                                if cleaned_back.lower() == valid_load.lower():
                                    df.at[index, 'back_load'] = valid_load
                                    break
        
        # Clean and convert data
        def clean_decimal(value):
            if pd.isna(value) or value == '' or value == 'nan':
                return 0
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0
        
        numeric_fields = ['debit', 'credit', 'final_total', 'quantity', 'price']
        for field in numeric_fields:
            if field in df.columns:
                df[field] = df[field].apply(clean_decimal)
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        string_fields = ['account_number', 'account_type', 'truck_type', 'plate_number', 
                       'description', 'remarks', 'reference_number', 'driver', 'route', 
                       'front_load', 'back_load']
        for field in string_fields:
            if field in df.columns:
                df[field] = df[field].astype(str).replace('nan', '').replace('None', '')
        
        # Calculate final_total from Debit and Credit if final_total column doesn't exist
        if 'debit' in df.columns and 'credit' in df.columns:
            df['debit'] = pd.to_numeric(df['debit'], errors='coerce').fillna(0)
            df['credit'] = pd.to_numeric(df['credit'], errors='coerce').fillna(0)
            
            if 'final_total' not in df.columns:
                df['final_total'] = df['debit'] - df['credit']
            else:
                df['final_total'] = pd.to_numeric(df['final_total'], errors='coerce')
                df['final_total'] = df['final_total'].fillna(df['debit'] - df['credit'])
        
        # For Hauling Income accounts, ensure final_total is positive
        if 'account_type' in df.columns and 'final_total' in df.columns:
            hauling_income_mask = df['account_type'].astype(str).str.contains('Hauling Income', case=False, na=False)
            df.loc[hauling_income_mask, 'final_total'] = df.loc[hauling_income_mask, 'final_total'].apply(lambda x: abs(x) if x < 0 else x)
        
        # Helper functions to normalize data for duplicate checking
        def normalize_account_number_for_dedup(account_num):
            if not account_num:
                return ''
            normalized = str(account_num).strip().replace('.0', '').replace('.00', '')
            return normalized
        
        def normalize_date_for_dedup(date_value):
            if date_value is None:
                return None
            if isinstance(date_value, date):
                return date_value
            if isinstance(date_value, datetime):
                return date_value.date()
            try:
                return pd.to_datetime(date_value).date()
            except:
                return None
        
        # Filter out rows where account_number is missing (after all parsing)
        if 'account_number' not in df.columns:
            df['account_number'] = None
        df = df[df['account_number'].notna() & (df['account_number'] != '')]
        df = df.reset_index(drop=True)
        total_rows = len(df)
        
        # Get existing accounts for duplicate checking
        existing_accounts = TruckingAccount.objects.all().values(
            'account_number', 'account_type_id', 'date', 'created_at'
        )
        existing_account_map = {}
        for record in existing_accounts:
            normalized_account = normalize_account_number_for_dedup(record['account_number'])
            normalized_date = normalize_date_for_dedup(record['date'])
            key = (normalized_account, record['account_type_id'], normalized_date)
            if key not in existing_account_map:
                existing_account_map[key] = []
            existing_account_map[key].append(record['created_at'])
        
        batch_created_at = timezone.now()
        BATCH_SIZE = 100
        accounts_to_create = []
        created_count = 0
        duplicate_count = 0
        errors = []
        parsing_stats = {
            'drivers_extracted': 0,
            'routes_extracted': 0,
            'loads_extracted': 0
        }
        
        # Process rows in batches
        for index, row in df.iterrows():
            try:
                # Update progress every 10 rows
                if index % 10 == 0:
                    progress = int((index / total_rows) * 90) + 5
                    cache.set(progress_key, {
                        'status': 'processing',
                        'progress': progress,
                        'total_rows': total_rows,
                        'processed_rows': index + 1,
                        'created_count': created_count,
                        'duplicate_count': duplicate_count,
                        'error_count': len(errors),
                        'errors': errors[-10:],
                        'message': f'Processing row {index + 1} of {total_rows}...'
                    }, timeout=3600)
                
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
                
                # Resolve Driver by name (only use existing drivers from database)
                driver_instance = None
                route_instance = None
                if row.get('driver') and str(row.get('driver')).strip() != '':
                    driver_name_raw = str(row.get('driver')).strip()
                    driver_instance = Driver.objects.filter(name__iexact=driver_name_raw).first()
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
                    account_number_value = normalize_account_number_for_dedup(raw_account_number)
                
                # Normalize date value
                account_date_value = None
                raw_date_value = row.get('date')
                if pd.notna(raw_date_value) and raw_date_value != '':
                    account_date_value = normalize_date_for_dedup(raw_date_value)
                
                # Skip if date is required but missing
                if account_date_value is None:
                    continue
                
                # Check for duplicates
                dedup_key = (
                    account_number_value,
                    account_type_instance.id if account_type_instance else None,
                    account_date_value,
                )
                
                if dedup_key in existing_account_map:
                    duplicate_count += 1
                    continue
                
                # Resolve Truck
                truck_instance = None
                plate_number_raw = row.get('plate_number', '')
                if plate_number_raw and str(plate_number_raw).strip() != '':
                    plate_number_standardized = standardize_plate_number(plate_number_raw)
                    if plate_number_standardized:
                        truck_type_str = str(row.get('truck_type', '')).strip() if pd.notna(row.get('truck_type')) and str(row.get('truck_type')).strip() != '' else None
                        company_str = str(row.get('company', '')).strip() if pd.notna(row.get('company')) and str(row.get('company')).strip() != '' else None
                        
                        truck_type_instance = None
                        if truck_type_str:
                            truck_type_instance, _ = TruckType.objects.get_or_create(name=truck_type_str)
                        
                        existing_truck = Truck.objects.filter(plate_number=plate_number_standardized).first()
                        if existing_truck:
                            truck_instance = existing_truck
                        else:
                            truck_instance = Truck.objects.create(
                                plate_number=plate_number_standardized,
                                truck_type=truck_type_instance,
                                company=company_str if company_str else None
                            )
                
                # Resolve LoadTypes
                front_load_instance = None
                if row.get('front_load') and str(row.get('front_load')).strip() != '':
                    front_load_cleaned = clean_load_value(row.get('front_load'))
                    if front_load_cleaned:
                        front_load_instance = LoadType.objects.filter(name__iexact=front_load_cleaned).first()
                
                back_load_instance = None
                if row.get('back_load') and str(row.get('back_load')).strip() != '':
                    back_load_cleaned = clean_load_value(row.get('back_load'))
                    if back_load_cleaned:
                        back_load_instance = LoadType.objects.filter(name__iexact=back_load_cleaned).first()
                
                # Create TruckingAccount instance
                account = TruckingAccount(
                    account_number=account_number_value,
                    account_type=account_type_instance,
                    truck=truck_instance,
                    description=str(row.get('description', '')) if pd.notna(row.get('description')) else '',
                    debit=float(row.get('debit', 0)) if pd.notna(row.get('debit')) else 0,
                    credit=float(row.get('credit', 0)) if pd.notna(row.get('credit')) else 0,
                    final_total=float(row.get('final_total', 0)) if pd.notna(row.get('final_total')) else 0,
                    remarks=str(row.get('remarks', '')) if pd.notna(row.get('remarks')) else '',
                    reference_number=str(row.get('reference_number', '')) if pd.notna(row.get('reference_number')) and row.get('reference_number') != '' and str(row.get('reference_number')).strip() != '' else None,
                    date=account_date_value,
                    quantity=float(row.get('quantity')) if pd.notna(row.get('quantity')) and row.get('quantity') != 0 else None,
                    price=float(row.get('price')) if pd.notna(row.get('price')) and row.get('price') != 0 else None,
                    driver=driver_instance,
                    route=route_instance,
                    front_load=front_load_instance,
                    back_load=back_load_instance,
                )
                account.created_at = batch_created_at
                accounts_to_create.append(account)
                
                # Bulk create when batch is full
                if len(accounts_to_create) >= BATCH_SIZE:
                    try:
                        with transaction.atomic():
                            TruckingAccount.objects.bulk_create(accounts_to_create, ignore_conflicts=False)
                        created_count += len(accounts_to_create)
                        accounts_to_create = []
                    except Exception as e:
                        # Fallback to individual saves
                        for acc in accounts_to_create:
                            try:
                                acc.save()
                                created_count += 1
                            except Exception as save_error:
                                errors.append(f"Row {index + 1}: {str(save_error)}")
                        accounts_to_create = []
                
            except Exception as e:
                errors.append(f"Row {index + 1}: {str(e)}")
                continue
        
        # Create remaining accounts
        if accounts_to_create:
            try:
                with transaction.atomic():
                    TruckingAccount.objects.bulk_create(accounts_to_create, ignore_conflicts=False)
                created_count += len(accounts_to_create)
            except Exception as e:
                for acc in accounts_to_create:
                    try:
                        acc.save()
                        created_count += 1
                    except Exception as save_error:
                        errors.append(f"Final batch: {str(save_error)}")
        
        # Update final progress
        cache.set(progress_key, {
            'status': 'completed',
            'progress': 100,
            'total_rows': total_rows,
            'processed_rows': total_rows,
            'created_count': created_count,
            'duplicate_count': duplicate_count,
            'error_count': len(errors),
            'errors': errors[:50],
            'message': f'Upload completed! Created {created_count} accounts.',
            'parsing_stats': parsing_stats
        }, timeout=3600)
        
        # Clean up file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return {
            'status': 'completed',
            'created_count': created_count,
            'duplicate_count': duplicate_count,
            'error_count': len(errors),
            'errors': errors[:50],
            'parsing_stats': parsing_stats
        }
        
    except Exception as e:
        import traceback
        error_msg = f'{str(e)}\n{traceback.format_exc()}'
        # Update error status
        progress_key = f'upload_progress_{task_id}'
        cache.set(progress_key, {
            'status': 'error',
            'progress': 0,
            'total_rows': 0,
            'processed_rows': 0,
            'created_count': 0,
            'duplicate_count': 0,
            'error_count': 1,
            'errors': [error_msg],
            'message': f'Upload failed: {str(e)}'
        }, timeout=3600)
        
        # Clean up file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        raise
