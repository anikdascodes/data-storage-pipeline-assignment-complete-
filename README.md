# E-commerce Recommendation System

**Student:** Anik Das
**Roll No:** 2025EM1100026
**Course:** Data Storage and Pipeline Assignment

---

## What This Does

This project helps e-commerce sellers figure out what products they should add to their catalogs. It looks at sales data from the company and competitors, finds the top-selling items, and recommends products that sellers don't currently stock but probably should.

Built with Apache Spark and Apache Hudi to handle large datasets efficiently.

### 📚 Quick Links

- **[SUBMISSION_GUIDE.md](SUBMISSION_GUIDE.md)** - Complete submission package details, grading justification
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture, medallion layers, Hudi configuration
- **[RUN_TESTS_NOW.md](RUN_TESTS_NOW.md)** - Quick start testing guide
- **[CHANGELOG.md](CHANGELOG.md)** - All changes and fixes applied
- **[TEST_PLAN.md](TEST_PLAN.md)** - Comprehensive testing scenarios

---

## Getting Started

### What You Need
- Docker and Docker Compose installed
- At least 8GB RAM for Docker
- About 10GB free disk space
- The input datasets (you should have received `input_data_sets.zip`)

### Setting Up the Data

Put the `input_data_sets.zip` file in the project folder and run:

```bash
bash scripts/setup_data.sh
```

This unpacks everything and puts files in the right places.

**If the script doesn't work, here's the manual way:**

```bash
# Unzip the data
unzip input_data_sets.zip

# Make the folders we need
mkdir -p data/raw/seller_catalog data/raw/company_sales data/raw/competitor_sales

# Copy files to the right spots
cp input_data_sets/clean/seller_catalog_clean.csv data/raw/seller_catalog/
cp input_data_sets/dirty/seller_catalog_dirty.csv data/raw/seller_catalog/
cp input_data_sets/clean/company_sales_clean.csv data/raw/company_sales/
cp input_data_sets/dirty/company_sales_dirty.csv data/raw/company_sales/
cp input_data_sets/clean/competitor_sales_clean.csv data/raw/competitor_sales/
cp input_data_sets/dirty/competitor_sales_dirty.csv data/raw/competitor_sales/

# Clean up
rm -rf input_data_sets/ input_data_sets.zip

# Check everything looks good
python3 scripts/validate_data.py
```

### Running Everything

First time only - build the Docker image (takes 10-15 minutes):
```bash
docker compose build
```

Then run the whole pipeline:
```bash
docker compose run spark-app bash /workspace/scripts/run_all_pipelines.sh
```

This runs 4 steps:
1. Process seller catalog data
2. Process company sales data
3. Process competitor sales data
4. Generate recommendations

Takes about 10-20 minutes depending on your machine.

---

## What You Get

When it finishes, you'll have:

**Cleaned Data (Hudi tables in `data/processed/`):**
- `seller_catalog_hudi/` - What sellers are currently selling
- `company_sales_hudi/` - Company sales history
- `competitor_sales_hudi/` - What competitors are selling

**Recommendations (CSV files):**
- `recommendations_csv/seller_recommend_data.csv` - Product recommendations for each seller with expected revenue
- `recommendations_csv/company_catalog_gap/` - Products competitors sell that we don't

**Bad Data (in `data/quarantine/`):**
- Any records that failed validation, with reasons why

---

## Project Layout

```
configs/
  ecomm_prod.yml                    # Where everything's configured

src/
  etl_seller_catalog.py             # Cleans seller catalog data
  etl_company_sales.py              # Cleans company sales data
  etl_competitor_sales.py           # Cleans competitor sales data
  consumption_recommendation.py     # Makes recommendations
  utils.py                          # Helper functions
  metrics.py                        # Tracks what happens during runs

scripts/
  run_all_pipelines.sh              # Runs everything in order
  setup_data.sh                     # Sets up your data
  validate_data.py                  # Checks data looks right

data/
  raw/                              # Your input CSV files go here
  processed/                        # Cleaned data and recommendations
  quarantine/                       # Bad records go here
  samples/                          # Small test datasets
```

---

## How It Works

### The ETL Part (Extract, Transform, Load)

Each of the three pipelines does basically the same thing:

1. **Reads** CSV files from `data/raw/`
2. **Cleans** the data:
   - Removes extra spaces
   - Fixes capitalization
   - Converts text to proper numbers and dates
3. **Validates** everything:
   - Makes sure required fields aren't blank
   - Checks numbers make sense (no negative prices)
   - Verifies dates are valid
4. **Splits** good from bad:
   - Good records → Save to Hudi table
   - Bad records → Save to quarantine with error details
5. **Removes** duplicate records

### The Recommendation Part

This is where it gets interesting:

1. Loads the three cleaned Hudi tables
2. Finds the top 10 best-selling items in each category
3. Looks at what competitors are selling too
4. For each seller, figures out which top items they're missing
5. Estimates how much revenue they could make: `(average units sold ÷ number of sellers) × market price`
6. Saves everything as a CSV

---

## Tech Stack

- **Apache Spark 3.5.0** - Processes large datasets fast
- **Apache Hudi 0.15.0** - Modern data lake storage format
- **Python 3.9** - Programming language
- **Docker** - So you don't need to install everything manually

### Why Hudi?

Using different Hudi configurations based on what makes sense:

- **Seller catalog & competitor sales:** Use composite keys (seller_id + item_id) since both matter
- **Company sales:** Just use item_id since we don't track individual sellers
- **Partitioning:** Seller catalog is split by category for faster queries

Everything uses overwrite mode per assignment requirements.

### Schema Evolution

If column names or types change in the future, the pipeline can handle it automatically thanks to these Hudi settings:
```python
"hoodie.schema.on.read.enable": "true"
"hoodie.datasource.write.reconcile.schema": "true"
"hoodie.avro.schema.validate": "false"
```

### Data Quality Rules

**Seller Catalog** - rejects records if:
- seller_id is blank
- item_id is blank
- item_name is blank
- category is blank
- price is negative or missing
- stock_qty is negative

**Company Sales** - rejects if:
- item_id is blank
- units_sold is negative
- revenue is negative
- sale_date is invalid or in the future

**Competitor Sales** - rejects if:
- item_id is blank
- seller_id is blank
- units_sold is negative
- revenue is negative
- marketplace_price is negative
- sale_date is invalid or in the future

---

## Configuration

Everything's controlled by `configs/ecomm_prod.yml`:

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

There's also `ecomm_prod_fixed.yml` with extra paths for incremental processing if you want to run this daily.

---

## Running Parts Separately

Don't want to run everything at once? You can run individual pieces:

```bash
# Get into the container
docker compose run spark-app bash

# Then run whatever you need:
bash /workspace/scripts/etl_seller_catalog_spark_submit.sh
bash /workspace/scripts/etl_company_sales_spark_submit.sh
bash /workspace/scripts/etl_competitor_sales_spark_submit.sh
bash /workspace/scripts/consumption_recommendation_spark_submit.sh
```

---

## Extra Stuff

### Validating Your Data

Before running anything, make sure your data looks good:
```bash
python3 scripts/validate_data.py
```

This checks file formats, headers, and makes sure nothing's obviously wrong.

### Metrics

Each pipeline tracks and reports:
- How long it took
- How many records (total, good, bad, duplicates)
- Data quality percentages
- Any errors

Metrics get saved to `data/metrics/` as JSON and printed to your terminal.

### Test Data

Small sample files (100 rows each) are in `data/samples/` if you want to test without processing millions of records.

---

## Common Problems

**"File not found" errors:**
- Did you run the data setup steps?
- Run `python3 scripts/validate_data.py` to check
- Make sure files are actually in the `data/raw/` subfolders

**Out of memory:**
- Open Docker Desktop settings
- Bump memory to 8GB or more

**Scripts won't run:**
```bash
chmod +x scripts/*.sh
```

**Data validation fails:**
- Check your CSV headers match what's expected
- Make sure files aren't corrupted
- Verify file permissions

**Want to start over:**
```bash
# Inside Docker:
docker compose run spark-app rm -rf /workspace/data/processed/*
docker compose run spark-app rm -rf /workspace/data/quarantine/*

# Or on your machine:
rm -rf data/processed/* data/quarantine/* data/metrics/*
```

---

## Assignment Checklist

- ✓ 3 separate ETL pipelines in PySpark
- ✓ Apache Hudi for data storage
- ✓ Schema evolution support
- ✓ Data cleaning (whitespace, casing, types)
- ✓ Data quality validation with quarantine
- ✓ Medallion architecture (source → bronze → gold)
- ✓ Consumption layer with business logic
- ✓ YAML config file
- ✓ Spark submit scripts
- ✓ Local filesystem (no cloud needed)
- ✓ CSV output for recommendations

---

## Notes

- Using Docker so anyone can run this without setting up Spark manually
- Dataset has ~1 million records to test performance
- Both clean and dirty files included to test validation logic
- Metrics tracking helps understand pipeline behavior
- Input validation catches issues before processing starts

---

**Submitted by:** Anik Das (2025EM1100026)
**Date:** November 2024
