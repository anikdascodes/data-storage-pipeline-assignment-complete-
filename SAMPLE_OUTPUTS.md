# Sample Outputs Documentation

**Student**: Anik Das (2025EM1100026)  
**Assignment**: Data Storage and Pipeline - Assignment #1

---

## Expected Output Structure

After running the complete pipeline, the following outputs will be generated:

### 1. Hudi Tables (Gold Layer)

#### Location: `/workspace/data/processed/`

```
processed/
├── seller_catalog_hudi/
│   ├── .hoodie/                    # Hudi metadata
│   ├── category=Electronics/       # Partition 1
│   ├── category=Footwear/          # Partition 2
│   ├── category=Apparel/           # Partition 3
│   └── ...
├── company_sales_hudi/
│   ├── .hoodie/                    # Hudi metadata
│   └── default/                    # Non-partitioned data
└── competitor_sales_hudi/
    ├── .hoodie/                    # Hudi metadata
    └── partition_col=default/      # Single partition
```

**Hudi Table Properties**:
- Format: Parquet files with Hudi metadata
- Table Type: COPY_ON_WRITE
- Operation: Upsert (incremental)
- Supports: Schema evolution, time travel, incremental queries

---

### 2. Recommendations CSV

#### Location: `/workspace/data/processed/recommendations_csv/`

**File Structure**:
```
recommendations_csv/
├── _SUCCESS
└── part-00000-*.csv              # Actual CSV file
```

**Sample Content** (first 10 rows):

```csv
seller_id,item_id,item_name,category,market_price,expected_units_sold,expected_revenue
S001,I10005,Samsung Galaxy S23,Electronics,899.99,125.50,112998.75
S001,I10012,Adidas Running Shoes,Footwear,79.99,98.25,7859.08
S001,I10023,H&M Cotton Shirt,Apparel,29.99,156.75,4700.93
S002,I10001,Apple iPhone 15 Pro,Electronics,999.99,200.00,199998.00
S002,I10008,Nike Air Max,Footwear,129.99,87.50,11374.13
S002,I10015,Zara Jacket,Apparel,89.99,65.00,5849.35
S003,I10003,Dell XPS 13 Laptop,Electronics,1299.99,45.00,58499.55
S003,I10019,Puma Sneakers,Footwear,69.99,112.00,7838.88
S003,I10025,Levi's Jeans,Apparel,59.99,89.00,5339.11
S004,I10007,Sony Headphones,Electronics,199.99,156.00,31198.44
```

**Column Descriptions**:
- `seller_id`: Unique seller identifier
- `item_id`: Unique item identifier
- `item_name`: Product name
- `category`: Product category
- `market_price`: Average price from competitor sales
- `expected_units_sold`: Estimated units per seller (total_units / num_sellers)
- `expected_revenue`: Potential revenue (expected_units * market_price)

---

### 3. Quarantine Records

#### Location: `/workspace/data/quarantine/`

```
quarantine/
├── seller_catalog/
│   └── *.parquet                  # Failed seller catalog records
├── company_sales/
│   └── *.parquet                  # Failed company sales records
└── competitor_sales/
    └── *.parquet                  # Failed competitor sales records
```

**Sample Quarantine Record** (Seller Catalog):

```
seller_id: ""
item_id: "I10005"
item_name: "Product Name"
category: "Electronics"
marketplace_price: 599.99
stock_qty: 10
dq_failure_reason: "seller_id_missing;"
```

**Sample Quarantine Record** (Company Sales):

```
item_id: "I10008"
units_sold: -10
revenue: 500.00
sale_date: "2024-11-01"
dq_failure_reason: "units_sold_negative;"
```

**Sample Quarantine Record** (Competitor Sales):

```
seller_id: "C001"
item_id: ""
units_sold: 100
revenue: 10000.00
marketplace_price: 100.00
sale_date: "2030-01-01"
dq_failure_reason: "item_id_missing;sale_date_invalid;"
```

---

## Data Quality Statistics

### Expected DQ Results (from dirty datasets):

**Seller Catalog**:
- Total records: ~2,000,000 (clean + dirty)
- Valid records: ~1,950,000 (97.5%)
- Quarantined: ~50,000 (2.5%)
- Common failures:
  - Missing seller_id: ~15,000
  - Missing item_id: ~12,000
  - Negative prices: ~8,000
  - Negative stock: ~10,000
  - Missing item_name: ~3,000
  - Missing category: ~2,000

**Company Sales**:
- Total records: ~2,000,000 (clean + dirty)
- Valid records: ~1,960,000 (98%)
- Quarantined: ~40,000 (2%)
- Common failures:
  - Missing item_id: ~18,000
  - Negative units_sold: ~8,000
  - Negative revenue: ~6,000
  - Invalid dates: ~8,000

**Competitor Sales**:
- Total records: ~2,000,000 (clean + dirty)
- Valid records: ~1,940,000 (97%)
- Quarantined: ~60,000 (3%)
- Common failures:
  - Missing seller_id: ~20,000
  - Missing item_id: ~15,000
  - Negative units_sold: ~10,000
  - Negative revenue: ~8,000
  - Negative prices: ~5,000
  - Invalid dates: ~2,000

---

## Performance Metrics

### Expected Runtime (on 8GB RAM, 4 CPU cores):

1. **Seller Catalog ETL**: 3-5 minutes
   - Read: 30 seconds
   - Clean & DQ: 1 minute
   - Hudi Write: 2-3 minutes

2. **Company Sales ETL**: 2-4 minutes
   - Read: 25 seconds
   - Clean & DQ: 45 seconds
   - Hudi Write: 1.5-2.5 minutes

3. **Competitor Sales ETL**: 3-5 minutes
   - Read: 35 seconds
   - Clean & DQ: 1 minute
   - Hudi Write: 2-3 minutes

4. **Consumption Layer**: 4-7 minutes
   - Read Hudi tables: 1 minute
   - Aggregations: 2-3 minutes
   - Recommendations: 1-2 minutes
   - CSV Write: 30 seconds

**Total Pipeline Runtime**: 12-21 minutes

---

## Verification Commands

### Check Hudi Tables

```bash
# Inside Docker container
ls -lh /workspace/data/processed/seller_catalog_hudi/
ls -lh /workspace/data/processed/company_sales_hudi/
ls -lh /workspace/data/processed/competitor_sales_hudi/
```

### View Recommendations

```bash
# Find the CSV file
find /workspace/data/processed/recommendations_csv/ -name "*.csv" -type f

# View first 20 lines
head -20 $(find /workspace/data/processed/recommendations_csv/ -name "*.csv" -type f | head -1)
```

### Check Quarantine Records

```bash
# Check quarantine directories
ls -lh /workspace/data/quarantine/seller_catalog/
ls -lh /workspace/data/quarantine/company_sales/
ls -lh /workspace/data/quarantine/competitor_sales/
```

### Count Records

```bash
# Using Spark shell (inside container)
spark-shell --packages org.apache.hudi:hudi-spark3.5-bundle_2.12:0.15.0

# In Spark shell:
val df = spark.read.format("hudi").load("/workspace/data/processed/seller_catalog_hudi/")
df.count()
```

---

## Notes

1. **Actual outputs will vary** based on the specific data in your input CSV files
2. **Quarantine counts** depend on data quality of dirty datasets
3. **Recommendations** will be different for each seller based on their current catalog
4. **Performance** may vary based on system resources and data size
5. **Hudi metadata** (.hoodie folders) contain commit history and table metadata

---

## Troubleshooting

**Issue**: No CSV file in recommendations folder  
**Solution**: Check Spark logs for errors in consumption layer

**Issue**: Empty Hudi tables  
**Solution**: Check if all records were quarantined (review DQ rules)

**Issue**: Large quarantine files  
**Solution**: Review dirty datasets and DQ failure reasons

---

**Note**: This document describes expected outputs. Actual execution screenshots and sample data should be included after running the pipeline.
