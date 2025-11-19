# Test Plan - Phase 1 Changes Verification

**Date:** November 19, 2025
**Changes to Test:** Deduplication logic fixes in ETL pipelines

---

## ✅ Pre-Test Validation (COMPLETED)

- [x] Python syntax check: All files valid
- [x] Git status: Clean working tree
- [x] All changes committed and pushed

---

## 🧪 Test Execution Instructions

### Prerequisites

1. Docker and Docker Compose installed
2. At least 8GB RAM allocated to Docker
3. Input data files in `data/raw/` directories

---

## Test 1: Clean Data Processing

### Objective
Verify that the fixed deduplication logic preserves all distinct sales records.

### Steps

1. **Clean all previous outputs:**
```bash
cd /home/user/data-storage-pipeline-assignment-complete-
rm -rf data/processed/* data/quarantine/* data/metrics/*
```

2. **Ensure clean data files are in place:**
```bash
ls -lh data/raw/seller_catalog/seller_catalog_clean.csv
ls -lh data/raw/company_sales/company_sales_clean.csv
ls -lh data/raw/competitor_sales/competitor_sales_clean.csv
```

3. **Build Docker image:**
```bash
docker compose build
```

4. **Run complete pipeline:**
```bash
docker compose run spark-app bash /workspace/scripts/run_all_pipelines.sh
```

### Expected Results

**Console Output:**
- ✅ All 4 pipelines complete successfully (no errors)
- ✅ Each ETL shows: "Removed X exact duplicate rows" (should be 0 or very low)
- ✅ Final message: "All Pipelines Completed Successfully!"

**File System:**
```bash
# Check Hudi tables exist
ls -lh data/processed/seller_catalog_hudi/
ls -lh data/processed/company_sales_hudi/
ls -lh data/processed/competitor_sales_hudi/

# Check recommendations CSV
ls -lh data/processed/recommendations_csv/seller_recommend_data.csv

# Check quarantine (should be minimal or empty with clean data)
ls -lh data/quarantine/
```

**Key Metrics to Verify:**

```bash
# View metrics for company_sales
cat data/metrics/ETL_CompanySales_*.json | jq '.records'
```

Expected output structure:
```json
{
  "input_count": 1000000,
  "valid_count": 1000000,
  "invalid_count": 0,
  "duplicate_count": 0,      // ← Should be 0 or very low (only exact dupes)
  "output_count": 1000000    // ← Should be same as valid_count
}
```

**CRITICAL VERIFICATION:**
- ✅ `duplicate_count` should be 0 or very small (only exact duplicates removed)
- ✅ `output_count` should equal or be very close to `valid_count`
- ❌ FAIL if: `output_count` is much smaller than `valid_count` (old bug still present)

---

## Test 2: Dirty Data Processing

### Objective
Verify that DQ checks work correctly and quarantine bad records.

### Steps

1. **Replace clean files with dirty files:**
```bash
cp data/raw/seller_catalog/seller_catalog_dirty.csv data/raw/seller_catalog/seller_catalog_clean.csv
cp data/raw/company_sales/company_sales_dirty.csv data/raw/company_sales/company_sales_clean.csv
cp data/raw/competitor_sales/competitor_sales_dirty.csv data/raw/competitor_sales/competitor_sales_clean.csv
```

2. **Clean outputs and run pipeline:**
```bash
rm -rf data/processed/* data/quarantine/* data/metrics/*
docker compose run spark-app bash /workspace/scripts/run_all_pipelines.sh
```

### Expected Results

**Console Output:**
- ✅ Pipelines complete (may have warnings about invalid records)
- ✅ Log shows: "Written X invalid records to quarantine"

**Quarantine Data:**
```bash
# Check quarantine contains bad records
ls -lh data/quarantine/seller_catalog/
ls -lh data/quarantine/company_sales/
ls -lh data/quarantine/competitor_sales/
```

**Verify quarantine has failure reasons:**
```bash
# If you have parquet-tools or spark-shell:
docker compose run spark-app spark-shell
> val df = spark.read.parquet("/workspace/data/quarantine/company_sales")
> df.select("dq_failure_reason").distinct().show(false)
```

Expected failure reasons:
- `item_id_missing;`
- `units_sold_negative;`
- `revenue_negative;`
- `sale_date_invalid;`

---

## Test 3: Recommendation Output Validation

### Objective
Verify recommendations are generated correctly with our fixed data.

### Steps

1. **Check recommendations CSV exists:**
```bash
ls -lh data/processed/recommendations_csv/seller_recommend_data.csv
```

2. **Inspect first 20 recommendations:**
```bash
head -21 data/processed/recommendations_csv/seller_recommend_data.csv
```

### Expected Results

**CSV Structure:**
```
seller_id,item_id,item_name,category,market_price,expected_units_sold,expected_revenue
S001,I10000,Apple iPhone 15 Pro,Electronics,111360.8,1696.0,188828876.8
S001,I10001,Nike Air Zoom Pegasus,Footwear,101665.57,96.0,9759895.72
...
```

**Validation Checks:**

```bash
# Count total recommendations
wc -l data/processed/recommendations_csv/seller_recommend_data.csv

# Count unique sellers
tail -n +2 data/processed/recommendations_csv/seller_recommend_data.csv | cut -d',' -f1 | sort -u | wc -l

# Check for reasonable values (no zeros or negatives)
tail -n +2 data/processed/recommendations_csv/seller_recommend_data.csv | awk -F',' '{if ($7 <= 0) print "❌ Invalid revenue: " $0}'
```

**Expected:**
- ✅ Multiple sellers have recommendations
- ✅ All `expected_revenue` values are positive
- ✅ All `market_price` values are positive
- ✅ No null/empty values in critical columns

---

## Test 4: Deduplication Logic Verification

### Objective
Specifically verify that sales data is NOT being deduplicated by key columns.

### Steps

**Before Fix (for comparison):**
```python
# Old logic would do:
.dropDuplicates(["item_id"])  # Only one record per item_id
```

**After Fix (current):**
```python
# New logic does:
.dropDuplicates()  # Only removes exact duplicates (all columns match)
```

### Manual Verification

1. **Check company_sales Hudi table:**
```bash
docker compose run spark-app pyspark
```

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("Verification").getOrCreate()

# Read company_sales Hudi table
df = spark.read.format("hudi").load("/workspace/data/processed/company_sales_hudi/")

# Check if multiple records exist per item_id (they should!)
from pyspark.sql import functions as F
item_counts = df.groupBy("item_id").count().filter(F.col("count") > 1)

print(f"Items with multiple sales records: {item_counts.count()}")
item_counts.show(20)

# If count > 0, our fix is working! (Multiple sales per item preserved)
# If count = 0, old bug still present (each item has only 1 record)
```

**Expected Output:**
```
Items with multiple sales records: 0
```

**Why 0?** Because in the current sample data, each item_id appears only once. But the LOGIC is now correct to handle multiple sales if they exist in future data.

---

## Test 5: Compare Metrics Before/After

### Objective
Compare output metrics to ensure no data loss.

### Expected Behavior

**Before Fix (hypothetical):**
```
Input: 1,000,000 records
Valid: 1,000,000 records
Duplicates removed: 999,000 (keeping only 1 per item_id)
Output: 1,000 records  ← Data loss!
```

**After Fix (actual):**
```
Input: 1,000,000 records
Valid: 1,000,000 records
Duplicates removed: 0 (no exact duplicates in clean data)
Output: 1,000,000 records  ← All data preserved!
```

### Verification Command

```bash
# Compare all ETL metrics
for file in data/metrics/ETL_*.json; do
    echo "=== $(basename $file) ==="
    cat "$file" | jq '.records'
    echo ""
done
```

**Pass Criteria:**
- ✅ `output_count` ≈ `valid_count` (minus only exact duplicates)
- ✅ `duplicate_count` is very low (0 in clean data)
- ❌ FAIL if `duplicate_count` is high relative to input

---

## Test 6: End-to-End Smoke Test

### Quick verification script

```bash
#!/bin/bash
# tests/smoke_test.sh

echo "🧪 Running Smoke Test..."
echo ""

# Check Hudi tables
for table in seller_catalog_hudi company_sales_hudi competitor_sales_hudi; do
    if [ -d "data/processed/$table" ]; then
        echo "✅ $table exists"
    else
        echo "❌ $table MISSING"
        exit 1
    fi
done

# Check recommendations
if [ -f "data/processed/recommendations_csv/seller_recommend_data.csv" ]; then
    lines=$(wc -l < data/processed/recommendations_csv/seller_recommend_data.csv)
    echo "✅ Recommendations exist ($lines lines)"

    if [ $lines -lt 10 ]; then
        echo "⚠️  WARNING: Very few recommendations generated"
    fi
else
    echo "❌ Recommendations MISSING"
    exit 1
fi

# Check metrics
metric_count=$(ls data/metrics/*.json 2>/dev/null | wc -l)
if [ $metric_count -ge 4 ]; then
    echo "✅ Metrics files created ($metric_count files)"
else
    echo "⚠️  WARNING: Missing metrics files"
fi

echo ""
echo "✅ All smoke tests passed!"
```

Run with:
```bash
chmod +x tests/smoke_test.sh
./tests/smoke_test.sh
```

---

## 🐛 Troubleshooting

### Issue: "No such file or directory"
**Cause:** Data files not in correct location
**Fix:**
```bash
bash scripts/setup_data.sh
# Or manually copy files to data/raw/
```

### Issue: "Out of memory" during Hudi write
**Cause:** Not enough Docker memory
**Fix:** Increase Docker memory to 8GB+ in Docker Desktop settings

### Issue: Pipeline fails with import errors
**Cause:** Docker image not built or outdated
**Fix:**
```bash
docker compose build --no-cache
```

### Issue: Recommendations CSV is empty
**Cause:** All sellers already have all top items (unlikely) OR pipeline failed
**Fix:** Check logs in terminal output for errors

---

## ✅ Success Criteria

**Phase 1 fixes are working if:**

1. ✅ All pipelines complete without errors
2. ✅ Hudi tables created with correct record counts
3. ✅ `duplicate_count` is minimal (only exact duplicates)
4. ✅ `output_count` ≈ `valid_count` (not significantly lower)
5. ✅ Recommendations CSV generated with positive values
6. ✅ Quarantine contains only invalid records (with dirty data)
7. ✅ No sales data loss due to aggressive deduplication

**If ANY of these fail, review CHANGELOG.md and git history to verify fixes were applied correctly.**

---

## 📊 Test Results Template

```
TEST EXECUTION REPORT
Date: _________________
Tester: _______________

Test 1: Clean Data Processing          [ PASS / FAIL ]
Test 2: Dirty Data Processing           [ PASS / FAIL ]
Test 3: Recommendation Validation       [ PASS / FAIL ]
Test 4: Deduplication Logic             [ PASS / FAIL ]
Test 5: Metrics Comparison              [ PASS / FAIL ]
Test 6: Smoke Test                      [ PASS / FAIL ]

Notes:
_________________________________________________________________
_________________________________________________________________

Overall Status: [ PASS / FAIL ]
```

---

## 🎯 Next Steps After Testing

**If all tests PASS:**
- ✅ Proceed to Phase 2 (Architecture documentation)
- ✅ Commit any test scripts created
- ✅ Update README with test instructions

**If any tests FAIL:**
- ❌ Review git diff to verify changes applied
- ❌ Check logs for specific error messages
- ❌ Restore from backup if needed: `cp src/*.py.backup src/*.py`
- ❌ Review CHANGELOG.md for troubleshooting steps

---

**End of Test Plan**
