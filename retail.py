"""

Retail Ingestion Pipeline (Production Style)

============================================

- Extract CSV files from source landing folder

- Move to Bronze layer

- Clean, validate (DQ), transform

- Load into Gold layer (Hudi table) incrementally

- Archive processed source files

"""



import os

import shutil

import logging

from datetime import datetime

from pyspark.sql import SparkSession, DataFrame, functions as F, types as T



# ---------------------------------------------------------------------------

# SPARK INITIALIZER

# ---------------------------------------------------------------------------

def get_spark_session(app_name: str) -> SparkSession:

    spark = (

        SparkSession.builder

        .appName(app_name)

        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")

        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")

        .getOrCreate()

    )

    spark.sparkContext.setLogLevel("WARN")

    return spark



# ---------------------------------------------------------------------------

# EXTRACT

# ---------------------------------------------------------------------------

def extract(config: dict) -> str:

    source_dir = config["paths"]["source"]

    bronze_dir = config["paths"]["bronze"]

    archive_dir = config["paths"]["archive"]



    os.makedirs(bronze_dir, exist_ok=True)

    os.makedirs(archive_dir, exist_ok=True)



    for file in os.listdir(source_dir):

        if file.endswith(".csv"):

            src_file = os.path.join(source_dir, file)

            dest_file = os.path.join(bronze_dir, file)

            shutil.move(src_file, dest_file)

            logging.info(f"Moved file {file} → Bronze layer.")



            archive_path = os.path.join(

                archive_dir,

                f"{os.path.splitext(file)[0]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            )

            shutil.copy(dest_file, archive_path)

            logging.info(f"Archived {file} → {archive_path}")



    return bronze_dir



# ---------------------------------------------------------------------------

# DATA CLEANING

# ---------------------------------------------------------------------------

def clean_data(df: DataFrame) -> DataFrame:

    cleaned_df = (

        df.dropDuplicates(["transaction_id"])

          .withColumn("amount", F.round(F.col("amount"), 2))

          .withColumn(

              "transaction_timestamp",

              F.coalesce(F.col("transaction_timestamp"), F.current_timestamp())

          )

          .withColumn(

              "transaction_date",

              F.coalesce(F.col("transaction_date"), F.current_date())

          )

    )

    return cleaned_df



# ---------------------------------------------------------------------------

# DATA QUALITY CHECKS

# ---------------------------------------------------------------------------

def apply_dq_checks(df: DataFrame) -> (DataFrame, DataFrame):

    valid_df = (

        df.filter(F.col("transaction_id").isNotNull())

          .filter(F.col("product_id").isNotNull())

          .filter(F.col("amount") > 0)

    )

    invalid_df = df.subtract(valid_df)

    logging.info(f"Valid records: {valid_df.count()} | Invalid records: {invalid_df.count()}")

    return valid_df, invalid_df



# ---------------------------------------------------------------------------

# TRANSFORM

# ---------------------------------------------------------------------------

def transform(spark: SparkSession, input_path: str) -> (DataFrame, DataFrame):

    schema = T.StructType([

        T.StructField("transaction_id", T.StringType(), True),

        T.StructField("store_id", T.StringType(), True),

        T.StructField("customer_id", T.StringType(), True),

        T.StructField("product_id", T.StringType(), True),

        T.StructField("quantity", T.DoubleType(), True),

        T.StructField("amount", T.DoubleType(), True),

        T.StructField("channel", T.StringType(), True),

        T.StructField("transaction_timestamp", T.TimestampType(), True),

        T.StructField("transaction_date", T.DateType(), True)

    ])



    df = (

        spark.read

        .schema(schema)

        .option("header", False)

        .option("ignoreLeadingWhiteSpace", True)

        .option("ignoreTrailingWhiteSpace", True)

        .csv(f"{input_path}/*.csv")

    )



    logging.info(f"Loaded {df.count()} records from Bronze layer.")



    cleaned_df = clean_data(df)

    valid_df, invalid_df = apply_dq_checks(cleaned_df)

    return valid_df, invalid_df



# ---------------------------------------------------------------------------

# LOAD

# ---------------------------------------------------------------------------

def load(valid_df: DataFrame, invalid_df: DataFrame, config: dict):

    paths = config["paths"]



    os.makedirs(paths["quarantine"], exist_ok=True)



    # Write invalid records to Quarantine

    if invalid_df.count() > 0:

        invalid_df.write.mode("overwrite").parquet(paths["quarantine"])

        logging.warning(f"Invalid records written to {paths['quarantine']}")



    if valid_df.count() > 0:

        logging.warning(f"++++++ Valid count >0 +++++++++++")



    # ----------------- Hudi Options (Hardcoded) -----------------

    hudi_options = {

        "hoodie.table.name": "retail_transactions_hudi",

        "hoodie.datasource.write.recordkey.field": "transaction_id",

        "hoodie.datasource.write.partitionpath.field": "transaction_date",

        "hoodie.datasource.write.precombine.field": "transaction_timestamp",

        "hoodie.datasource.write.operation": "upsert",

        "hoodie.datasource.write.table.type": "COPY_ON_WRITE",

        "hoodie.datasource.write.hive_style_partitioning": "true",

        "hoodie.datasource.write.keygenerator.class": "org.apache.hudi.keygen.SimpleKeyGenerator",

        "hoodie.datasource.hive_sync.enable": "false"

    }





    valid_df.write.format("hudi").options(**hudi_options).mode("overwrite").save(paths["gold"])





    logging.info(f"Upserted valid records to Gold Hudi table: {paths['gold']}")



# ---------------------------------------------------------------------------

# MAIN

# ---------------------------------------------------------------------------

def main():

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")



    # ----------------- Hardcoded Paths (Example) -----------------

    config = {

        "paths": {

            "source": "/home/cloud/week8/source/landing",

            "bronze": "/home/cloud/week8/bronze/transactions",

            "gold": "/home/cloud/week8/gold/transactions_hudi",

            "archive": "/home/cloud/week8/source/archive",

            "quarantine": "/home/cloud/week8/quarantine/transactions_invalid"

        },

        "spark": {

            "app_name_ingestion": "Retail_Ingestion_ETL"

        }

    }



    spark = get_spark_session(config["spark"]["app_name_ingestion"])

    logging.info("Starting Retail Ingestion ETL (Source → Bronze → Gold)")



    bronze_path = extract(config)

    valid_df, invalid_df = transform(spark, bronze_path)

    load(valid_df, invalid_df, config)



    logging.info("Retail Ingestion Pipeline completed successfully.")

    spark.stop()





if __name__ == "__main__":

    main()


