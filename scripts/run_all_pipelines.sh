#!/bin/bash

echo "=========================================="
echo "E-commerce Recommendation System Pipeline"
echo "=========================================="
echo ""

# Run ETL pipelines
echo "Step 1/4: Running ETL for Seller Catalog..."
bash /workspace/scripts/etl_seller_catalog_spark_submit.sh
if [ $? -ne 0 ]; then
    echo "ERROR: Seller Catalog ETL failed"
    exit 1
fi
echo ""

echo "Step 2/4: Running ETL for Company Sales..."
bash /workspace/scripts/etl_company_sales_spark_submit.sh
if [ $? -ne 0 ]; then
    echo "ERROR: Company Sales ETL failed"
    exit 1
fi
echo ""

echo "Step 3/4: Running ETL for Competitor Sales..."
bash /workspace/scripts/etl_competitor_sales_spark_submit.sh
if [ $? -ne 0 ]; then
    echo "ERROR: Competitor Sales ETL failed"
    exit 1
fi
echo ""

echo "Step 4/4: Running Consumption Layer (Recommendations)..."
bash /workspace/scripts/consumption_recommendation_spark_submit.sh
if [ $? -ne 0 ]; then
    echo "ERROR: Consumption Layer failed"
    exit 1
fi
echo ""

echo "=========================================="
echo "All Pipelines Completed Successfully!"
echo "=========================================="
echo ""
echo "Output locations:"
echo "  - Seller Catalog Hudi: /workspace/data/processed/seller_catalog_hudi/"
echo "  - Company Sales Hudi: /workspace/data/processed/company_sales_hudi/"
echo "  - Competitor Sales Hudi: /workspace/data/processed/competitor_sales_hudi/"
echo "  - Recommendations CSV: /workspace/data/processed/recommendations_csv/"
echo "  - Quarantine Data: /workspace/data/quarantine/"
echo ""
