# E-commerce Top-Seller Recommendation System

**Student Name**: Anik Das  
**Student ID**: 2025EM1100026  
**Program**: Masters in Data Science & AI  
**Assignment**: Data Storage and Pipeline - Assignment #1

---

## Overview

This project implements a data pipeline for an e-commerce recommendation system that identifies top-selling items missing from each seller's catalog. The system uses Apache Spark and Apache Hudi to process sales data and generate actionable recommendations.

## Key Features

- **Apache Hudi Integration**: Uses overwrite mode for data consistency as required
- **Medallion Architecture**: Implements incremental processing with source → bronze → archive pattern
- **Data Quality**: Comprehensive validation with quarantine zone for invalid records
- **Scalable Design**: Containerized with Docker for easy deployment

## Implementation Notes

This implementation follows the assignment requirements with:
- **Overwrite Mode**: All ETL pipelines use `.mode("overwrite")` for Hudi tables
- **Incremental Processing**: Added `extract_new_files()` function for medallion architecture
- **Backward Compatibility**: Supports both legacy and new configuration formats

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
docker compose build
```

*Note: First build takes 10-15 minutes to download Spark and dependencies*

### Step 2: Run Complete Pipeline

```bash
docker compose run spark-app bash /workspace/scripts/run_all_pipelines.sh
```

This will run all four components:
1. Seller Catalog ETL
2. Company Sales ETL  
3. Competitor Sales ETL
4. Recommendation Generation

*Expected runtime: 10-20 minutes depending on system*

### Alternative: Run Individual Pipelines

```bash
# Start container
docker compose run spark-app bash

# Inside container, run:
bash /workspace/scripts/etl_seller_catalog_spark_submit.sh
bash /workspace/scripts/etl_company_sales_spark_submit.sh
bash /workspace/scripts/etl_competitor_sales_spark_submit.sh
bash /workspace/scripts/consumption_recommendation_spark_submit.sh
```

---

## Expected Outputs

After successful execution, you should see:

**Hudi Tables (Gold Layer):**
- `/workspace/data/processed/seller_catalog_hudi/` - Seller catalog data
- `/workspace/data/processed/company_sales_hudi/` - Company sales data  
- `/workspace/data/processed/competitor_sales_hudi/` - Competitor sales data

**Final Recommendations:**
- `/workspace/data/processed/recommendations_csv/seller_recommend_data.csv`

**Data Quality Reports:**
- `/workspace/data/quarantine/*/` - Invalid records with failure reasons

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

### Key Design Decisions

**Hudi Configuration**:
- Seller Catalog & Competitor Sales use ComplexKeyGenerator for composite keys (seller_id, item_id)
- Company Sales uses NonpartitionedKeyGenerator for single key (item_id)
- Seller Catalog partitioned by category for better query performance

**Data Processing**:
- Overwrite mode ensures data consistency as required by assignment
- Medallion architecture with source → bronze → archive for incremental processing
- Quarantine zone separates invalid records for data quality monitoring

**Performance**:
- DataFrame caching for operations requiring multiple passes
- Proper null handling and edge case protection
- Docker containerization with eclipse-temurin Java base image

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

**Out of Memory Errors:**
- Increase Docker memory allocation to 8GB in Docker Desktop settings

**Permission Issues:**
```bash
chmod +x scripts/*.sh
```

**Clean Previous Runs:**
```bash
docker compose run spark-app rm -rf /workspace/data/processed/*
docker compose run spark-app rm -rf /workspace/data/quarantine/*
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
