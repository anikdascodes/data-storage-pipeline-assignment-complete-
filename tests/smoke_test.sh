#!/bin/bash
# Smoke Test - Quick validation of pipeline outputs
# Run after pipeline execution to verify all outputs exist

set -e  # Exit on first error

WORKSPACE="/workspace"
if [ ! -d "$WORKSPACE" ]; then
    # Running outside Docker, adjust paths
    WORKSPACE="."
fi

echo "🧪 E-commerce Pipeline Smoke Test"
echo "=================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# Test 1: Check Hudi tables exist
echo "📊 Test 1: Checking Hudi Tables..."
for table in seller_catalog_hudi company_sales_hudi competitor_sales_hudi; do
    path="$WORKSPACE/data/processed/$table"
    if [ -d "$path" ]; then
        # Check if directory has files
        file_count=$(find "$path" -type f | wc -l)
        if [ $file_count -gt 0 ]; then
            echo -e "${GREEN}✅${NC} $table exists ($file_count files)"
            ((PASS_COUNT++))
        else
            echo -e "${YELLOW}⚠️${NC}  $table exists but is empty"
            ((WARN_COUNT++))
        fi
    else
        echo -e "${RED}❌${NC} $table MISSING"
        ((FAIL_COUNT++))
    fi
done
echo ""

# Test 2: Check recommendations CSV
echo "📝 Test 2: Checking Recommendations..."
rec_csv="$WORKSPACE/data/processed/recommendations_csv"
if [ -d "$rec_csv" ]; then
    # Find the actual CSV file (Spark creates part-*.csv files)
    csv_file=$(find "$rec_csv" -name "*.csv" -type f | head -1)

    if [ -n "$csv_file" ]; then
        lines=$(cat "$csv_file" | wc -l)
        echo -e "${GREEN}✅${NC} Recommendations CSV exists ($lines lines)"

        if [ $lines -lt 10 ]; then
            echo -e "${YELLOW}⚠️${NC}  WARNING: Very few recommendations ($lines lines)"
            ((WARN_COUNT++))
        else
            ((PASS_COUNT++))
        fi

        # Check for data quality
        if head -5 "$csv_file" | grep -q "seller_id"; then
            echo -e "${GREEN}✅${NC} CSV has correct header"
            ((PASS_COUNT++))
        else
            echo -e "${RED}❌${NC} CSV missing header or malformed"
            ((FAIL_COUNT++))
        fi
    else
        echo -e "${RED}❌${NC} No CSV file found in recommendations directory"
        ((FAIL_COUNT++))
    fi
else
    echo -e "${RED}❌${NC} Recommendations directory MISSING"
    ((FAIL_COUNT++))
fi
echo ""

# Test 3: Check quarantine (optional - depends on dirty vs clean data)
echo "🚫 Test 3: Checking Quarantine Zone..."
quarantine_found=false
for dataset in seller_catalog company_sales competitor_sales; do
    qpath="$WORKSPACE/data/quarantine/$dataset"
    if [ -d "$qpath" ]; then
        file_count=$(find "$qpath" -type f | wc -l)
        if [ $file_count -gt 0 ]; then
            echo -e "${GREEN}✅${NC} $dataset quarantine has $file_count files (dirty data detected)"
            quarantine_found=true
        fi
    fi
done

if [ "$quarantine_found" = false ]; then
    echo -e "${GREEN}✅${NC} No quarantine data (all records valid)"
    ((PASS_COUNT++))
fi
echo ""

# Test 4: Check metrics files
echo "📈 Test 4: Checking Metrics..."
metrics_path="$WORKSPACE/data/metrics"
if [ -d "$metrics_path" ]; then
    metric_count=$(find "$metrics_path" -name "*.json" -type f | wc -l)

    if [ $metric_count -ge 4 ]; then
        echo -e "${GREEN}✅${NC} Metrics files created ($metric_count files)"
        ((PASS_COUNT++))

        # Check metrics content
        for metric_file in "$metrics_path"/*.json; do
            if [ -f "$metric_file" ]; then
                pipeline_name=$(basename "$metric_file" | cut -d'_' -f1-2)
                status=$(grep -o '"status":\s*"[^"]*"' "$metric_file" | cut -d'"' -f4)

                if [ "$status" = "SUCCESS" ]; then
                    echo -e "${GREEN}  ✓${NC} $pipeline_name: SUCCESS"
                else
                    echo -e "${RED}  ✗${NC} $pipeline_name: $status"
                    ((FAIL_COUNT++))
                fi
            fi
        done
    elif [ $metric_count -gt 0 ]; then
        echo -e "${YELLOW}⚠️${NC}  Some metrics missing ($metric_count/4 expected)"
        ((WARN_COUNT++))
    else
        echo -e "${YELLOW}⚠️${NC}  No metrics files found"
        ((WARN_COUNT++))
    fi
else
    echo -e "${YELLOW}⚠️${NC}  Metrics directory does not exist"
    ((WARN_COUNT++))
fi
echo ""

# Test 5: Check for common issues
echo "🔍 Test 5: Checking for Common Issues..."

# Check if recommendations have valid data
if [ -n "$csv_file" ]; then
    # Check for zero or negative expected_revenue (column 7)
    zero_revenue=$(tail -n +2 "$csv_file" | awk -F',' '$7 <= 0 {count++} END {print count+0}')

    if [ "$zero_revenue" -eq 0 ]; then
        echo -e "${GREEN}✅${NC} All recommendations have positive revenue"
        ((PASS_COUNT++))
    else
        echo -e "${YELLOW}⚠️${NC}  Found $zero_revenue recommendations with zero/negative revenue"
        ((WARN_COUNT++))
    fi

    # Check for unique sellers
    unique_sellers=$(tail -n +2 "$csv_file" | cut -d',' -f1 | sort -u | wc -l)
    echo -e "${GREEN}✅${NC} Recommendations for $unique_sellers unique sellers"
    ((PASS_COUNT++))
fi
echo ""

# Summary
echo "=================================="
echo "📊 TEST SUMMARY"
echo "=================================="
echo -e "${GREEN}✅ Passed:${NC} $PASS_COUNT"
echo -e "${YELLOW}⚠️  Warnings:${NC} $WARN_COUNT"
echo -e "${RED}❌ Failed:${NC} $FAIL_COUNT"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    if [ $WARN_COUNT -eq 0 ]; then
        echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
        echo "Pipeline executed successfully. Ready for Phase 2."
        exit 0
    else
        echo -e "${YELLOW}⚠️  TESTS PASSED WITH WARNINGS${NC}"
        echo "Pipeline completed but some issues detected. Review warnings above."
        exit 0
    fi
else
    echo -e "${RED}❌ TESTS FAILED${NC}"
    echo "Pipeline has issues. Review failed tests above."
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check pipeline logs for errors"
    echo "  2. Verify input data exists in data/raw/"
    echo "  3. Ensure Docker has enough memory (8GB+)"
    echo "  4. Run: docker compose build --no-cache"
    exit 1
fi
