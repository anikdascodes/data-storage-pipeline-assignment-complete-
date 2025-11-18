"""
ETL Pipeline for Competitor Sales (FIXED VERSION)
- Supports incremental processing (source → bronze → archive)
- Applies data cleaning and DQ checks
- Quarantines bad records
- Writes valid records to Hudi table with OVERWRITE mode
"""

import os
import shutil
import argparse
import yaml
import logging
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
    """Extract new CSV files from source → bronze → archive"""
    os.makedirs(bronze_path, exist_ok=True)
    os.makedirs(archive_path, exist_ok=True)

    if not os.path.exists(source_path):
        logger.warning(f"Source path does not exist: {source_path}")
        return bronze_path

    files_processed = 0
    for file in os.listdir(source_path):
        if file.endswith(".csv"):
            src_file = os.path.join(source_path, file)
            dest_file = os.path.join(bronze_path, file)

            # Move to bronze
            shutil.move(src_file, dest_file)
            logger.info(f"Moved file {file} → Bronze layer")

            # Archive with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_file = f"{os.path.splitext(file)[0]}_{timestamp}.csv"
            archive_full_path = os.path.join(archive_path, archive_file)
            shutil.copy(dest_file, archive_full_path)
            logger.info(f"Archived {file} → {archive_full_path}")

            files_processed += 1

    logger.info(f"Processed {files_processed} files from source to bronze")
    return bronze_path


def read_data(spark: SparkSession, input_path: str) -> DataFrame:
    """Read competitor sales CSV files with schema"""
    schema = T.StructType([
        T.StructField("seller_id", T.StringType(), True),
        T.StructField("item_id", T.StringType(), True),
        T.StructField("units_sold", T.StringType(), True),
        T.StructField("revenue", T.StringType(), True),
        T.StructField("marketplace_price", T.StringType(), True),
        T.StructField("sale_date", T.StringType(), True)
    ])

    df = (
        spark.read
        .schema(schema)
        .option("header", True)
        .option("ignoreLeadingWhiteSpace", True)
        .option("ignoreTrailingWhiteSpace", True)
        .csv(f"{input_path}/*.csv")
    )

    record_count = df.count()
    logger.info(f"Loaded {record_count} records from {input_path}")

    if record_count == 0:
        logger.warning("No records found in input path")

    return df


def clean_data(df: DataFrame) -> DataFrame:
    """Apply data cleaning transformations"""
    cleaned_df = (
        df
        # Trim whitespace
        .withColumn("seller_id", F.trim(F.col("seller_id")))
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
        .withColumn("marketplace_price",
                   F.when(F.col("marketplace_price").cast(T.DoubleType()).isNotNull(),
                         F.col("marketplace_price").cast(T.DoubleType()))
                   .otherwise(0.0))

        # Parse and standardize date
        .withColumn("sale_date",
                   F.when(F.to_date(F.col("sale_date"), "yyyy-MM-dd").isNotNull(),
                         F.to_date(F.col("sale_date"), "yyyy-MM-dd"))
                   .otherwise(None))
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
                   F.when(F.col("item_id").isNull() | (F.col("item_id") == ""),
                         F.concat(F.col("dq_failure_reason"), F.lit("item_id_missing;")))
                   .otherwise(F.col("dq_failure_reason")))
        .withColumn("dq_failure_reason",
                   F.when(F.col("seller_id").isNull() | (F.col("seller_id") == ""),
                         F.concat(F.col("dq_failure_reason"), F.lit("seller_id_missing;")))
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
                   F.when(F.col("marketplace_price") < 0,
                         F.concat(F.col("dq_failure_reason"), F.lit("marketplace_price_negative;")))
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

    return valid_df, invalid_df


def remove_duplicates(df: DataFrame) -> DataFrame:
    """Remove duplicates based on composite key (seller_id, item_id)"""
    # Keep the first occurrence based on sale_date (most recent)
    deduped_df = (
        df
        .orderBy(F.col("sale_date").desc())
        .dropDuplicates(["seller_id", "item_id"])
    )

    logger.info(f"After deduplication: {deduped_df.count()} records")
    return deduped_df


def write_to_quarantine(invalid_df: DataFrame, quarantine_path: str):
    """Write invalid records to quarantine zone"""
    if invalid_df.count() > 0:
        invalid_df.write.mode("overwrite").parquet(quarantine_path)
        logger.warning(f"Written {invalid_df.count()} invalid records to {quarantine_path}")
    else:
        logger.info("No invalid records to quarantine")


def write_to_hudi(valid_df: DataFrame, hudi_output_path: str):
    """
    Write valid records to Hudi table
    FIXED: Using mode("overwrite") as per assignment requirement
    """

    # Add a constant partition column for ComplexKeyGenerator
    valid_df = valid_df.withColumn("partition_col", F.lit("default"))

    hudi_options = {
        "hoodie.table.name": "competitor_sales_hudi",
        "hoodie.datasource.write.recordkey.field": "seller_id,item_id",
        "hoodie.datasource.write.partitionpath.field": "partition_col",
        "hoodie.datasource.write.precombine.field": "sale_date",
        "hoodie.datasource.write.operation": "upsert",
        "hoodie.datasource.write.table.type": "COPY_ON_WRITE",
        "hoodie.datasource.write.hive_style_partitioning": "true",
        "hoodie.datasource.write.keygenerator.class": "org.apache.hudi.keygen.ComplexKeyGenerator",
        "hoodie.datasource.hive_sync.enable": "false"
    }

    # FIXED: Use overwrite mode as per assignment requirement
    valid_df.write.format("hudi").options(**hudi_options).mode("overwrite").save(hudi_output_path)

    logger.info(f"Written {valid_df.count()} valid records to Hudi table: {hudi_output_path}")


def main(config_path: str):
    """Main ETL pipeline execution"""
    logger.info("Starting ETL pipeline for Competitor Sales (FIXED VERSION)")

    # Load configuration
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Support both old and new config formats
    if 'source_path' in config['competitor_sales']:
        source_path = config['competitor_sales']['source_path']
        bronze_path = config['competitor_sales']['bronze_path']
        archive_path = config['competitor_sales']['archive_path']
    else:
        bronze_path = config['competitor_sales']['input_path']
        source_path = None
        archive_path = None

    hudi_output_path = config['competitor_sales']['hudi_output_path']
    quarantine_path = config['competitor_sales']['quarantine_path']

    # Initialize Spark
    spark = get_spark_session("ETL_CompetitorSales")

    try:
        # STEP 1: Extract
        if source_path:
            logger.info("Step 1: Extract - Moving files from source to bronze")
            bronze_path = extract_new_files(source_path, bronze_path, archive_path)
        else:
            logger.info("Step 1: Extract - Skipped (using bronze path directly)")

        # STEP 2: Transform
        logger.info("Step 2: Transform - Reading, cleaning, validating")
        df = read_data(spark, bronze_path)

        if df.rdd.isEmpty():
            logger.warning("No data to process. Exiting.")
            return

        cleaned_df = clean_data(df)
        valid_df, invalid_df = apply_dq_checks(cleaned_df)

        # STEP 3: Load
        logger.info("Step 3: Load - Writing to quarantine and gold layer")

        # Write invalid records to quarantine
        write_to_quarantine(invalid_df, quarantine_path)

        # Remove duplicates and write to Hudi
        if valid_df.count() > 0:
            deduped_df = remove_duplicates(valid_df)
            write_to_hudi(deduped_df, hudi_output_path)
        else:
            logger.warning("No valid records to write to Hudi")

        logger.info("ETL pipeline for Competitor Sales completed successfully")

    except Exception as e:
        logger.error(f"ETL pipeline failed: {str(e)}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETL Pipeline for Competitor Sales (FIXED)")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    args = parser.parse_args()
    main(args.config)
