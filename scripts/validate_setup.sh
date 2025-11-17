#!/bin/bash

echo "=========================================="
echo "Validating Project Setup"
echo "=========================================="
echo ""

# Check if config file exists
echo "1. Checking configuration file..."
if [ -f "/workspace/configs/ecomm_prod.yml" ]; then
    echo "   ✅ Config file exists"
else
    echo "   ❌ Config file missing"
    exit 1
fi

# Check if source files exist
echo ""
echo "2. Checking source files..."
for file in etl_seller_catalog.py etl_company_sales.py etl_competitor_sales.py consumption_recommendation.py; do
    if [ -f "/workspace/src/$file" ]; then
        echo "   ✅ $file exists"
    else
        echo "   ❌ $file missing"
        exit 1
    fi
done

# Check if scripts exist
echo ""
echo "3. Checking spark-submit scripts..."
for script in etl_seller_catalog_spark_submit.sh etl_company_sales_spark_submit.sh etl_competitor_sales_spark_submit.sh consumption_recommendation_spark_submit.sh; do
    if [ -f "/workspace/scripts/$script" ]; then
        echo "   ✅ $script exists"
    else
        echo "   ❌ $script missing"
        exit 1
    fi
done

# Check if input data exists
echo ""
echo "4. Checking input data files..."
for dir in seller_catalog company_sales competitor_sales; do
    if [ -d "/workspace/data/raw/$dir" ]; then
        file_count=$(ls -1 /workspace/data/raw/$dir/*.csv 2>/dev/null | wc -l)
        if [ $file_count -gt 0 ]; then
            echo "   ✅ $dir: $file_count CSV files found"
        else
            echo "   ❌ $dir: No CSV files found"
            exit 1
        fi
    else
        echo "   ❌ $dir directory missing"
        exit 1
    fi
done

# Check if output directories exist
echo ""
echo "5. Checking output directories..."
for dir in processed quarantine; do
    if [ -d "/workspace/data/$dir" ]; then
        echo "   ✅ $dir directory exists"
    else
        echo "   ❌ $dir directory missing"
        exit 1
    fi
done

# Check Python syntax
echo ""
echo "6. Validating Python syntax..."
for file in /workspace/src/*.py; do
    python3 -m py_compile "$file" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "   ✅ $(basename $file) syntax valid"
    else
        echo "   ❌ $(basename $file) syntax error"
        exit 1
    fi
done

# Check if Spark is available
echo ""
echo "7. Checking Spark installation..."
if command -v spark-submit &> /dev/null; then
    echo "   ✅ spark-submit found"
    spark-submit --version 2>&1 | grep "version" | head -1
else
    echo "   ❌ spark-submit not found"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ All validation checks passed!"
echo "=========================================="
echo ""
echo "You can now run the pipelines:"
echo "  bash /workspace/scripts/run_all_pipelines.sh"
echo ""
