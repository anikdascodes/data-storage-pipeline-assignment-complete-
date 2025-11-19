#!/bin/bash

##############################################
# Clean Previous Pipeline Run
# Removes all processed data to allow fresh runs
##############################################

echo "=========================================="
echo "Cleaning Previous Pipeline Run"
echo "=========================================="
echo ""

# Remove processed Hudi tables
echo "Step 1/4: Removing Hudi tables..."
rm -rf /workspace/data/processed/seller_catalog_hudi
rm -rf /workspace/data/processed/company_sales_hudi
rm -rf /workspace/data/processed/competitor_sales_hudi
echo "✅ Hudi tables cleaned"

# Remove recommendations
echo ""
echo "Step 2/4: Removing recommendations..."
rm -rf /workspace/data/processed/recommendations_csv
echo "✅ Recommendations cleaned"

# Remove quarantine data
echo ""
echo "Step 3/4: Removing quarantine data..."
rm -rf /workspace/data/quarantine/*
echo "✅ Quarantine data cleaned"

# Remove metrics
echo ""
echo "Step 4/4: Removing metrics..."
rm -rf /workspace/data/metrics/*
echo "✅ Metrics cleaned"

echo ""
echo "=========================================="
echo "✅ Cleanup Complete! Ready for fresh run."
echo "=========================================="
