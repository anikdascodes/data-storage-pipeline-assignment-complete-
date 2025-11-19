# Changelog - Assignment Fixes

**Date:** November 19, 2025
**Student:** Anik Das (Roll No: 2025EM1100026)

---

## Phase 1: CRITICAL FIXES ✅ COMPLETED

### 🔴 Fix 1: Corrected Deduplication Logic in ETL Pipelines

**Problem Identified:**
- `etl_company_sales.py` and `etl_competitor_sales.py` were deduplicating by key columns
- This removed valid sales transactions (transactional data should allow multiples)
- Would cause incorrect aggregations in recommendation calculations

**Files Changed:**
- `src/etl_company_sales.py`
- `src/etl_competitor_sales.py`

**Changes Made:**

#### etl_company_sales.py
**Before:**
```python
def remove_duplicates(df: DataFrame) -> DataFrame:
    """Remove duplicates based on item_id"""
    deduped_df = (
        df
        .orderBy(F.col("sale_date").desc())
        .dropDuplicates(["item_id"])  # ❌ Removes multiple sales per item
    )
```

**After:**
```python
def remove_duplicates(df: DataFrame) -> DataFrame:
    """Remove exact duplicate rows (all columns identical)"""
    deduped_df = df.dropDuplicates()  # ✅ Only removes exact duplicates
    duplicates_removed = df.count() - deduped_df.count()
    logger.info(f"Removed {duplicates_removed} exact duplicate rows")
```

#### etl_competitor_sales.py
- Applied same fix: changed from `dropDuplicates(["seller_id", "item_id"])` to `dropDuplicates()`
- Added comprehensive documentation explaining why

**Rationale:**
1. Sales data is **transactional** - same item can sell multiple times
2. Deduplicating by keys loses valid business data
3. Aggregation should happen in **consumption layer**, not ETL
4. Assignment description implies aggregating sales, not deduplicating

**Impact:**
- ✅ Preserves all valid sales transactions
- ✅ Consumption layer aggregations now work with complete data
- ✅ Expected revenue calculations will be accurate
- ✅ Top-selling item rankings use full sales history

**Verification:**
- Consumption layer already uses `F.sum("units_sold")` for aggregation ✅
- No changes needed in consumption layer - it was designed correctly
- Backups created: `*.py.backup` files

---

## Testing Status

### Before Fix:
- Each item would have only ONE sales record (most recent)
- Lost ~0 records in clean data (no duplicates in sample)
- But logic was wrong for real-world transactional data

### After Fix:
- Preserves ALL distinct sales transactions
- Only removes exact duplicate rows (all columns identical)
- Correct handling of transactional sales data

---

## Next Steps: Phase 2 (High Priority)

1. Add explicit medallion architecture documentation
2. Create incremental processing demonstration
3. Add validation checks in consumption layer
4. Create sample outputs

---

## Backup Files Created

- `src/etl_company_sales.py.backup`
- `src/etl_competitor_sales.py.backup`

To restore original:
```bash
cp src/etl_company_sales.py.backup src/etl_company_sales.py
cp src/etl_competitor_sales.py.backup src/etl_competitor_sales.py
```

---

## Code Review Checklist

- [x] Company sales deduplication fixed
- [x] Competitor sales deduplication fixed
- [x] Seller catalog deduplication is correct (keeps composite key logic)
- [x] Consumption layer aggregation verified
- [x] Documentation added explaining rationale
- [x] Backups created
- [ ] End-to-end pipeline tested
- [ ] Output data validated

---

**Status:** Phase 1 COMPLETE - Ready for Phase 2
