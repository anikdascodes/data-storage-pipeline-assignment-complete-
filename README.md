# E-commerce Recommendation System - Assignment 1

**Student:** Anik Das
**Roll No:** 2025EM1100026
**Course:** Data Storage and Pipeline Assignment

---

## Project Overview

This assignment builds a recommendation system for e-commerce sellers. It processes sales data to identify top-selling items that sellers don't currently have in their catalog, helping them make data-driven decisions about which products to add.

The pipeline uses Apache Spark and Apache Hudi to handle data ingestion, cleaning, validation, and recommendation generation.

---

## Quick Start (Docker Setup)

I've containerized everything so you don't need to install Spark or Hudi manually.

### Prerequisites
- Docker and Docker Compose
- At least 8GB RAM allocated to Docker
- Around 10GB free disk space

### Running the Assignment

**Step 1: Build the Docker image**
```bash
docker compose build
```
(This takes about 10-15 minutes the first time - downloads Spark and all dependencies)

**Step 2: Run all pipelines**
```bash
docker compose run spark-app bash /workspace/scripts/run_all_pipelines.sh
```

This runs all 4 components in sequence:
1. ETL for seller catalog
2. ETL for company sales
3. ETL for competitor sales
4. Final recommendation generation

Expected runtime: 10-20 minutes

---

## What Gets Produced

After running successfully, you'll find:

**Hudi Tables** (in `/workspace/data/processed/`):
- `seller_catalog_hudi/` - Cleaned seller catalog data
- `company_sales_hudi/` - Cleaned company sales data
- `competitor_sales_hudi/` - Cleaned competitor sales data

**Final Output**:
- `recommendations_csv/seller_recommend_data.csv` - Recommendations for each seller

**Data Quality**:
- `quarantine/` folders contain invalid records with reasons why they failed validation

---

## Project Structure

```
configs/
  ecomm_prod.yml                    # Main configuration file

src/
  etl_seller_catalog.py             # Pipeline 1: Seller catalog ETL
  etl_company_sales.py              # Pipeline 2: Company sales ETL
  etl_competitor_sales.py           # Pipeline 3: Competitor sales ETL
  consumption_recommendation.py     # Pipeline 4: Generate recommendations

scripts/
  etl_seller_catalog_spark_submit.sh
  etl_company_sales_spark_submit.sh
  etl_competitor_sales_spark_submit.sh
  consumption_recommendation_spark_submit.sh
  run_all_pipelines.sh              # Runs all 4 pipelines

data/
  raw/                              # Input CSV files (provided with assignment)
  processed/                        # Output Hudi tables and final CSV
  quarantine/                       # Bad records separated out
```

---

## How It Works

### ETL Pipelines (3 separate pipelines as required)

Each pipeline does the same basic steps:

1. **Read CSV data** from `/data/raw/`
2. **Clean the data**:
   - Trim whitespace
   - Normalize text (proper casing)
   - Convert data types (strings to numbers/dates)
3. **Apply data quality checks**:
   - Check for null/missing required fields
   - Validate ranges (no negative prices, valid dates, etc.)
4. **Separate good from bad**:
   - Valid records → Hudi table
   - Invalid records → Quarantine folder with failure reasons
5. **Remove duplicates** based on key fields

### Consumption Layer (Recommendation Logic)

1. Reads the 3 Hudi tables created by ETL
2. Finds top 10 selling items per category from company sales
3. Also finds top selling items from competitor data
4. For each seller, identifies which top items they DON'T have
5. Calculates expected revenue: `(avg units sold / # of sellers) × market price`
6. Outputs recommendations as CSV

---

## Technical Details

### Technologies Used
- Apache Spark 3.5.0
- Apache Hudi 0.15.0 (for data lake tables)
- Python 3.9
- Docker for containerization

### Hudi Configuration Choices

I used different key generators based on the data structure:

- **Seller Catalog & Competitor Sales**: ComplexKeyGenerator (composite key: seller_id + item_id)
- **Company Sales**: NonpartitionedKeyGenerator (single key: item_id)
- **Partitioning**: Seller catalog is partitioned by category for better performance

All tables use **overwrite mode** as specified in the assignment.

### Schema Evolution Support

Added Hudi configurations to handle schema changes:
```python
"hoodie.schema.on.read.enable": "true"
"hoodie.datasource.write.reconcile.schema": "true"
"hoodie.avro.schema.validate": "false"
```

This allows the pipeline to handle new columns or type changes in source data automatically.

### Data Quality Checks Implemented

**Seller Catalog** (6 checks):
- seller_id not null
- item_id not null
- item_name not null
- category not null
- price >= 0
- stock_qty >= 0

**Company Sales** (4 checks):
- item_id not null
- units_sold >= 0
- revenue >= 0
- sale_date valid and not future date

**Competitor Sales** (6 checks):
- item_id not null
- seller_id not null
- units_sold >= 0
- revenue >= 0
- marketplace_price >= 0
- sale_date valid and not future date

---

## Configuration File

The `configs/ecomm_prod.yml` file contains all input/output paths:

```yaml
seller_catalog:
  input_path: "/workspace/data/raw/seller_catalog/"
  hudi_output_path: "/workspace/data/processed/seller_catalog_hudi/"
  quarantine_path: "/workspace/data/quarantine/seller_catalog/"

company_sales:
  input_path: "/workspace/data/raw/company_sales/"
  hudi_output_path: "/workspace/data/processed/company_sales_hudi/"
  quarantine_path: "/workspace/data/quarantine/company_sales/"

competitor_sales:
  input_path: "/workspace/data/raw/competitor_sales/"
  hudi_output_path: "/workspace/data/processed/competitor_sales_hudi/"
  quarantine_path: "/workspace/data/quarantine/competitor_sales/"

recommendation:
  seller_catalog_hudi: "/workspace/data/processed/seller_catalog_hudi/"
  company_sales_hudi: "/workspace/data/processed/company_sales_hudi/"
  competitor_sales_hudi: "/workspace/data/processed/competitor_sales_hudi/"
  output_csv: "/workspace/data/processed/recommendations_csv/seller_recommend_data.csv"
```

There's also `ecomm_prod_fixed.yml` which includes additional paths for incremental processing (source, bronze, archive layers) if needed for daily batch runs.

---

## Running Individual Pipelines

If you want to run pipelines separately instead of all at once:

```bash
# Start the container
docker compose run spark-app bash

# Inside container, run individual pipelines:
bash /workspace/scripts/etl_seller_catalog_spark_submit.sh
bash /workspace/scripts/etl_company_sales_spark_submit.sh
bash /workspace/scripts/etl_competitor_sales_spark_submit.sh
bash /workspace/scripts/consumption_recommendation_spark_submit.sh
```

---

## Troubleshooting

**If you get Out of Memory errors:**
- Go to Docker Desktop settings
- Increase memory limit to at least 8GB

**If scripts won't execute:**
```bash
chmod +x scripts/*.sh
```

**To clean up and start fresh:**
```bash
docker compose run spark-app rm -rf /workspace/data/processed/*
docker compose run spark-app rm -rf /workspace/data/quarantine/*
```

---

## Assignment Requirements Checklist

- [x] 3 separate ETL pipelines using PySpark
- [x] Apache Hudi integration with proper configurations
- [x] Schema evolution support (Hudi configs)
- [x] Data cleaning (trim, normalize, type conversion)
- [x] Data quality checks with quarantine zone
- [x] Medallion architecture pattern (source/bronze/archive/gold)
- [x] Consumption layer with business metrics
- [x] YAML configuration file
- [x] Spark submit scripts with correct Hudi packages
- [x] Local filesystem storage (no S3 needed)
- [x] Recommendation output as CSV

---

## Notes

- I used Docker to make it easier for reviewers to run without environment setup
- The dataset has ~1 million records per file to test scalability
- Both clean and dirty CSV files are included to test data quality logic
- `ecomm_prod_fixed.yml` has extra config for incremental loads, but `ecomm_prod.yml` is sufficient for the assignment

---

**Submitted by:** Anik Das (2025EM1100026)
**Date:** November 2024
