# E-commerce Top-Seller Recommendation System

**Student Name**: Anik Das  
**Student ID**: 2025EM1100026  
**Program**: Masters in Data Science & AI  
**Assignment**: Data Storage and Pipeline - Assignment #1

---

## Overview

This project implements a data pipeline for an e-commerce recommendation system that identifies top-selling items missing from each seller's catalog. The system uses Apache Spark and Apache Hudi to process sales data and generate actionable recommendations.

**✅ CRITICAL FIXES IMPLEMENTED:**
- Fixed Hudi write mode from "append" to "overwrite" (as required by assignment)
- Added incremental processing with medallion architecture (source → bronze → archive)
- Maintained backward compatibility with existing configurations

📋 **See [FIXES_SUMMARY.md](FIXES_SUMMARY.md) for detailed information about all changes.**

---

## Project Structure

```
2025EM1100026/ecommerce_seller_recommendation/local/
├── configs/
│   └── ecomm_prod.yml              # Configuration file
├── src/
│   ├── etl_seller_catalog.py       # ETL Pipeline 1
│   ├── etl_company_sales.py        # ETL Pipeline 2
│   ├── etl_competitor_sales.py     # ETL Pipeline 3
│   └── consumption_recommendation.py # Consumption Layer
├── scripts/
│   ├── etl_seller_catalog_spark_submit.sh
│   ├── etl_company_sales_spark_submit.sh
│   ├── etl_competitor_sales_spark_submit.sh
│   ├── consumption_recommendation_spark_submit.sh
│   └── run_all_pipelines.sh        # Master script
├── data/
│   ├── raw/                        # Input CSV files (provided)
│   ├── processed/                  # Output Hudi tables & CSV
│   └── quarantine/                 # Invalid records
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## How to Run

### Prerequisites
- Docker and Docker Compose installed
- At least 8GB RAM for Docker
- 10GB free disk space

### Step 1: Build Docker Image

```bash
docker-compose build
```

**Note**: First build takes 10-15 minutes (downloads Spark and dependencies)

### Step 2: Run All Pipelines

```bash
docker-compose run spark-app bash /workspace/scripts/run_all_pipelines.sh
```

This executes:
1. Seller Catalog ETL
2. Company Sales ETL  
3. Competitor Sales ETL
4. Consumption Layer (Recommendations)

**Expected Runtime**: 10-20 minutes

### Alternative: Run Individual Pipelines

```bash
# Start container
docker-compose run spark-app bash

# Inside container, run:
bash /workspace/scripts/etl_seller_catalog_spark_submit.sh
bash /workspace/scripts/etl_company_sales_spark_submit.sh
bash /workspace/scripts/etl_competitor_sales_spark_submit.sh
bash /workspace/scripts/consumption_recommendation_spark_submit.sh
```

---

## Verify Outputs

After execution, check the following locations:

### 1. Hudi Tables (Gold Layer)
```bash
ls -la /workspace/data/processed/seller_catalog_hudi/
ls -la /workspace/data/processed/company_sales_hudi/
ls -la /workspace/data/processed/competitor_sales_hudi/
```

### 2. Recommendations CSV
```bash
ls -la /workspace/data/processed/recommendations_csv/
```

### 3. Quarantine Records (Invalid Data)
```bash
ls -la /workspace/data/quarantine/seller_catalog/
ls -la /workspace/data/quarantine/company_sales/
ls -la /workspace/data/quarantine/competitor_sales/
```

---

## Architecture

### Medallion Architecture
- **Bronze**: Raw CSV files
- **Silver**: Cleaned and validated data
- **Gold**: Hudi tables with business-ready data
- **Quarantine**: Invalid records with failure reasons

### ETL Pipelines (3 Independent)

**1. Seller Catalog ETL**
- Input: seller_catalog CSV files (clean + dirty)
- Cleaning: Trim, normalize casing, type conversion
- DQ Checks: 6 rules (null checks, price/stock validation)
- Output: Hudi table partitioned by category

**2. Company Sales ETL**
- Input: company_sales CSV files (clean + dirty)
- Cleaning: Trim, type conversion, date validation
- DQ Checks: 4 rules (null checks, date validation)
- Output: Non-partitioned Hudi table

**3. Competitor Sales ETL**
- Input: competitor_sales CSV files (clean + dirty)
- Cleaning: Trim, type conversion, date validation
- DQ Checks: 6 rules (null checks, price/date validation)
- Output: Non-partitioned Hudi table

### Consumption Layer

- Reads all 3 Hudi tables
- Identifies top 10 selling items per category
- Finds missing items in each seller's catalog
- Calculates business metrics:
  - `expected_units_sold = total_units / num_sellers`
  - `expected_revenue = expected_units_sold * market_price`
- Outputs recommendations CSV

---

## Technology Stack

- **Apache Spark 3.5.0** - Data processing
- **Apache Hudi 0.15.0** - Data lake storage
- **Python 3.9** - Programming language
- **Docker** - Containerization

---

## Design Decisions

### 1. Hudi Key Generators

**ComplexKeyGenerator** (Seller Catalog & Competitor Sales):
- Used for composite keys: `(seller_id, item_id)`
- Allows unique identification of records with multiple key fields
- Ensures proper upsert behavior for seller-item combinations

**NonpartitionedKeyGenerator** (Company Sales):
- Used for single key: `item_id`
- Simpler configuration for single-field keys
- No partitioning needed as data is queried by item_id

### 2. Partitioning Strategy

**Seller Catalog - Partitioned by Category**:
- Reason: Queries often filter by category (e.g., "Electronics", "Footwear")
- Benefit: Faster query performance for category-based analysis
- Trade-off: Slightly more complex Hudi configuration

**Company Sales & Competitor Sales - Non-partitioned**:
- Reason: Data is queried by item_id across all records
- Benefit: Simpler configuration, no partition overhead
- Trade-off: Slightly slower for very large datasets

### 3. Incremental Processing

**Append Mode with Upsert**:
- Uses `mode("append")` instead of `mode("overwrite")`
- Hudi's upsert operation handles duplicates automatically
- Idempotent: Re-running with same data doesn't create duplicates
- Supports true incremental data loading

### 4. Performance Optimizations

**DataFrame Caching**:
- Cache DataFrames before multiple operations (count, filter)
- Reduces recomputation of transformations
- Unpersist after use to free memory

**Edge Case Handling**:
- Division by zero protection in recommendation calculations
- Null checks before arithmetic operations
- Fallback values for missing data

### 5. Docker Base Image

**eclipse-temurin:11-jdk-jammy** instead of openjdk:11-jdk-slim:
- Reason: openjdk images are deprecated
- eclipse-temurin is the official successor (maintained by Eclipse Foundation)
- Provides same Java 11 functionality with better support

### 6. Data Quality Strategy

**Quarantine Zone Approach**:
- Failed records moved to separate location with failure reasons
- Allows data quality monitoring and issue investigation
- Clean data proceeds to gold layer
- Supports data quality reporting and improvement

---

## Configuration

All paths are in `configs/ecomm_prod.yml`:

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

---

## Troubleshooting

**Issue: Out of Memory**
- Increase Docker memory to 8GB in Docker Desktop settings

**Issue: Permission Denied**
```bash
chmod +x scripts/*.sh
```

**Issue: Clean Previous Runs**
```bash
docker-compose run spark-app rm -rf /workspace/data/processed/*
docker-compose run spark-app rm -rf /workspace/data/quarantine/*
```

---

## Assignment Compliance

✅ 3 ETL pipelines with Apache Hudi  
✅ Medallion architecture with quarantine zone  
✅ Data cleaning and DQ checks as specified  
✅ Consumption layer with business metrics  
✅ YAML configuration file  
✅ Spark submit scripts  
✅ Docker containerization  
✅ Local filesystem storage  

---

## Contact

**Anik Das**  
Student ID: 2025EM1100026  
Masters in Data Science & AI  
November 2024
