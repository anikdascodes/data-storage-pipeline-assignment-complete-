#!/bin/bash

echo "=========================================="
echo "Starting Consumption Layer: Recommendations"
echo "=========================================="

spark-submit \
  --conf spark.serializer=org.apache.spark.serializer.KryoSerializer \
  --conf spark.sql.legacy.timeParserPolicy=LEGACY \
  /workspace/src/consumption_recommendation.py \
  --config /workspace/configs/ecomm_prod.yml

echo "=========================================="
echo "Consumption Layer: Recommendations Completed"
echo "=========================================="
