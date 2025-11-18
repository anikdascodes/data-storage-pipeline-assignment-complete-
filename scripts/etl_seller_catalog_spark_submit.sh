#!/bin/bash

echo "=========================================="
echo "Starting ETL Pipeline: Seller Catalog"
echo "=========================================="

spark-submit \
  --conf spark.serializer=org.apache.spark.serializer.KryoSerializer \
  --conf spark.sql.legacy.timeParserPolicy=LEGACY \
  /workspace/src/etl_seller_catalog.py \
  --config /workspace/configs/ecomm_prod.yml

echo "=========================================="
echo "ETL Pipeline: Seller Catalog Completed"
echo "=========================================="
