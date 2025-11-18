#!/bin/bash

echo "=========================================="
echo "Starting ETL Pipeline: Company Sales"
echo "=========================================="

spark-submit \
  --conf spark.serializer=org.apache.spark.serializer.KryoSerializer \
  --conf spark.sql.legacy.timeParserPolicy=LEGACY \
  /workspace/src/etl_company_sales.py \
  --config /workspace/configs/ecomm_prod.yml

echo "=========================================="
echo "ETL Pipeline: Company Sales Completed"
echo "=========================================="
