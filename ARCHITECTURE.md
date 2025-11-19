# System Architecture

**Project:** E-commerce Recommendation System
**Student:** Anik Das (Roll No: 2025EM1100026)
**Architecture Pattern:** Medallion Architecture with Quarantine Zone

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA FLOW ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│   SOURCE     │  Landing zone for raw CSV files
│   (Landing)  │  - seller_catalog_clean.csv
│              │  - company_sales_clean.csv
└──────┬───────┘  - competitor_sales_clean.csv
       │
       │ [Extract & Move]
       ↓
┌──────────────┐
│   BRONZE     │  🥉 Raw data layer (immutable)
│   Layer      │  - Files moved from source
│              │  - Timestamped archives created
└──────┬───────┘  - Format: CSV
       │
       │ [Read & Parse]
       ↓
┌──────────────┐
│   SILVER     │  🥈 Cleaned data layer (in-memory)
│   Layer      │  - Whitespace trimmed
│  (implicit)  │  - Types converted (String → Int/Double/Date)
│              │  - Casing normalized (Title Case)
└──────┬───────┘  - Null handling
       │
       │ [Data Quality Checks]
       ↓
   ┌───┴────┐
   │        │
   ↓        ↓
┌──────┐ ┌────────────┐
│ GOLD │ │ QUARANTINE │  ⚠️ Invalid data isolation
│      │ │   ZONE     │  - Records failing DQ checks
│ ✓ Valid│ │            │  - Includes failure reasons
│      │ │ ✗ Invalid  │  - Format: Parquet
└──┬───┘ └────────────┘
   │
   │ [Apache Hudi Write]
   ↓
┌──────────────┐
│   GOLD       │  🥇 Production-ready data
│   Layer      │  - Format: Apache Hudi (COPY_ON_WRITE)
│              │  - ACID transactions
│  (Hudi)      │  - Schema evolution support
│              │  - Incremental upserts
└──────┬───────┘  - Time travel capabilities
       │
       │ [Aggregation & Business Logic]
       ↓
┌──────────────┐
│ CONSUMPTION  │  📊 Analytics-ready layer
│   Layer      │  - Top-selling items per category
│              │  - Missing item identification
│              │  - Revenue calculations
└──────┬───────┘  - Format: CSV
       │
       ↓
┌──────────────┐
│  OUTPUTS     │  📁 Final deliverables
│              │  - seller_recommend_data.csv
│              │  - company_catalog_gap/
└──────────────┘
```

---

## 📊 Medallion Architecture Layers

### 🥉 Bronze Layer (Raw Zone)

**Location:** `data/bronze/`

**Purpose:**
- Store raw data exactly as received from source
- Immutable landing zone
- Audit trail with timestamped archives

**Characteristics:**
- Format: CSV (original format preserved)
- No transformations applied
- Full data lineage tracking
- Archived to `data/archive/` with timestamps

**Data Flow:**
```python
# Extract phase in ETL
source_file → bronze_layer → archive_with_timestamp
```

**Implementation:**
```python
def extract_new_files(source_path, bronze_path, archive_path):
    """Move CSV files from source to bronze, create archives"""
    for file in source_files:
        shutil.move(source_file, bronze_path)  # Move to bronze
        shutil.copy(bronze_file, archive_path)  # Archive with timestamp
```

---

### 🥈 Silver Layer (Cleaned Zone)

**Location:** In-memory (implicit layer)

**Purpose:**
- Clean and standardize data
- Type conversions
- Basic transformations
- Prepare for validation

**Transformations Applied:**

1. **String Cleaning:**
   ```python
   .withColumn("seller_id", F.trim(F.col("seller_id")))
   .withColumn("item_name", F.initcap(F.col("item_name")))  # Title Case
   ```

2. **Type Conversions:**
   ```python
   .withColumn("marketplace_price", F.col("marketplace_price").cast(T.DoubleType()))
   .withColumn("stock_qty", F.col("stock_qty").cast(T.IntegerType()))
   .withColumn("sale_date", F.to_date(F.col("sale_date"), "yyyy-MM-dd"))
   ```

3. **Null Handling:**
   ```python
   .withColumn("stock_qty", F.coalesce(F.col("stock_qty"), F.lit(0)))
   ```

**Why Implicit?**
- Transformations happen in-memory during ETL
- No physical storage of intermediate cleaned data
- More efficient (no extra I/O operations)
- Follows modern data engineering patterns

---

### 🥇 Gold Layer (Trusted Zone)

**Location:** `data/processed/*_hudi/`

**Purpose:**
- Production-ready, validated data
- Optimized for analytics queries
- ACID transaction guarantees
- Schema evolution support

**Format:** Apache Hudi (Hadoop Update Delete Insert)

**Hudi Configuration:**

```python
hudi_options = {
    # Table identification
    "hoodie.table.name": "seller_catalog_hudi",

    # Key configuration
    "hoodie.datasource.write.recordkey.field": "seller_id,item_id",
    "hoodie.datasource.write.partitionpath.field": "category",
    "hoodie.datasource.write.precombine.field": "marketplace_price",

    # Write operation
    "hoodie.datasource.write.operation": "upsert",
    "hoodie.datasource.write.table.type": "COPY_ON_WRITE",

    # Schema evolution
    "hoodie.schema.on.read.enable": "true",
    "hoodie.datasource.write.reconcile.schema": "true",
    "hoodie.avro.schema.validate": "false"
}
```

**Key Features:**

1. **ACID Transactions:**
   - Atomic writes (all or nothing)
   - Consistent reads
   - Isolated operations
   - Durable storage

2. **Upsert Support:**
   - Insert new records
   - Update existing records based on record key
   - Idempotent operations (can replay safely)

3. **Schema Evolution:**
   - Add new columns without breaking existing queries
   - Change data types with validation
   - Handle schema drift automatically

4. **Time Travel:**
   - Query data as of specific timestamp
   - Rollback to previous versions
   - Audit historical changes

---

### ⚠️ Quarantine Zone

**Location:** `data/quarantine/`

**Purpose:**
- Isolate invalid records
- Track data quality issues
- Enable data remediation
- Maintain data lineage

**Structure:**
```
quarantine/
├── seller_catalog/
│   └── [parquet files with failure reasons]
├── company_sales/
│   └── [parquet files with failure reasons]
└── competitor_sales/
    └── [parquet files with failure reasons]
```

**Quarantine Record Schema:**
```
Original Columns + dq_failure_reason (STRING)
```

**Example Failure Reasons:**
- `seller_id_missing;`
- `price_invalid;`
- `units_sold_negative;`
- `sale_date_invalid;`

**Implementation:**
```python
df_with_checks = (
    df.withColumn("dq_failure_reason", F.lit(""))
      .withColumn("dq_failure_reason",
                  F.when(F.col("seller_id").isNull(),
                        F.concat(F.col("dq_failure_reason"),
                                F.lit("seller_id_missing;")))
                  .otherwise(F.col("dq_failure_reason")))
)

invalid_df = df_with_checks.filter(F.col("dq_failure_reason") != "")
invalid_df.write.mode("overwrite").parquet(quarantine_path)
```

---

## 🔄 Data Quality Framework

### DQ Check Categories

1. **Presence Checks:**
   - NOT NULL validation
   - Empty string detection
   - Required field enforcement

2. **Range Checks:**
   - Numeric bounds (price ≥ 0)
   - Date validity (not future dates)
   - Quantity constraints (stock ≥ 0)

3. **Type Checks:**
   - Correct data types
   - Format validation (dates)
   - Numeric parsing

4. **Business Rules:**
   - Expected revenue = units_sold × market_price
   - Category standardization
   - Seller/item relationships

### DQ Implementation Pattern

```python
def apply_dq_checks(df: DataFrame) -> Tuple[DataFrame, DataFrame]:
    """Separate valid and invalid records"""

    # Add failure reason tracking
    df_with_checks = df.withColumn("dq_failure_reason", F.lit(""))

    # Apply checks (accumulate failure reasons)
    df_with_checks = (
        df_with_checks
        .withColumn("dq_failure_reason",
                   F.when(CHECK_CONDITION,
                         F.concat(F.col("dq_failure_reason"),
                                 F.lit("failure_reason;")))
                   .otherwise(F.col("dq_failure_reason")))
    )

    # Separate valid from invalid
    valid_df = df_with_checks.filter(F.col("dq_failure_reason") == "")
    invalid_df = df_with_checks.filter(F.col("dq_failure_reason") != "")

    return valid_df, invalid_df
```

---

## 🔧 Apache Hudi Deep Dive

### Why Hudi?

1. **Incremental Processing:**
   - Process only changed records
   - Efficient for daily updates
   - Reduces processing time and cost

2. **ACID Guarantees:**
   - No partial writes
   - Consistent snapshots
   - Transactional semantics

3. **Schema Evolution:**
   - Adapt to changing data structures
   - Backward compatibility
   - Forward compatibility

4. **Update/Delete Support:**
   - Modify existing records
   - Soft deletes (mark as deleted)
   - Hard deletes (physical removal)

### Hudi Table Types

We use **COPY_ON_WRITE (COW):**

**Characteristics:**
- Updates create new file versions
- Reads are fast (no merge needed)
- Writes are slower (full file rewrite)
- Best for read-heavy workloads

**Alternative: MERGE_ON_READ (MOR):**
- Updates write to delta logs
- Reads require merge operation
- Writes are fast
- Best for write-heavy workloads

**Our Choice:** COW because:
- Analytics workload (more reads than writes)
- Daily batch updates (not real-time)
- Simpler query patterns
- Better suited for assignment requirements

### Key Configuration Explained

```python
# Record Key: Uniquely identifies records
"hoodie.datasource.write.recordkey.field": "seller_id,item_id"
# → Composite key for seller catalog
# → Simple key (item_id) for company sales

# Partition Key: Physical data organization
"hoodie.datasource.write.partitionpath.field": "category"
# → Enables partition pruning for category-based queries
# → Speeds up top items per category analysis

# Precombine Key: Conflict resolution
"hoodie.datasource.write.precombine.field": "marketplace_price"
# → When multiple updates for same record, use latest price
# → Could be timestamp in production
```

---

## 📈 Consumption Layer Architecture

### Purpose
Transform gold layer data into business insights and recommendations.

### Key Operations

1. **Aggregation:**
   ```python
   # Total units sold per item across all transactions
   company_sales.groupBy("item_id").agg(
       F.sum("units_sold").alias("total_units_sold"),
       F.sum("revenue").alias("total_revenue")
   )
   ```

2. **Ranking:**
   ```python
   # Top 10 items per category
   window_spec = Window.partitionBy("category") \
                       .orderBy(F.col("total_units_sold").desc())

   top_items = item_sales.withColumn("rank", F.row_number().over(window_spec)) \
                         .filter(F.col("rank") <= 10)
   ```

3. **Gap Analysis:**
   ```python
   # Items missing from seller's catalog
   missing_items = all_top_items.join(
       seller_items,
       (seller_items.seller_id == sellers.seller_id) &
       (seller_items.item_id == all_top_items.item_id),
       "left_anti"  # Keep only non-matches
   )
   ```

4. **Revenue Calculation:**
   ```python
   expected_revenue = expected_units_sold × market_price

   # Where expected_units_sold = total_units / number_of_sellers
   ```

---

## 🔄 Incremental Processing

### Daily Batch Pattern

```
Day 1: Initial Load
┌────────┐
│ Source │ → Bronze → Silver → Gold (Full Load)
└────────┘    1M records

Day 2: Incremental Update
┌────────┐
│ Source │ → Bronze → Silver → Gold (Upsert)
└────────┘    50K new + 10K updates

Result: Gold layer has 1.05M records (1M + 50K new)
        10K records updated via upsert
```

### Idempotent Operations

Hudi's upsert ensures:
- Reprocessing same data = same result
- No duplicate records
- Safe to replay failed jobs

**Example:**
```python
# Day 1: Insert record
(seller_id='S001', item_id='I100', price=100)

# Day 2: Update same record
(seller_id='S001', item_id='I100', price=120)

# Result: Single record with price=120 (not two records!)
```

---

## 📁 Directory Structure

```
data-storage-pipeline-assignment-complete-/
├── configs/
│   └── ecomm_prod.yml              # Configuration (paths only)
│
├── src/
│   ├── etl_seller_catalog.py       # ETL Pipeline 1
│   ├── etl_company_sales.py        # ETL Pipeline 2
│   ├── etl_competitor_sales.py     # ETL Pipeline 3
│   ├── consumption_recommendation.py # Consumption Layer
│   ├── utils.py                    # Helper functions
│   └── metrics.py                  # Metrics tracking
│
├── scripts/
│   ├── run_all_pipelines.sh        # Orchestration
│   ├── etl_*_spark_submit.sh       # Individual pipeline runners
│   └── setup_data.sh               # Data preparation
│
├── data/
│   ├── raw/                        # Source data (CSV)
│   │   ├── seller_catalog/
│   │   ├── company_sales/
│   │   └── competitor_sales/
│   │
│   ├── bronze/                     # Raw landing (generated)
│   │   ├── seller_catalog/
│   │   ├── company_sales/
│   │   └── competitor_sales/
│   │
│   ├── archive/                    # Timestamped backups
│   │   ├── seller_catalog/
│   │   ├── company_sales/
│   │   └── competitor_sales/
│   │
│   ├── processed/                  # Gold layer (Hudi + CSV)
│   │   ├── seller_catalog_hudi/
│   │   ├── company_sales_hudi/
│   │   ├── competitor_sales_hudi/
│   │   └── recommendations_csv/
│   │
│   ├── quarantine/                 # Invalid records
│   │   ├── seller_catalog/
│   │   ├── company_sales/
│   │   └── competitor_sales/
│   │
│   └── metrics/                    # Pipeline execution metrics
│       └── *.json
│
├── tests/
│   └── smoke_test.sh               # Automated validation
│
└── docs/
    ├── ARCHITECTURE.md             # This file
    ├── CHANGELOG.md                # Change history
    ├── CODE_REVIEW.md              # Code analysis
    ├── TEST_PLAN.md                # Testing guide
    └── TEST_RESULTS.md             # Test outcomes
```

---

## 🎯 Design Decisions

### 1. Deduplication Strategy

**Decision:** Only remove exact duplicate rows (all columns identical)

**Rationale:**
- Sales data is transactional (multiple sales per item valid)
- Deduplicating by key columns loses business data
- Aggregation happens in consumption layer

**Implementation:**
```python
# ETL Layer: Minimal deduplication
df.dropDuplicates()  # All columns must match

# Consumption Layer: Aggregation
df.groupBy("item_id").agg(F.sum("units_sold"))
```

### 2. Hudi Key Selection

| Dataset | Record Key | Partition Key | Rationale |
|---------|-----------|---------------|-----------|
| Seller Catalog | seller_id + item_id | category | Composite key ensures uniqueness; partition by category for analytics |
| Company Sales | item_id | none | Simple key; no partitioning (small dataset) |
| Competitor Sales | seller_id + item_id | none | Composite key; no natural partition column |

### 3. Schema Evolution Strategy

**Enabled globally:**
```python
"hoodie.schema.on.read.enable": "true"
"hoodie.datasource.write.reconcile.schema": "true"
```

**Supports:**
- Adding new columns
- Changing nullable constraints
- Type promotions (Int → Long)

**Does NOT support:**
- Renaming columns (breaks existing queries)
- Removing columns (data loss)
- Type demotions (Long → Int)

### 4. Overwrite Mode Justification

**Assignment Requirement:**
> "Your final output should be 3 different Hudi tables with overwrite mode"

**Implementation:**
```python
valid_df.write.format("hudi").options(**hudi_options).mode("overwrite").save(path)
```

**Why Overwrite + Upsert?**
- `mode("overwrite")` → DataFrame write mode (Spark API)
- `"hoodie.datasource.write.operation": "upsert"` → Hudi internal operation
- Together: Replace Hudi table, but handle updates intelligently

---

## 🚀 Performance Optimizations

### 1. DataFrame Caching
```python
df.cache()  # Before multiple actions
df.count()  # Action 1
df.filter(...).count()  # Action 2 (uses cache)
df.unpersist()  # Free memory
```

### 2. Partition Pruning
```python
# Query only Electronics category
spark.read.format("hudi") \
     .load(path) \
     .filter(F.col("category") == "Electronics")
# → Only reads Electronics partition files!
```

### 3. Predicate Pushdown
```python
# Hudi pushes filter to storage layer
df.filter(F.col("marketplace_price") > 100)
# → Reads fewer records from disk
```

---

## 📊 Monitoring & Observability

### Metrics Collected

Every pipeline tracks:
```json
{
  "pipeline_name": "ETL_SellerCatalog",
  "start_time": "2025-11-19T10:00:00",
  "end_time": "2025-11-19T10:05:00",
  "duration_seconds": 300,
  "status": "SUCCESS",
  "records": {
    "input_count": 1000000,
    "valid_count": 999500,
    "invalid_count": 500,
    "duplicate_count": 0,
    "output_count": 999500
  },
  "data_quality": {
    "valid_percentage": 99.95,
    "invalid_percentage": 0.05
  }
}
```

### Logging Levels
```python
logger.info("Normal operations")
logger.warning("Data quality issues")
logger.error("Pipeline failures")
```

---

## 🎓 Assignment Alignment

### Medallion Architecture ✅
- **Bronze:** Raw data preservation
- **Silver:** Cleaned & typed (implicit)
- **Gold:** Validated Hudi tables
- **Quarantine:** DQ failure isolation

### Apache Hudi ✅
- Schema evolution enabled
- Incremental upserts configured
- COPY_ON_WRITE table type
- Composite keys for catalogs

### Data Quality ✅
- Comprehensive DQ checks
- Quarantine with failure reasons
- Metrics tracking DQ percentages

### Business Logic ✅
- Top 10 items per category
- Missing item identification
- Expected revenue calculation
- Seller-specific recommendations

---

**Architecture Version:** 1.0
**Last Updated:** November 19, 2025
**Author:** Anik Das (2025EM1100026)
