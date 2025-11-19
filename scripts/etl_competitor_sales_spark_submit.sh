#!/bin/bash

echo "=========================================="
echo "Starting ETL Pipeline: Competitor Sales"
echo "=========================================="

spark-submit \
  --packages org.apache.hudi:hudi-spark3.5-bundle_2.12:0.15.0,org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262 \
  --driver-memory ${SPARK_DRIVER_MEMORY:-2g} \
  --executor-memory ${SPARK_EXECUTOR_MEMORY:-2g} \
  --conf spark.serializer=org.apache.spark.serializer.KryoSerializer \
  --conf spark.sql.legacy.timeParserPolicy=LEGACY \
  --conf spark.sql.adaptive.enabled=true \
  --conf spark.sql.adaptive.coalescePartitions.enabled=true \
  /workspace/src/etl_competitor_sales.py \
  --config /workspace/configs/ecomm_prod.yml

echo "=========================================="
echo "ETL Pipeline: Competitor Sales Completed"
echo "=========================================="
