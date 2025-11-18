#!/bin/bash

echo "=========================================="
echo "Starting ETL Pipeline: Competitor Sales"
echo "=========================================="

spark-submit \
  --conf spark.serializer=org.apache.spark.serializer.KryoSerializer \
  --conf spark.sql.legacy.timeParserPolicy=LEGACY \
  /workspace/src/etl_competitor_sales.py \
  --config /workspace/configs/ecomm_prod.yml

echo "=========================================="
echo "ETL Pipeline: Competitor Sales Completed"
echo "=========================================="
