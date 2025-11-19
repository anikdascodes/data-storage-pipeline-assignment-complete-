#!/usr/bin/env python3
"""
Data Validation Script
Validates input CSV files before running ETL pipelines
Checks:
- File existence
- CSV headers match expected schema
- Basic row count checks
- File readability
"""

import os
import sys
import csv
from pathlib import Path

# Expected schemas
EXPECTED_SCHEMAS = {
    "seller_catalog": ["seller_id", "item_id", "item_name", "category", "marketplace_price", "stock_qty"],
    "company_sales": ["item_id", "units_sold", "revenue", "sale_date"],
    "competitor_sales": ["seller_id", "item_id", "units_sold", "revenue", "marketplace_price", "sale_date"]
}

# Minimum row counts (excluding header)
MIN_ROW_COUNTS = {
    "seller_catalog": 10,
    "company_sales": 10,
    "competitor_sales": 10
}

def validate_file_exists(file_path: str) -> bool:
    """Check if file exists and is readable"""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    if not os.path.isfile(file_path):
        print(f"❌ Not a file: {file_path}")
        return False
    if not os.access(file_path, os.R_OK):
        print(f"❌ File not readable: {file_path}")
        return False
    print(f"✅ File exists and readable: {file_path}")
    return True

def validate_csv_header(file_path: str, expected_columns: list) -> bool:
    """Validate CSV header matches expected schema"""
    try:
        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            
            if header == expected_columns:
                print(f"✅ Header matches expected schema: {', '.join(header)}")
                return True
            else:
                print(f"❌ Header mismatch!")
                print(f"   Expected: {', '.join(expected_columns)}")
                print(f"   Found:    {', '.join(header)}")
                return False
    except Exception as e:
        print(f"❌ Error reading CSV header: {e}")
        return False

def validate_row_count(file_path: str, min_rows: int) -> bool:
    """Validate CSV has minimum number of rows"""
    try:
        with open(file_path, 'r') as f:
            row_count = sum(1 for _ in f) - 1  # Exclude header
            
            if row_count >= min_rows:
                print(f"✅ Row count: {row_count:,} (minimum: {min_rows})")
                return True
            else:
                print(f"❌ Insufficient rows: {row_count} (minimum: {min_rows})")
                return False
    except Exception as e:
        print(f"❌ Error counting rows: {e}")
        return False

def validate_dataset(dataset_name: str, base_path: str) -> bool:
    """Validate a complete dataset (clean + dirty files)"""
    print(f"\n{'='*60}")
    print(f"Validating {dataset_name.upper()}")
    print(f"{'='*60}")
    
    dataset_path = os.path.join(base_path, dataset_name)
    expected_schema = EXPECTED_SCHEMAS[dataset_name]
    min_rows = MIN_ROW_COUNTS[dataset_name]
    
    all_valid = True
    
    # Check for CSV files in the directory
    csv_files = list(Path(dataset_path).glob("*.csv"))
    
    if not csv_files:
        print(f"❌ No CSV files found in {dataset_path}")
        return False
    
    print(f"Found {len(csv_files)} CSV file(s)")
    
    for csv_file in csv_files:
        print(f"\n--- Validating: {csv_file.name} ---")
        
        # Validate file exists
        if not validate_file_exists(str(csv_file)):
            all_valid = False
            continue
        
        # Validate header
        if not validate_csv_header(str(csv_file), expected_schema):
            all_valid = False
            continue
        
        # Validate row count
        if not validate_row_count(str(csv_file), min_rows):
            all_valid = False
            continue
    
    return all_valid

def main():
    """Main validation function"""
    print("="*60)
    print("DATA VALIDATION SCRIPT")
    print("="*60)
    
    # Base path for raw data (support both Docker and local paths)
    if os.path.exists("/workspace/data/raw"):
        base_path = "/workspace/data/raw"
    else:
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw")
    
    # Check if base path exists
    if not os.path.exists(base_path):
        print(f"\n❌ Base data path not found: {base_path}")
        print("Please ensure data files are in the correct location.")
        sys.exit(1)
    
    # Validate each dataset
    results = {}
    for dataset_name in EXPECTED_SCHEMAS.keys():
        results[dataset_name] = validate_dataset(dataset_name, base_path)
    
    # Summary
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    
    all_passed = True
    for dataset_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{dataset_name:20s}: {status}")
        if not passed:
            all_passed = False
    
    print(f"{'='*60}")
    
    if all_passed:
        print("\n✅ All validations passed! Ready to run ETL pipelines.")
        sys.exit(0)
    else:
        print("\n❌ Some validations failed. Please fix the issues before running pipelines.")
        sys.exit(1)

if __name__ == "__main__":
    main()
