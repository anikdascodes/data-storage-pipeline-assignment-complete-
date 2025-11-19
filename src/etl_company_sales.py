"""
ETL Pipeline for Company Sales
- Reads company sales CSV files (clean + dirty)
- Applies data cleaning and DQ checks
- Quarantines bad records
- Writes valid records to Hudi table
"""

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
from utils import ensure_dir, resolve_medallion_paths
from metrics import PipelineMetrics

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


def validate_input_files(input_path: str) -> bool:
    """Validate that input path exists and contains readable CSV files"""
    if not os.path.exists(input_path):
        logger.error(f"Input path does not exist: {input_path}")
        return False

    # Check if it's a specific CSV file
    if input_path.endswith('.csv'):
        if not os.path.isfile(input_path):
            logger.error(f"Input file does not exist: {input_path}")
            return False
        if os.path.getsize(input_path) == 0:
            logger.error(f"Input file is empty: {input_path}")
            return False
        return True

    # Check if directory contains CSV files
    if os.path.isdir(input_path):
        csv_files = [f for f in os.listdir(input_path) if f.endswith('.csv')]
        if not csv_files:
            logger.error(f"No CSV files found in directory: {input_path}")
            return False
        # Check if any CSV files are readable
        for csv_file in csv_files:
            file_path = os.path.join(input_path, csv_file)
            if os.path.getsize(file_path) == 0:
                logger.warning(f"Empty CSV file found: {csv_file}")
        return True

    logger.error(f"Input path is neither a file nor directory: {input_path}")
    return False


def extract_new_files(source_path: str, bronze_path: str, archive_path: str) -> str:
    """
    Extract new CSV files from source landing folder
    Move to Bronze layer and archive with timestamp
    Implements medallion architecture incremental processing pattern
    """
    ensure_dir(bronze_path)
    ensure_dir(archive_path)
    
    files_processed = 0
    if not os.path.exists(source_path):
        logger.warning(f"Source path {source_path} does not exist yet")
        return bronze_path

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
    """Read company sales CSV files with schema"""
    schema = T.StructType([
        T.StructField("item_id", T.StringType(), True),
        T.StructField("units_sold", T.StringType(), True),
        T.StructField("revenue", T.StringType(), True),
        T.StructField("sale_date", T.StringType(), True)
    ])
    
    csv_path = input_path if input_path.endswith(".csv") else os.path.join(input_path.rstrip("/"), "*.csv")
    df = (
        spark.read
        .schema(schema)
        .option("header", True)
        .option("ignoreLeadingWhiteSpace", True)
        .option("ignoreTrailingWhiteSpace", True)
        .csv(csv_path)
    )
    
    logger.info(f"Loaded {df.count()} records from {input_path}")
    return df


def clean_data(df: DataFrame) -> DataFrame:
    """Apply data cleaning transformations"""
    cleaned_df = (
        df
        # Trim whitespace
        .withColumn("item_id", F.trim(F.col("item_id")))
        
        # Convert types
        .withColumn("units_sold",
                   F.when(F.col("units_sold").cast(T.IntegerType()).isNotNull(),
                         F.col("units_sold").cast(T.IntegerType()))
                   .otherwise(0))
        .withColumn("revenue",
                   F.when(F.col("revenue").cast(T.DoubleType()).isNotNull(),
                         F.col("revenue").cast(T.DoubleType()))
                   .otherwise(0.0))
        
        # Parse and standardize date
        .withColumn("sale_date",
                   F.when(F.to_date(F.col("sale_date"), "yyyy-MM-dd").isNotNull(),
                         F.to_date(F.col("sale_date"), "yyyy-MM-dd"))
                   .otherwise(None))
    )
    
    logger.info("Data cleaning completed")
    return cleaned_df


def apply_dq_checks(df: DataFrame) -> Tuple[DataFrame, DataFrame, int, int]:
    """Apply data quality checks and separate valid/invalid records"""
    
    # Cache the DataFrame as it will be used multiple times
    df.cache()
    
    # Add DQ failure reason column
    df_with_checks = (
        df
        .withColumn("dq_failure_reason", F.lit(""))
        .withColumn("dq_failure_reason",
                   F.when(F.col("item_id").isNull() | (F.col("item_id") == ""),
                         F.concat(F.col("dq_failure_reason"), F.lit("item_id_missing;")))
                   .otherwise(F.col("dq_failure_reason")))
        .withColumn("dq_failure_reason",
                   F.when(F.col("units_sold") < 0,
                         F.concat(F.col("dq_failure_reason"), F.lit("units_sold_negative;")))
                   .otherwise(F.col("dq_failure_reason")))
        .withColumn("dq_failure_reason",
                   F.when(F.col("revenue") < 0,
                         F.concat(F.col("dq_failure_reason"), F.lit("revenue_negative;")))
                   .otherwise(F.col("dq_failure_reason")))
        .withColumn("dq_failure_reason",
                   F.when((F.col("sale_date").isNull()) | (F.col("sale_date") > F.current_date()),
                         F.concat(F.col("dq_failure_reason"), F.lit("sale_date_invalid;")))
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
    
    return valid_df, invalid_df, valid_count, invalid_count


def remove_duplicates(df: DataFrame) -> DataFrame:
    """
    Remove exact duplicate rows (all columns identical)

    NOTE: For company sales data, we DO NOT deduplicate by item_id because:
    - Sales data is transactional (one item can sell multiple times)
    - Each row represents a distinct sale event
    - Aggregation should happen in the consumption layer, not ETL
    - Deduplicating by item_id would lose valuable transaction history

    We only remove rows where ALL columns are identical (likely data errors)
    """
    deduped_df = df.dropDuplicates()  # Remove exact duplicates only

    duplicates_removed = df.count() - deduped_df.count()
    logger.info(f"Removed {duplicates_removed} exact duplicate rows")
    logger.info(f"After deduplication: {deduped_df.count()} records")
    return deduped_df


def write_to_quarantine(invalid_df: DataFrame, invalid_count: int, quarantine_path: str):
    """Write invalid records to quarantine zone"""
    if invalid_count > 0:
        ensure_dir(quarantine_path)
        invalid_df.write.mode("overwrite").parquet(quarantine_path)
        logger.warning(f"Written {invalid_count} invalid records to {quarantine_path}")
    else:
        logger.info("No invalid records to quarantine")


def write_to_hudi(valid_df: DataFrame, hudi_output_path: str, record_count: int):
    """Write valid records to Hudi table with schema evolution support"""

    hudi_options = {
        "hoodie.table.name": "company_sales_hudi",
        "hoodie.datasource.write.recordkey.field": "item_id",
        "hoodie.datasource.write.partitionpath.field": "",
        "hoodie.datasource.write.precombine.field": "sale_date",
        "hoodie.datasource.write.operation": "upsert",
        "hoodie.datasource.write.table.type": "COPY_ON_WRITE",
        "hoodie.datasource.write.hive_style_partitioning": "true",
        "hoodie.datasource.write.keygenerator.class": "org.apache.hudi.keygen.NonpartitionedKeyGenerator",
        "hoodie.datasource.hive_sync.enable": "false",
        # Schema evolution configurations
        "hoodie.schema.on.read.enable": "true",
        "hoodie.datasource.write.reconcile.schema": "true",
        "hoodie.avro.schema.validate": "false"
    }
    
    # Use overwrite mode as required by assignment
    valid_df.write.format("hudi").options(**hudi_options).mode("overwrite").save(hudi_output_path)
    
    logger.info(f"Upserted {record_count} valid records to Hudi table: {hudi_output_path}")


def main(config_path: str):
    """Main ETL pipeline execution"""
    logger.info("Starting ETL pipeline for Company Sales")

    # Initialize metrics collection
    metrics = PipelineMetrics("ETL_CompanySales")

    # Load configuration
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Support both old and new config formats for backward compatibility
    company_config = config['company_sales']
    paths = resolve_medallion_paths('company_sales', company_config)
    source_path = paths['source']
    bronze_path = paths['bronze']
    archive_path = paths['archive']
    hudi_output_path = paths['hudi']
    quarantine_path = paths['quarantine']
    
    # Initialize Spark
    spark = get_spark_session("ETL_CompanySales")
    
    try:
        # Step 1: Extract new files (incremental processing)
        if source_path != bronze_path:
            bronze_path = extract_new_files(source_path, bronze_path, archive_path)

        # Step 2: Validate input files
        if not validate_input_files(bronze_path):
            raise ValueError(f"Input validation failed for path: {bronze_path}")

        # Step 3: ETL Pipeline
        df = read_data(spark, bronze_path)
        input_count = df.count()
        metrics.set_input_count(input_count)

        cleaned_df = clean_data(df)
        valid_df, invalid_df, valid_count, invalid_count = apply_dq_checks(cleaned_df)

        metrics.set_valid_count(valid_count)
        metrics.set_invalid_count(invalid_count)

        # Step 3: Write invalid records to quarantine
        write_to_quarantine(invalid_df, invalid_count, quarantine_path)
        invalid_df.unpersist()

        # Step 4: Remove exact duplicate rows and write to Hudi
        # NOTE: We only remove exact duplicates (all columns identical)
        # We do NOT deduplicate by item_id because sales data is transactional:
        # - Same item can sell multiple times (different dates/quantities)
        # - Aggregation happens in consumption layer, not here
        if valid_count > 0:
            deduped_df = remove_duplicates(valid_df)
            output_count = deduped_df.count()
            metrics.set_duplicate_count(valid_count, output_count)
            metrics.set_output_count(output_count)

            write_to_hudi(deduped_df, hudi_output_path, output_count)
            valid_df.unpersist()
        else:
            logger.warning("No valid records to write to Hudi")
            metrics.set_output_count(0)
            valid_df.unpersist()

        # Finalize metrics
        metrics.finalize("SUCCESS")
        metrics.print_summary()
        metrics.save_to_file()

        logger.info("ETL pipeline for Company Sales completed successfully")

    except Exception as e:
        error_msg = f"ETL pipeline failed: {str(e)}"
        metrics.add_error(error_msg)
        metrics.finalize("FAILED")
        metrics.print_summary()
        metrics.save_to_file()
        logger.error(error_msg)
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETL Pipeline for Company Sales")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    args = parser.parse_args()
    main(args.config)
