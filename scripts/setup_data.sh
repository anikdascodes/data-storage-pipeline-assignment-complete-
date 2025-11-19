#!/bin/bash

# Data Setup Script
# Automates the process of setting up input datasets

set -e  # Exit on error

echo "=========================================="
echo "E-commerce Pipeline - Data Setup"
echo "=========================================="
echo ""

# Check if input_data_sets.zip exists
if [ ! -f "input_data_sets.zip" ]; then
    echo "❌ Error: input_data_sets.zip not found in project root"
    echo ""
    echo "Please ensure you have the input_data_sets.zip file from your instructor"
    echo "and place it in the project root directory."
    echo ""
    exit 1
fi

echo "✅ Found input_data_sets.zip"
echo ""

# Unzip the datasets
echo "Step 1/5: Unzipping datasets..."
unzip -q input_data_sets.zip
echo "✅ Datasets unzipped"
echo ""

# Create data directories
echo "Step 2/5: Creating data directories..."
mkdir -p data/raw/seller_catalog
mkdir -p data/raw/company_sales
mkdir -p data/raw/competitor_sales
echo "✅ Directories created"
echo ""

# Copy files to proper locations
echo "Step 3/5: Organizing files..."
cp input_data_sets/clean/seller_catalog_clean.csv data/raw/seller_catalog/
cp input_data_sets/dirty/seller_catalog_dirty.csv data/raw/seller_catalog/
echo "  ✅ Seller catalog files copied"

cp input_data_sets/clean/company_sales_clean.csv data/raw/company_sales/
cp input_data_sets/dirty/company_sales_dirty.csv data/raw/company_sales/
echo "  ✅ Company sales files copied"

cp input_data_sets/clean/competitor_sales_clean.csv data/raw/competitor_sales/
cp input_data_sets/dirty/competitor_sales_dirty.csv data/raw/competitor_sales/
echo "  ✅ Competitor sales files copied"
echo ""

# Clean up
echo "Step 4/5: Cleaning up temporary files..."
rm -rf input_data_sets/
echo "✅ Cleanup complete"
echo ""

# Validate data
echo "Step 5/5: Validating data..."
python3 scripts/validate_data.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Data Setup Complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "  1. Build Docker image: docker compose build"
    echo "  2. Run pipelines: docker compose run spark-app bash /workspace/scripts/run_all_pipelines.sh"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "❌ Data Validation Failed"
    echo "=========================================="
    echo ""
    echo "Please check the error messages above and fix any issues."
    echo ""
    exit 1
fi
