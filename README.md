# E-commerce Recommendation System

**Student:** Anik Das
**Roll No:** 2025EM1100026
**Course:** Data Storage and Pipeline Assignment

---

## Overview

This project implements a recommendation system for e-commerce sellers using Apache Spark and Apache Hudi. It analyzes sales data to identify top-selling items and recommends products that sellers should add to their catalogs to increase revenue.

### Key Features

- **3 ETL Pipelines:** Process seller catalog, company sales, and competitor sales data
- **Apache Hudi:** ACID transactions, schema evolution, incremental upserts
- **Medallion Architecture:** Bronze → Silver → Gold layers + Quarantine zone
- **Data Quality:** Comprehensive validation with automatic quarantine of bad records
- **Recommendation Engine:** Calculates expected revenue for missing items per seller

---

## Project Structure

```
2025EM1100026/ecommerce_seller_recommendation/local/
├── configs/
│   └── ecomm_prod.yml              # Configuration (input/output paths only)
│
├── src/
│   ├── etl_seller_catalog.py       # ETL Pipeline 1
│   ├── etl_company_sales.py        # ETL Pipeline 2
│   ├── etl_competitor_sales.py     # ETL Pipeline 3
│   ├── consumption_recommendation.py  # Consumption Layer
│   ├── utils.py                    # Helper functions
│   └── metrics.py                  # Metrics tracking
│
├── scripts/
│   ├── etl_seller_catalog_spark_submit.sh
│   ├── etl_company_sales_spark_submit.sh
│   ├── etl_competitor_sales_spark_submit.sh
│   ├── consumption_recommendation_spark_submit.sh
│   ├── run_all_pipelines.sh        # Orchestrator (runs all 4 pipelines)
│   ├── setup_data.sh               # Data preparation
│   └── demo_incremental_processing.sh  # Incremental processing demo
│
├── data/
│   ├── raw/                        # Input CSV files
│   ├── processed/                  # Output Hudi tables + CSV
│   └── quarantine/                 # Invalid records
│
├── Dockerfile                      # Docker configuration
├── docker-compose.yml              # Docker Compose setup
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

---

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- At least 8GB RAM allocated to Docker
- 10GB free disk space
- Input datasets (`input_data_sets.zip`)

### Step 1: Setup Data

Place `input_data_sets.zip` in the project root and run:

```bash
bash scripts/setup_data.sh
```

Or manually:

```bash
unzip input_data_sets.zip
mkdir -p data/raw/seller_catalog data/raw/company_sales data/raw/competitor_sales
cp input_data_sets/clean/*.csv data/raw/*/
rm -rf input_data_sets/ input_data_sets.zip
```

### Step 2: Build Docker Image

```bash
docker compose build
```

**Time:** 5-10 minutes (first time only)

### Step 3: Run Complete Pipeline

```bash
docker compose run spark-app bash /workspace/scripts/run_all_pipelines.sh
```

**Time:** 10-20 minutes
**Runs:** All 4 pipelines in sequence (3 ETL + 1 consumption)

### Expected Output

```
==========================================
E-commerce Recommendation System Pipeline
==========================================

Step 1/4: Running ETL for Seller Catalog...
✓ Loaded 1,000,000 records
✓ Valid: 1,000,000 | Invalid: 0
✓ Removed 0 exact duplicate rows
✓ Written to Hudi table

Step 2/4: Running ETL for Company Sales...
✓ Complete

Step 3/4: Running ETL for Competitor Sales...
✓ Complete

Step 4/4: Running Consumption Layer (Recommendations)...
✓ Generated recommendations
✓ Written to CSV

==========================================
All Pipelines Completed Successfully!
==========================================
```

---

## Outputs

### Hudi Tables (Gold Layer)

```
data/processed/
├── seller_catalog_hudi/         # ~1M records, partitioned by category
├── company_sales_hudi/          # ~1M records, all sales transactions
└── competitor_sales_hudi/       # ~1M records, competitor data
```

### CSV Recommendations

```
data/processed/recommendations_csv/
└── part-*.csv                   # Seller recommendations

Format: seller_id,item_id,item_name,category,market_price,expected_units_sold,expected_revenue
```

### Quarantine Zone

```
data/quarantine/
├── seller_catalog/              # Invalid catalog records
├── company_sales/               # Invalid sales records
└── competitor_sales/            # Invalid competitor records

Each record includes dq_failure_reason column.
```

---

## Configuration

All paths are configured in `configs/ecomm_prod.yml`:

```yaml
seller_catalog:
  input_path: "/workspace/data/raw/seller_catalog/"
  hudi_output_path: "/workspace/data/processed/seller_catalog_hudi/"

company_sales:
  input_path: "/workspace/data/raw/company_sales/"
  hudi_output_path: "/workspace/data/processed/company_sales_hudi/"

competitor_sales:
  input_path: "/workspace/data/raw/competitor_sales/"
  hudi_output_path: "/workspace/data/processed/competitor_sales_hudi/"

recommendation:
  seller_catalog_hudi: "/workspace/data/processed/seller_catalog_hudi/"
  company_sales_hudi: "/workspace/data/processed/company_sales_hudi/"
  competitor_sales_hudi: "/workspace/data/processed/competitor_sales_hudi/"
  output_csv: "/workspace/data/processed/recommendations_csv/seller_recommend_data.csv"
```

---

## Running Individual Pipelines

```bash
# Inside Docker container
docker compose run spark-app bash

# Then run individual pipelines:
bash /workspace/scripts/etl_seller_catalog_spark_submit.sh
bash /workspace/scripts/etl_company_sales_spark_submit.sh
bash /workspace/scripts/etl_competitor_sales_spark_submit.sh
bash /workspace/scripts/consumption_recommendation_spark_submit.sh
```

---

## Technical Implementation

### Data Quality Checks

**Seller Catalog:**
- seller_id IS NOT NULL
- item_id IS NOT NULL
- marketplace_price >= 0
- stock_qty >= 0
- item_name IS NOT NULL
- category IS NOT NULL

**Company Sales:**
- item_id IS NOT NULL
- units_sold >= 0
- revenue >= 0
- sale_date valid and not future

**Competitor Sales:**
- All company sales checks
- seller_id IS NOT NULL
- marketplace_price >= 0

### Apache Hudi Configuration

**Seller Catalog:**
```python
"hoodie.datasource.write.recordkey.field": "seller_id,item_id"  # Composite key
"hoodie.datasource.write.partitionpath.field": "category"        # Partition by category
"hoodie.datasource.write.operation": "upsert"                    # Insert + Update
"hoodie.schema.on.read.enable": "true"                           # Schema evolution
```

**Company Sales & Competitor Sales:**
- Simple/composite keys as appropriate
- Upsert operation for idempotency
- Schema evolution enabled
- COPY_ON_WRITE table type

### Recommendation Logic

```python
# Expected units sold per seller
expected_units_sold = total_units_sold / number_of_sellers

# Expected revenue calculation
expected_revenue = expected_units_sold × marketplace_price
```

---

## Medallion Architecture

### Bronze Layer
- Raw CSV files moved from source
- Timestamped archives created
- Immutable audit trail

### Silver Layer (Implicit)
- Data cleaning (trim, normalize casing)
- Type conversions (String → Int/Double/Date)
- In-memory transformations

### Gold Layer
- Validated, production-ready data
- Apache Hudi tables with ACID guarantees
- Ready for analytics and recommendations

### Quarantine Zone
- Invalid records isolated
- Includes failure reasons
- Enables data remediation

---

## Incremental Processing

The pipeline supports daily incremental data processing:

```bash
# Run demo to see incremental behavior
docker compose run spark-app bash /workspace/scripts/demo_incremental_processing.sh
```

**How it works:**
- Day 1: Initial load of records
- Day 2: New records inserted, existing records updated
- Hudi's upsert ensures no duplicates
- Idempotent operations (safe to replay)

---

## Troubleshooting

### "No CSV files found in directory"
**Fix:** Run `bash scripts/setup_data.sh` or manually copy data files

### "Out of memory" errors
**Fix:**
- Open Docker Desktop → Settings → Resources
- Increase Memory to 8GB or more
- Apply & Restart

### Pipeline hangs
**Fix:**
- First run downloads Spark/Hudi packages (takes time)
- Wait up to 20 minutes
- Check Docker logs for errors

### "ModuleNotFoundError"
**Fix:**
```bash
docker compose build --no-cache
```

### Start fresh
```bash
# Clean all outputs
rm -rf data/processed/* data/quarantine/* data/metrics/*

# Rebuild and rerun
docker compose build
docker compose run spark-app bash /workspace/scripts/run_all_pipelines.sh
```

---

## Spark Submit Commands

Each pipeline uses the same Spark configuration:

```bash
spark-submit \
  --packages org.apache.hudi:hudi-spark3.5-bundle_2.12:0.15.0,\
             org.apache.hadoop:hadoop-aws:3.3.4,\
             com.amazonaws:aws-java-sdk-bundle:1.12.262 \
  --conf spark.serializer=org.apache.spark.serializer.KryoSerializer \
  --conf spark.sql.legacy.timeParserPolicy=LEGACY \
  /workspace/src/<pipeline_name>.py \
  --config /workspace/configs/ecomm_prod.yml
```

---

## Metrics Tracking

Each pipeline generates metrics in `data/metrics/*.json`:

```json
{
  "pipeline_name": "ETL_CompanySales",
  "duration_seconds": 180,
  "status": "SUCCESS",
  "records": {
    "input_count": 1000000,
    "valid_count": 1000000,
    "invalid_count": 0,
    "duplicate_count": 0,
    "output_count": 1000000
  },
  "data_quality": {
    "valid_percentage": 100.0,
    "invalid_percentage": 0.0
  }
}
```

---

## Testing in GitHub Codespaces

```bash
# 1. Open Codespaces from GitHub
# Repository → Code → Codespaces → Create

# 2. Setup data
bash scripts/setup_data.sh

# 3. Build Docker
docker compose build

# 4. Run pipeline
docker compose run spark-app bash /workspace/scripts/run_all_pipelines.sh

# 5. Verify outputs
ls -lh data/processed/
head -20 data/processed/recommendations_csv/part-*.csv
cat data/metrics/*.json | jq '.records'
```

---

## Key Implementation Notes

### Data Deduplication

**Sales Data (Company & Competitor):**
- Only removes **exact duplicate rows** (all columns identical)
- Preserves multiple sales transactions for same item
- Aggregation happens in consumption layer

```python
# Removes only exact duplicates
df.dropDuplicates()  # NOT dropDuplicates(["item_id"])
```

**Catalog Data (Seller):**
- Deduplicates by composite key (seller_id + item_id)
- Keeps most recent price when duplicates exist

### Schema Evolution

All Hudi tables support schema evolution:
```python
"hoodie.schema.on.read.enable": "true"
"hoodie.datasource.write.reconcile.schema": "true"
```

This allows:
- Adding new columns without breaking queries
- Handling data type changes
- Adapting to evolving data structures

---

## Assignment Requirements Coverage

✅ **ETL Ingestion (15 marks)**
- 3 separate ETL pipelines
- YAML-configurable paths
- Apache Hudi with schema evolution
- Incremental upsert support
- Data cleaning and type conversion
- Comprehensive DQ validation
- Quarantine zone with failure reasons
- Medallion architecture (Bronze/Silver/Gold)
- Overwrite mode output

✅ **Consumption Layer (5 marks)**
- Reads 3 Hudi tables
- Aggregates sales data
- Identifies top-selling items per category
- Compares catalogs to find missing items
- Calculates expected revenue
- Outputs recommendations to CSV
- Validation checks on output

---

## Tech Stack

- **Apache Spark 3.5.0** - Distributed data processing
- **Apache Hudi 0.15.0** - Data lake storage with ACID
- **Python 3.9** - Programming language
- **Docker** - Containerization
- **PySpark** - Python Spark API

---

## Contact

**Student:** Anik Das
**Roll Number:** 2025EM1100026

---

**Last Updated:** November 19, 2025
