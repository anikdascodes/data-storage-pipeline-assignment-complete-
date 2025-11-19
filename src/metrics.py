"""
Metrics Collection Module
Tracks and reports pipeline execution metrics
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class PipelineMetrics:
    """Collects and reports pipeline execution metrics"""
    
    def __init__(self, pipeline_name: str):
        self.pipeline_name = pipeline_name
        self.start_time = datetime.now()
        self.metrics = {
            "pipeline_name": pipeline_name,
            "start_time": self.start_time.isoformat(),
            "end_time": None,
            "duration_seconds": None,
            "status": "RUNNING",
            "records": {
                "input_count": 0,
                "valid_count": 0,
                "invalid_count": 0,
                "duplicate_count": 0,
                "output_count": 0
            },
            "data_quality": {
                "valid_percentage": 0.0,
                "invalid_percentage": 0.0
            },
            "errors": []
        }
    
    def set_input_count(self, count: int):
        """Set input record count"""
        self.metrics["records"]["input_count"] = count
        logger.info(f"Input records: {count:,}")
    
    def set_valid_count(self, count: int):
        """Set valid record count"""
        self.metrics["records"]["valid_count"] = count
        logger.info(f"Valid records: {count:,}")
    
    def set_invalid_count(self, count: int):
        """Set invalid record count"""
        self.metrics["records"]["invalid_count"] = count
        logger.info(f"Invalid records: {count:,}")
    
    def set_duplicate_count(self, before: int, after: int):
        """Calculate and set duplicate count"""
        duplicates = before - after
        self.metrics["records"]["duplicate_count"] = duplicates
        logger.info(f"Duplicates removed: {duplicates:,}")
    
    def set_output_count(self, count: int):
        """Set output record count"""
        self.metrics["records"]["output_count"] = count
        logger.info(f"Output records: {count:,}")
    
    def add_error(self, error_msg: str):
        """Add error message"""
        self.metrics["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "message": error_msg
        })
        logger.error(error_msg)
    
    def finalize(self, status: str = "SUCCESS"):
        """Finalize metrics collection"""
        self.metrics["end_time"] = datetime.now().isoformat()
        self.metrics["status"] = status
        
        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        self.metrics["duration_seconds"] = round(duration, 2)
        
        # Calculate data quality percentages
        input_count = self.metrics["records"]["input_count"]
        if input_count > 0:
            valid_count = self.metrics["records"]["valid_count"]
            invalid_count = self.metrics["records"]["invalid_count"]
            
            self.metrics["data_quality"]["valid_percentage"] = round(
                (valid_count / input_count) * 100, 2
            )
            self.metrics["data_quality"]["invalid_percentage"] = round(
                (invalid_count / input_count) * 100, 2
            )
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        lines = [
            f"\n{'='*60}",
            f"PIPELINE METRICS: {self.pipeline_name}",
            f"{'='*60}",
            f"Status: {self.metrics['status']}",
            f"Duration: {self.metrics['duration_seconds']}s",
            f"",
            f"Records:",
            f"  Input:      {self.metrics['records']['input_count']:>10,}",
            f"  Valid:      {self.metrics['records']['valid_count']:>10,} ({self.metrics['data_quality']['valid_percentage']}%)",
            f"  Invalid:    {self.metrics['records']['invalid_count']:>10,} ({self.metrics['data_quality']['invalid_percentage']}%)",
            f"  Duplicates: {self.metrics['records']['duplicate_count']:>10,}",
            f"  Output:     {self.metrics['records']['output_count']:>10,}",
            f"{'='*60}\n"
        ]
        return "\n".join(lines)
    
    def save_to_file(self, output_dir: str = "/workspace/data/metrics"):
        """Save metrics to JSON file"""
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.pipeline_name}_{timestamp}.json"
            filepath = Path(output_dir) / filename
            
            with open(filepath, 'w') as f:
                json.dump(self.metrics, f, indent=2)
            
            logger.info(f"Metrics saved to: {filepath}")
        except Exception as e:
            logger.warning(f"Failed to save metrics: {e}")
    
    def print_summary(self):
        """Print summary to console"""
        print(self.get_summary())
