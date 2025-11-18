# Assignment Review Guide

## Quick Start for Reviewers

### Prerequisites
- Docker and Docker Compose installed
- At least 8GB RAM allocated to Docker
- 10GB free disk space

### Step 1: Build and Run
```bash
# Clone/extract the assignment
cd data-storage-pipeline-assignment-complete-

# Build Docker image (takes 10-15 minutes first time)
docker compose build

# Run complete pipeline (takes 10-20 minutes)
docker compose run spark-app bash /workspace/scripts/run_all_pipelines.sh
```

### Step 2: Verify Outputs
```bash
# Check Hudi tables were created
docker compose run spark-app ls -la /workspace/data/processed/

# Check recommendations CSV
docker compose run spark-app ls -la /workspace/data/processed/recommendations_csv/

# Check quarantine records
docker compose run spark-app ls -la /workspace/data/quarantine/
```

### Expected Outputs
- `/workspace/data/processed/seller_catalog_hudi/` - Hudi table (partitioned by category)
- `/workspace/data/processed/company_sales_hudi/` - Hudi table (non-partitioned)
- `/workspace/data/processed/competitor_sales_hudi/` - Hudi table (non-partitioned)
- `/workspace/data/processed/recommendations_csv/seller_recommend_data.csv` - Final recommendations
- `/workspace/data/quarantine/*/` - Invalid records with failure reasons

## Critical Fixes Implemented

✅ **Fixed Hudi Write Mode**: Changed from "append" to "overwrite" (as required)
✅ **Added Incremental Processing**: Medallion architecture (source → bronze → archive)
✅ **Maintained Backward Compatibility**: Works with both old and new config formats

## Troubleshooting

**Out of Memory**: Increase Docker memory to 8GB in Docker Desktop settings
**Permission Issues**: Run `chmod +x scripts/*.sh`
**Clean Previous Runs**: 
```bash
docker compose run spark-app rm -rf /workspace/data/processed/*
docker compose run spark-app rm -rf /workspace/data/quarantine/*
```

## Assignment Compliance Checklist

- ✅ 3 ETL pipelines using Apache Hudi
- ✅ Medallion architecture with quarantine zone
- ✅ Data cleaning and quality checks
- ✅ Consumption layer with business metrics
- ✅ YAML configuration files
- ✅ Spark submit scripts
- ✅ Docker containerization
- ✅ Overwrite mode (as specified in assignment)
- ✅ Incremental processing pattern

## Files Overview

**Core ETL Files:**
- `src/etl_seller_catalog.py` - Processes seller catalog data
- `src/etl_company_sales.py` - Processes company sales data  
- `src/etl_competitor_sales.py` - Processes competitor sales data
- `src/consumption_recommendation.py` - Generates recommendations

**Configuration:**
- `configs/ecomm_prod.yml` - Original config (backward compatible)
- `configs/ecomm_prod_fixed.yml` - New config with incremental processing

**Scripts:**
- `scripts/run_all_pipelines.sh` - Master script to run everything
- `scripts/*_spark_submit.sh` - Individual pipeline scripts

**Documentation:**
- `README.md` - Complete setup and usage instructions
- `FIXES_SUMMARY.md` - Detailed explanation of all fixes implemented

## Contact
Student: Anik Das (2025EM1100026)
Program: Masters in Data Science & AI
