"""
Consumption Layer: Recommendation System
- Reads Hudi tables from gold layer
- Calculates top-selling items per category
- Identifies missing items per seller
- Generates recommendations with business metrics
- Outputs to CSV
"""

import argparse
import logging
import os
import yaml
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql.window import Window
from utils import ensure_dir

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_spark_session(app_name: str) -> SparkSession:
    """Initialize Spark session"""
    spark = (
        SparkSession.builder
        .appName(app_name)
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def read_hudi_table(spark: SparkSession, hudi_path: str, table_name: str) -> DataFrame:
    """Read Hudi table"""
    df = spark.read.format("hudi").load(hudi_path)
    logger.info(f"Loaded {df.count()} records from {table_name}")
    return df


def get_top_company_items(company_sales: DataFrame, seller_catalog: DataFrame, top_n: int = 10) -> DataFrame:
    """
    Get top-selling items from company sales per category
    
    Logic:
    1. Join sales data with catalog to get category information
    2. Aggregate total units sold per item
    3. Rank items within each category using window function
    4. Select top N items per category
    """
    # Join company sales with seller catalog to get category information
    # Left join ensures we keep all sales even if item not in catalog
    sales_with_category = company_sales.join(
        seller_catalog.select("item_id", "category", "item_name").distinct(),
        "item_id",
        "left"
    )
    
    # Aggregate sales by item and category
    # Sum units_sold and revenue across all transactions for each item
    item_sales = (
        sales_with_category
        .groupBy("item_id", "category", "item_name")
        .agg(
            F.sum("units_sold").alias("total_units_sold"),
            F.sum("revenue").alias("total_revenue")
        )
    )
    
    # Rank items within each category using window function
    # Partition by category to rank items separately in each category
    # Order by total_units_sold descending to get best sellers first
    window_spec = Window.partitionBy("category").orderBy(F.col("total_units_sold").desc())
    
    # Apply ranking and filter to top N items per category
    top_items = (
        item_sales
        .withColumn("rank", F.row_number().over(window_spec))
        .filter(F.col("rank") <= top_n)
        .select("item_id", "category", "item_name", "total_units_sold", "rank")
    )
    
    logger.info(f"Identified top {top_n} company items per category")
    return top_items


def get_top_competitor_items(competitor_sales: DataFrame, seller_catalog: DataFrame, top_n: int = 10) -> DataFrame:
    """
    Get top-selling items from competitor sales
    """
    # Get item names and categories from seller catalog
    catalog_info = seller_catalog.select("item_id", "category", "item_name").distinct()
    
    # Aggregate competitor sales by item
    item_sales = (
        competitor_sales
        .groupBy("item_id")
        .agg(
            F.sum("units_sold").alias("total_units_sold"),
            F.sum("revenue").alias("total_revenue"),
            F.avg("marketplace_price").alias("avg_marketplace_price"),
            F.countDistinct("seller_id").alias("num_sellers")
        )
    )
    
    # Join with catalog to get category and item name
    item_sales_with_info = item_sales.join(catalog_info, "item_id", "left")
    
    # Calculate expected units sold per seller (with edge case handling)
    # If num_sellers is 0 or null, use total_units_sold as fallback
    item_sales_with_info = item_sales_with_info.withColumn(
        "expected_units_sold",
        F.when((F.col("num_sellers").isNotNull()) & (F.col("num_sellers") > 0), 
               F.col("total_units_sold") / F.col("num_sellers"))
        .otherwise(F.col("total_units_sold"))
    )
    
    # Rank items overall
    top_items = (
        item_sales_with_info
        .orderBy(F.col("total_units_sold").desc())
        .limit(top_n)
        .select(
            "item_id",
            "category",
            "item_name",
            "total_units_sold",
            "avg_marketplace_price",
            "expected_units_sold",
            "num_sellers"
        )
    )
    
    logger.info(f"Identified top {top_n} competitor items")
    return top_items


def build_company_metrics(company_sales: DataFrame, seller_catalog: DataFrame) -> DataFrame:
    """Aggregate company metrics for pricing and expected units."""
    aggregates = (
        company_sales
        .groupBy("item_id")
        .agg(
            F.sum("units_sold").alias("company_total_units"),
            F.sum("revenue").alias("company_total_revenue")
        )
        .withColumn(
            "company_market_price",
            F.when(F.col("company_total_units") > 0,
                   F.col("company_total_revenue") / F.col("company_total_units"))
             .otherwise(None)
        )
    )

    seller_counts = (
        seller_catalog
        .groupBy("item_id")
        .agg(F.countDistinct("seller_id").alias("company_seller_count"))
    )

    metrics = aggregates.join(seller_counts, "item_id", "left")
    metrics = metrics.withColumn(
        "company_expected_units",
        F.when(F.col("company_seller_count") > 0,
               F.col("company_total_units") / F.col("company_seller_count"))
         .otherwise(F.col("company_total_units"))
    )
    return metrics


def build_competitor_metrics(competitor_sales: DataFrame) -> DataFrame:
    """Aggregate competitor metrics for pricing and expected units."""
    metrics = (
        competitor_sales
        .groupBy("item_id")
        .agg(
            F.sum("units_sold").alias("competitor_total_units"),
            F.sum("revenue").alias("competitor_total_revenue"),
            F.avg("marketplace_price").alias("competitor_market_price"),
            F.countDistinct("seller_id").alias("competitor_seller_count")
        )
    )

    metrics = metrics.withColumn(
        "competitor_expected_units",
        F.when(F.col("competitor_seller_count") > 0,
               F.col("competitor_total_units") / F.col("competitor_seller_count"))
         .otherwise(F.col("competitor_total_units"))
    )
    return metrics


def build_company_gap(top_competitor_items: DataFrame, seller_catalog: DataFrame) -> DataFrame:
    """Identify top competitor items missing entirely from the company catalog."""
    catalog_items = seller_catalog.select("item_id").distinct()
    gap = top_competitor_items.join(catalog_items, "item_id", "left_anti")
    return gap.select(
        "item_id",
        "item_name",
        "category",
        F.col("total_units_sold"),
        F.round("avg_marketplace_price", 2).alias("market_price"),
        F.round("expected_units_sold", 2).alias("expected_units_sold")
    )


def generate_recommendations(
    seller_catalog: DataFrame,
    company_sales: DataFrame,
    top_company_items: DataFrame,
    top_competitor_items: DataFrame,
    competitor_sales: DataFrame
) -> DataFrame:
    """
    Generate recommendations for each seller
    
    Logic:
    1. Identify all sellers
    2. Get top items (company + competitor)
    3. Find items missing from each seller's catalog
    4. Calculate expected revenue for missing items
    5. Rank recommendations by expected revenue
    """
    # Get all unique sellers from catalog
    sellers = seller_catalog.select("seller_id").distinct()
    
    # Get current catalog per seller (what they already have)
    seller_items = seller_catalog.select("seller_id", "item_id")
    
    # Combine top company and competitor items (union of both lists)
    # These are the items we want to recommend
    all_top_items = top_company_items.select("item_id", "category", "item_name").union(
        top_competitor_items.select("item_id", "category", "item_name")
    ).distinct()
    
    # Cross join: Create all possible (seller, item) combinations
    # This gives us every seller paired with every top item
    seller_item_combinations = sellers.crossJoin(all_top_items)
    
    # Filter out items already in seller's catalog using left anti join
    # Left anti join keeps only rows from left table that have no match in right table
    # Result: Only items that seller does NOT currently have
    missing_items = seller_item_combinations.join(
        seller_items,
        (seller_item_combinations.seller_id == seller_items.seller_id) & 
        (seller_item_combinations.item_id == seller_items.item_id),
        "left_anti"
    )
    
    competitor_metrics = build_competitor_metrics(competitor_sales)
    company_metrics = build_company_metrics(company_sales, seller_catalog)
    metrics = competitor_metrics.join(company_metrics, "item_id", "full_outer")

    recommendations = missing_items.join(metrics, "item_id", "left")

    recommendations = recommendations.withColumn(
        "market_price",
        F.coalesce(
            F.col("company_market_price"),
            F.col("competitor_market_price"),
            F.lit(0.0)
        )
    )

    recommendations = recommendations.withColumn(
        "expected_units_sold",
        F.coalesce(
            F.col("company_expected_units"),
            F.col("competitor_expected_units"),
            F.lit(0.0)
        )
    )

    recommendations = recommendations.withColumn(
        "expected_revenue",
        F.round(F.col("expected_units_sold") * F.col("market_price"), 2)
    )

    recommendations = recommendations.fillna({
        "expected_revenue": 0.0
    })
    
    # Select and order final columns
    final_recommendations = recommendations.select(
        "seller_id",
        "item_id",
        "item_name",
        "category",
        F.round("market_price", 2).alias("market_price"),
        F.round("expected_units_sold", 2).alias("expected_units_sold"),
        F.round("expected_revenue", 2).alias("expected_revenue")
    ).orderBy("seller_id", F.col("expected_revenue").desc())
    
    logger.info(f"Generated {final_recommendations.count()} recommendations")
    return final_recommendations


def validate_recommendations(recommendations: DataFrame) -> bool:
    """
    Validate recommendation outputs for data quality
    Returns True if all validations pass, False otherwise
    """
    logger.info("Validating recommendations quality...")

    all_valid = True

    # Check 1: Expected revenue should be positive
    invalid_revenue = recommendations.filter(F.col("expected_revenue") < 0).count()
    if invalid_revenue > 0:
        logger.warning(f"⚠️  Found {invalid_revenue} recommendations with negative expected revenue")
        all_valid = False
    else:
        logger.info(f"✓ All recommendations have positive expected revenue")

    # Check 2: Expected units should be positive
    invalid_units = recommendations.filter(F.col("expected_units_sold") <= 0).count()
    if invalid_units > 0:
        logger.warning(f"⚠️  Found {invalid_units} recommendations with zero/negative expected units")
        all_valid = False
    else:
        logger.info(f"✓ All recommendations have positive expected units")

    # Check 3: Market price should be reasonable (not zero)
    zero_price = recommendations.filter(F.col("market_price") <= 0).count()
    if zero_price > 0:
        logger.warning(f"⚠️  Found {zero_price} recommendations with zero/negative market price")
        all_valid = False
    else:
        logger.info(f"✓ All recommendations have positive market prices")

    # Check 4: No null values in critical columns
    null_checks = [
        ("seller_id", recommendations.filter(F.col("seller_id").isNull()).count()),
        ("item_id", recommendations.filter(F.col("item_id").isNull()).count()),
        ("expected_revenue", recommendations.filter(F.col("expected_revenue").isNull()).count())
    ]

    for col_name, null_count in null_checks:
        if null_count > 0:
            logger.warning(f"⚠️  Found {null_count} null values in {col_name}")
            all_valid = False

    if all([count == 0 for _, count in null_checks]):
        logger.info(f"✓ No null values in critical columns")

    # Summary statistics
    total_recommendations = recommendations.count()
    unique_sellers = recommendations.select("seller_id").distinct().count()
    unique_items = recommendations.select("item_id").distinct().count()

    # Calculate statistics
    stats = recommendations.agg(
        F.avg("expected_revenue").alias("avg_revenue"),
        F.max("expected_revenue").alias("max_revenue"),
        F.min("expected_revenue").alias("min_revenue")
    ).collect()[0]

    logger.info(f"")
    logger.info(f"Recommendation Statistics:")
    logger.info(f"  Total recommendations: {total_recommendations:,}")
    logger.info(f"  Unique sellers: {unique_sellers:,}")
    logger.info(f"  Unique items recommended: {unique_items:,}")
    logger.info(f"  Avg expected revenue: ${stats['avg_revenue']:,.2f}")
    logger.info(f"  Max expected revenue: ${stats['max_revenue']:,.2f}")
    logger.info(f"  Min expected revenue: ${stats['min_revenue']:,.2f}")

    return all_valid


def write_to_csv(df: DataFrame, output_path: str):
    """Write recommendations to CSV"""
    ensure_dir(os.path.dirname(output_path.rstrip('/')) or output_path)
    df.coalesce(1).write.mode("overwrite").option("header", True).csv(output_path)
    logger.info(f"Written recommendations to {output_path}")


def write_company_gap_report(gap_df: DataFrame, recommendation_output: str):
    """Persist items missing from company catalog but strong in competitor data."""
    if gap_df.rdd.isEmpty():
        logger.info("No competitor-driven gaps to report")
        return

    parent = os.path.dirname(recommendation_output.rstrip('/')) or recommendation_output
    gap_path = os.path.join(parent, "company_catalog_gap")
    ensure_dir(gap_path)
    (
        gap_df
        .orderBy(F.col("total_units_sold").desc())
        .coalesce(1)
        .write
        .mode("overwrite")
        .option("header", True)
        .csv(gap_path)
    )
    logger.info(f"Written company catalog gap report to {gap_path}")


def main(config_path: str):
    """Main consumption layer execution"""
    logger.info("Starting Consumption Layer: Recommendation System")
    
    # Load configuration
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    seller_catalog_hudi = config['recommendation']['seller_catalog_hudi']
    company_sales_hudi = config['recommendation']['company_sales_hudi']
    competitor_sales_hudi = config['recommendation']['competitor_sales_hudi']
    output_csv = config['recommendation']['output_csv']
    
    # Initialize Spark
    spark = get_spark_session("Consumption_Recommendation")
    
    try:
        # Read Hudi tables
        seller_catalog = read_hudi_table(spark, seller_catalog_hudi, "seller_catalog")
        company_sales = read_hudi_table(spark, company_sales_hudi, "company_sales")
        competitor_sales = read_hudi_table(spark, competitor_sales_hudi, "competitor_sales")
        
        # Get top-selling items
        top_company_items = get_top_company_items(company_sales, seller_catalog, top_n=10)
        top_competitor_items = get_top_competitor_items(competitor_sales, seller_catalog, top_n=10)
        
        # Generate recommendations
        recommendations = generate_recommendations(
            seller_catalog,
            company_sales,
            top_company_items,
            top_competitor_items,
            competitor_sales
        )
        company_gap = build_company_gap(top_competitor_items, seller_catalog)

        # Validate recommendations quality
        is_valid = validate_recommendations(recommendations)
        if not is_valid:
            logger.warning("⚠️  Some validation checks failed. Review warnings above.")
        else:
            logger.info("✅ All validation checks passed!")

        # Write to CSV
        write_to_csv(recommendations, output_csv)
        write_company_gap_report(company_gap, output_csv)
        
        logger.info("Consumption Layer: Recommendation System completed successfully")
        
    except Exception as e:
        logger.error(f"Consumption layer failed: {str(e)}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consumption Layer: Recommendation System")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    args = parser.parse_args()
    main(args.config)
