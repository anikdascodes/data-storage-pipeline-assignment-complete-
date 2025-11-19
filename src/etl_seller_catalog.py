"""
ETL Pipeline for Seller Catalog
- Reads seller catalog CSV files (clean + dirty)
- Applies data cleaning and DQ checks
- Quarantines bad records
- Writes valid records to Hudi table
"""

import sys
import argparse
import yaml
import logging
import os
import shutil
from datetime import datetime
from typing import Tuple
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_spark_session(app_name: str) -> SparkSession:
    """Initialize Spark session with Hudi configurations"""
    spark = (
        SparkSession.builder
        .appName(app_name)
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def extract_new_files(source_path: str, bronze_path: str, archive_path: str) -> str:
    """
    Extract new CSV files from source landing folder
    Move to Bronze layer and archive with timestamp
    Implements medallion architecture incremental processing pattern
    """
    os.makedirs(bronze_path, exist_ok=True)
    os.makedirs(archive_path, exist_ok=True)
    
    files_processed = 0
    for file in os.listdir(source_path):
        if file.endswith(".csv"):
            src_file = os.path.join(source_path, file)
            dest_file = os.path.join(bronze_path, file)
            
            # Step 1: Move to bronze layer
            shutil.move(src_file, dest_file)
            logger.info(f"Moved file {file} → Bronze layer")
            
            # Step 2: Archive with timestamp for audit trail
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_file = f"{os.path.splitext(file)[0]}_{timestamp}.csv"
            archive_full_path = os.path.join(archive_path, archive_file)
            shutil.copy(dest_file, archive_full_path)
            logger.info(f"Archived {file} → {archive_full_path}")
            
            files_processed += 1
    
    logger.info(f"Processed {files_processed} new files from source to bronze")
    return bronze_path


def read_data(spark: SparkSession, input_path: str) -> DataFrame:
    """Read seller catalog CSV files with schema"""
    schema = T.StructType([
        T.StructField("seller_id", T.StringType(), True),
        T.StructField("item_id", T.StringType(), True),
        T.StructField("item_name", T.StringType(), True),
        T.StructField("category", T.StringType(), True),
        T.StructField("marketplace_price", T.StringType(), True),
        T.StructField("stock_qty", T.StringType(), True)
    ])
    
    df = (
        spark.read
        .schema(schema)
        .option("header", True)
        .option("ignoreLeadingWhiteSpace", True)
        .option("ignoreTrailingWhiteSpace", True)
        .csv(f"{input_path}/*.csv")
    )
    
    logger.info(f"Loaded {df.count()} records from {input_path}")
    return df


def clean_data(df: DataFrame) -> DataFrame:
    """Apply data cleaning transformations"""
    cleaned_df = (
        df
        # Trim whitespace from string columns
        .withColumn("seller_id", F.trim(F.col("seller_id")))
        .withColumn("item_id", F.trim(F.col("item_id")))
        .withColumn("item_name", F.trim(F.col("item_name")))
        .withColumn("category", F.trim(F.col("category")))
        
        # Normalize casing
        .withColumn("item_name", F.initcap(F.col("item_name")))  # Title Case
        .withColumn("category", F.initcap(F.col("category")))  # Standardized
        
        # Convert types
        .withColumn("marketplace_price", 
                   F.when(F.col("marketplace_price").cast(T.DoubleType()).isNotNull(),
                         F.col("marketplace_price").cast(T.DoubleType()))
                   .otherwise(None))
        .withColumn("stock_qty",
                   F.when(F.col("stock_qty").cast(T.IntegerType()).isNotNull(),
                         F.col("stock_qty").cast(T.IntegerType()))
                   .otherwise(0))
    )
    
    logger.info("Data cleaning completed")
    return cleaned_df


def apply_dq_checks(df: DataFrame) -> Tuple[DataFrame, DataFrame]:
    """Apply data quality checks and separate valid/invalid records"""
    
    # Cache the DataFrame as it will be used multiple times
    df.cache()
    
    # Add DQ failure reason column
    df_with_checks = (
        df
        .withColumn("dq_failure_reason", F.lit(""))
        .withColumn("dq_failure_reason",
                   F.when(F.col("seller_id").isNull() | (F.col("seller_id") == ""),
                         F.concat(F.col("dq_failure_reason"), F.lit("seller_id_missing;")))
                   .otherwise(F.col("dq_failure_reason")))
        .withColumn("dq_failure_reason",
                   F.when(F.col("item_id").isNull() | (F.col("item_id") == ""),
                         F.concat(F.col("dq_failure_reason"), F.lit("item_id_missing;")))
                   .otherwise(F.col("dq_failure_reason")))
        .withColumn("dq_failure_reason",
                   F.when(F.col("item_name").isNull() | (F.col("item_name") == ""),
                         F.concat(F.col("dq_failure_reason"), F.lit("item_name_missing;")))
                   .otherwise(F.col("dq_failure_reason")))
        .withColumn("dq_failure_reason",
                   F.when(F.col("category").isNull() | (F.col("category") == ""),
                         F.concat(F.col("dq_failure_reason"), F.lit("category_missing;")))
                   .otherwise(F.col("dq_failure_reason")))
        .withColumn("dq_failure_reason",
                   F.when((F.col("marketplace_price").isNull()) | (F.col("marketplace_price") < 0),
                         F.concat(F.col("dq_failure_reason"), F.lit("price_invalid;")))
                   .otherwise(F.col("dq_failure_reason")))
        .withColumn("dq_failure_reason",
                   F.when(F.col("stock_qty") < 0,
                         F.concat(F.col("dq_failure_reason"), F.lit("stock_qty_negative;")))
                   .otherwise(F.col("dq_failure_reason")))
    )
    
    # Separate valid and invalid records
    valid_df = df_with_checks.filter(F.col("dq_failure_reason") == "").drop("dq_failure_reason")
    invalid_df = df_with_checks.filter(F.col("dq_failure_reason") != "")
    
    # Cache for multiple counts (performance optimization)
    valid_df.cache()
    invalid_df.cache()
    
    valid_count = valid_df.count()
    invalid_count = invalid_df.count()
    
    logger.info(f"Valid records: {valid_count} | Invalid records: {invalid_count}")
    
    # Unpersist the original cached DataFrame
    df.unpersist()
    
    return valid_df, invalid_df


def remove_duplicates(df: DataFrame) -> DataFrame:
    """Remove duplicates based on composite key (seller_id, item_id)"""
    # Keep the first occurrence based on marketplace_price (higher price preferred)
    deduped_df = (
        df
        .orderBy(F.col("marketplace_price").desc())
        .dropDuplicates(["seller_id", "item_id"])
    )
    
    logger.info(f"After deduplication: {deduped_df.count()} records")
    return deduped_df


def write_to_quarantine(invalid_df: DataFrame, quarantine_path: str):
    """Write invalid records to quarantine zone"""
    # Use cached count to avoid recomputation
    if invalid_df.rdd.isEmpty() == False:
        invalid_df.write.mode("overwrite").parquet(quarantine_path)
        logger.warning(f"Written {invalid_df.count()} invalid records to {quarantine_path}")
    else:
        logger.info("No invalid records to quarantine")


def write_to_hudi(valid_df: DataFrame, hudi_output_path: str):
    """Write valid records to Hudi table with schema evolution support"""

    hudi_options = {
        "hoodie.table.name": "seller_catalog_hudi",
        "hoodie.datasource.write.recordkey.field": "seller_id,item_id",
        "hoodie.datasource.write.partitionpath.field": "category",
        "hoodie.datasource.write.precombine.field": "marketplace_price",
        "hoodie.datasource.write.operation": "upsert",
        "hoodie.datasource.write.table.type": "COPY_ON_WRITE",
        "hoodie.datasource.write.hive_style_partitioning": "true",
        "hoodie.datasource.write.keygenerator.class": "org.apache.hudi.keygen.ComplexKeyGenerator",
        "hoodie.datasource.hive_sync.enable": "false",
        # Schema evolution configurations
        "hoodie.schema.on.read.enable": "true",
        "hoodie.datasource.write.reconcile.schema": "true",
        "hoodie.avro.schema.validate": "false"
    }
    
    # Use overwrite mode as required by assignment
    valid_df.write.format("hudi").options(**hudi_options).mode("overwrite").save(hudi_output_path)
    
    logger.info(f"Upserted {valid_df.count()} valid records to Hudi table: {hudi_output_path}")


def main(config_path: str):
    """Main ETL pipeline execution"""
    logger.info("Starting ETL pipeline for Seller Catalog")
    
    # Load configuration
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Support both old and new config formats for backward compatibility
    seller_config = config['seller_catalog']
    
    # New format (recommended): source_path, bronze_path, archive_path
    if 'source_path' in seller_config:
        source_path = seller_config['source_path']
        bronze_path = seller_config['bronze_path']
        archive_path = seller_config['archive_path']
    else:
        # Old format fallback: use input_path as bronze_path
        bronze_path = seller_config['input_path']
        source_path = bronze_path  # No incremental processing in old format
        archive_path = bronze_path.replace('/raw/', '/archive/')
    
    hudi_output_path = seller_config['hudi_output_path']
    quarantine_path = seller_config['quarantine_path']
    
    # Initialize Spark
    spark = get_spark_session("ETL_SellerCatalog")
    
    try:
        # Step 1: Extract new files (incremental processing)
        if source_path != bronze_path:
            bronze_path = extract_new_files(source_path, bronze_path, archive_path)
        
        # Step 2: ETL Pipeline
        df = read_data(spark, bronze_path)
        cleaned_df = clean_data(df)
        valid_df, invalid_df = apply_dq_checks(cleaned_df)
        
        # Step 3: Write invalid records to quarantine
        write_to_quarantine(invalid_df, quarantine_path)
        
        # Step 4: Remove duplicates and write to Hudi
        if valid_df.rdd.isEmpty() == False:
            deduped_df = remove_duplicates(valid_df)
            write_to_hudi(deduped_df, hudi_output_path)
            # Unpersist cached DataFrames
            valid_df.unpersist()
        else:
            logger.warning("No valid records to write to Hudi")
            valid_df.unpersist()
        
        logger.info("ETL pipeline for Seller Catalog completed successfully")
        
    except Exception as e:
        logger.error(f"ETL pipeline failed: {str(e)}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETL Pipeline for Seller Catalog")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    args = parser.parse_args()
    main(args.config)
