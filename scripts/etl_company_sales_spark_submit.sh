#!/bin/bash

echo "=========================================="
echo "Starting ETL Pipeline: Company Sales"
echo "=========================================="

spark-submit \
  --packages org.apache.hudi:hudi-spark3.5-bundle_2.12:0.15.0,org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262 \
  --conf spark.serializer=org.apache.spark.serializer.KryoSerializer \
  --conf spark.sql.legacy.timeParserPolicy=LEGACY \
  /workspace/src/etl_company_sales.py \
  --config /workspace/configs/ecomm_prod.yml

echo "=========================================="
echo "ETL Pipeline: Company Sales Completed"
echo "=========================================="
