# 🚀 RUN TESTS NOW - Quick Start Guide

**Status:** Ready to test Phase 1 fixes
**Time Required:** 20 minutes
**Prerequisites:** Docker and Docker Compose installed on your machine

---

## ⚠️ IMPORTANT NOTE

Docker is not available in the current development environment.

**You need to run these tests on your local machine where Docker is installed.**

---

## 🎯 Quick Test Execution

### Step 1: Navigate to Project Directory

```bash
cd /path/to/data-storage-pipeline-assignment-complete-
```

Or if you're already in the project:
```bash
cd ~/data-storage-pipeline-assignment-complete-
# Or wherever you cloned the repo
```

---

### Step 2: Pull Latest Changes

```bash
git checkout claude/setup-docker-ecommerce-0191ZE131YK9fdv9eFQJvzJy
git pull origin claude/setup-docker-ecommerce-0191ZE131YK9fdv9eFQJvzJy
```

**Expected output:**
```
Already up to date.
```

---

### Step 3: Clean Previous Outputs (Fresh Start)

```bash
rm -rf data/processed/* data/quarantine/* data/metrics/*
```

**Why?** Ensures we're testing with clean slate, no leftover data from previous runs.

---

### Step 4: Verify Input Data Exists

```bash
ls -lh data/raw/seller_catalog/
ls -lh data/raw/company_sales/
ls -lh data/raw/competitor_sales/
```

**Expected output:**
You should see `.csv` files in each directory (clean and/or dirty versions).

If files are missing:
```bash
bash scripts/setup_data.sh
```

---

### Step 5: Build Docker Image

```bash
docker compose build
```

**Time:** 5-10 minutes (first time only)
**Expected output:**
```
[+] Building ...
 => [internal] load build definition
 => => transferring dockerfile
 ...
 => exporting to image
Successfully built ...
```

**If you get errors:**
- Ensure Docker Desktop is running
- Check you have 8GB+ RAM allocated to Docker
- Try: `docker compose build --no-cache`

---

### Step 6: Run Complete Pipeline 🚀

```bash
docker compose run spark-app bash /workspace/scripts/run_all_pipelines.sh
```

**Time:** 10-15 minutes (depending on machine)

**What you'll see:**
```
==========================================
E-commerce Recommendation System Pipeline
==========================================

Step 1/4: Running ETL for Seller Catalog...
==========================================
Starting ETL Pipeline: Seller Catalog
==========================================
2025-11-19 - INFO - Loaded 1000000 records from /workspace/data/raw/seller_catalog/
2025-11-19 - INFO - Valid records: 1000000 | Invalid records: 0
2025-11-19 - INFO - Removed 0 exact duplicate rows  ← THIS IS KEY!
2025-11-19 - INFO - After deduplication: 1000000 records
...

Step 2/4: Running ETL for Company Sales...
...
2025-11-19 - INFO - Removed 0 exact duplicate rows  ← THIS IS KEY!
...

Step 3/4: Running ETL for Competitor Sales...
...
2025-11-19 - INFO - Removed 0 exact duplicate rows  ← THIS IS KEY!
...

Step 4/4: Running Consumption Layer (Recommendations)...
...
2025-11-19 - INFO - Generated XXXX recommendations

==========================================
All Pipelines Completed Successfully!
==========================================
```

**✅ GOOD SIGNS:**
- "Removed 0 exact duplicate rows" (or very small number)
- "All Pipelines Completed Successfully!"
- No Python errors or exceptions
- No "FAILED" status messages

**❌ BAD SIGNS:**
- Python ImportError or ModuleNotFoundError
- "FAILED" status
- Spark exceptions or Java errors
- Process exits before completion

---

### Step 7: Run Automated Smoke Test ✅

```bash
bash tests/smoke_test.sh
```

**Expected output:**
```
🧪 E-commerce Pipeline Smoke Test
==================================

📊 Test 1: Checking Hudi Tables...
✅ seller_catalog_hudi exists (XXX files)
✅ company_sales_hudi exists (XXX files)
✅ competitor_sales_hudi exists (XXX files)

📝 Test 2: Checking Recommendations...
✅ Recommendations CSV exists (XXXX lines)
✅ CSV has correct header

🚫 Test 3: Checking Quarantine Zone...
✅ No quarantine data (all records valid)

📈 Test 4: Checking Metrics...
✅ Metrics files created (4 files)
  ✓ ETL_SellerCatalog: SUCCESS
  ✓ ETL_CompanySales: SUCCESS
  ✓ ETL_CompetitorSales: SUCCESS
  ✓ Consumption_Recommendation: SUCCESS

🔍 Test 5: Checking for Common Issues...
✅ All recommendations have positive revenue
✅ Recommendations for XX unique sellers

==================================
📊 TEST SUMMARY
==================================
✅ Passed: 15
⚠️  Warnings: 0
❌ Failed: 0

🎉 ALL TESTS PASSED!
Pipeline executed successfully. Ready for Phase 2.
```

---

### Step 8: Verify Key Metrics 📊

```bash
# Check company_sales metrics (THIS IS CRITICAL)
cat data/metrics/ETL_CompanySales_*.json | jq '.records'
```

**Expected output:**
```json
{
  "input_count": 1000000,
  "valid_count": 1000000,
  "invalid_count": 0,
  "duplicate_count": 0,        ← Should be 0 or very small
  "output_count": 1000000      ← Should equal valid_count!
}
```

**✅ SUCCESS if:**
- `duplicate_count` is 0 or less than 10
- `output_count` equals `valid_count`
- No massive data loss

**❌ FAILURE if:**
- `duplicate_count` is huge (like 999,000)
- `output_count` is much smaller than `valid_count`
- This means old bug still present (but shouldn't be!)

---

### Step 9: Inspect Sample Recommendations

```bash
head -20 data/processed/recommendations_csv/part-*.csv
```

**Expected format:**
```csv
seller_id,item_id,item_name,category,market_price,expected_units_sold,expected_revenue
S001,I10000,Apple Iphone 15 Pro,Electronics,111360.8,1696.0,188828876.8
S001,I10001,Nike Air Zoom Pegasus,Footwear,101665.57,96.0,9759895.72
...
```

**Check:**
- ✅ All `market_price` values are positive
- ✅ All `expected_revenue` values are positive
- ✅ Multiple sellers have recommendations
- ✅ Item names make sense

---

## 📊 What To Report Back

### If ALL TESTS PASSED ✅

Tell me:
```
✅ ALL TESTS PASSED!

Key Metrics:
- Input: 1,000,000 records
- Output: 1,000,000 records
- Duplicates removed: 0
- Recommendations generated: XXXX lines
- All smoke tests: PASS

Phase 1 fixes are working perfectly!
Ready to continue to Phase 2.
```

---

### If ANY TESTS FAILED ❌

Tell me:
```
❌ TESTS FAILED

Failed at: [Step number]
Error message: [Copy exact error]
Smoke test output: [Copy relevant parts]

Metrics:
- duplicate_count: [value]
- output_count: [value]
```

And attach or paste:
- Terminal output from pipeline run
- Smoke test output
- Any error messages

---

## 🐛 Troubleshooting

### Error: "No such file or directory: data/raw/..."
**Fix:**
```bash
bash scripts/setup_data.sh
```

### Error: "Cannot connect to Docker daemon"
**Fix:**
- Start Docker Desktop
- Wait for it to fully start
- Try again

### Error: "Out of memory"
**Fix:**
- Open Docker Desktop → Settings → Resources
- Increase Memory to 8GB or more
- Apply & Restart
- Try again

### Error: "ModuleNotFoundError: No module named 'pyspark'"
**Fix:**
- This shouldn't happen in Docker
- Try: `docker compose build --no-cache`
- If persists, check Dockerfile has `RUN pip3 install -r requirements.txt`

### Pipeline hangs or takes too long
**Fix:**
- First run takes longer (downloading Spark/Hudi packages)
- Wait up to 20 minutes
- If still stuck, Ctrl+C and check Docker logs

---

## ⏱️ Expected Timeline

| Step | Time | Status |
|------|------|--------|
| Pull changes | 10 sec | Instant |
| Clean outputs | 5 sec | Instant |
| Build Docker | 5-10 min | First time only |
| Run pipeline | 10-15 min | Main execution |
| Smoke test | 10 sec | Instant |
| Verify metrics | 30 sec | Manual check |
| **TOTAL** | **15-25 min** | **One-time setup** |

Future runs (after Docker built): Only 10-15 minutes!

---

## 🎯 Success Criteria Checklist

After running all steps, you should have:

- [ ] All 4 pipelines completed successfully
- [ ] No Python errors in terminal
- [ ] 3 Hudi tables in `data/processed/`
- [ ] Recommendations CSV generated
- [ ] Smoke test shows: "🎉 ALL TESTS PASSED!"
- [ ] Metrics show minimal duplicate_count
- [ ] Metrics show output_count ≈ valid_count
- [ ] Recommendations have positive revenue values

**If all checked:** Phase 1 is VERIFIED WORKING! ✅

---

## 📸 Optional: Take Screenshots

For your records (or to show your teacher):
1. Terminal showing "All Pipelines Completed Successfully!"
2. Smoke test output showing all green checkmarks
3. Metrics JSON showing correct counts
4. Sample recommendations CSV

---

## 🚀 After Tests Pass

Come back and tell me:
- ✅ "All tests passed!"
- Paste key metrics
- Ask: "What's next?"

Then we'll proceed to:
- **Phase 2:** Architecture documentation (30 mins)
- **Phase 3:** Sample outputs and validation (30 mins)
- **Phase 4:** Final polish (30 mins)
- **Total:** 90 minutes to perfection!

---

## 🆘 Need Help?

If you get stuck:
1. Copy the EXACT error message
2. Note which step failed
3. Paste relevant terminal output
4. Ask me and I'll help debug!

---

**Ready? Let's test! 🚀**

Run the commands above and report back with results!
