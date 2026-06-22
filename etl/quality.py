import os
import polars as pl
from sqlalchemy.orm import Session
from backend.models.models import Dataset

def get_dataset_quality_metrics(dataset_file_path: str, file_type: str) -> dict:
    """
    Computes data quality statistics for a given CSV/Parquet file.
    Returns:
        - total_rows: total number of rows
        - duplicate_rows: number of duplicate records
        - duplicate_percentage: ratio of duplicates
        - column_stats: dictionary of columns with null counts, percentages, and basic stats
    """
    if not os.path.exists(dataset_file_path):
        return {"error": "Dataset file not found"}
        
    try:
        # Load dataset
        if file_type.lower() == "parquet":
            df = pl.read_parquet(dataset_file_path)
        else:
            df = pl.read_csv(dataset_file_path)
            
        total_rows = df.height
        if total_rows == 0:
            return {
                "total_rows": 0,
                "duplicate_rows": 0,
                "duplicate_percentage": 0.0,
                "column_stats": {}
            }
            
        # Calculate duplicates
        # We check duplicates by checking if unique length matches height
        unique_rows = df.unique().height
        duplicate_rows = total_rows - unique_rows
        duplicate_pct = round((duplicate_rows / total_rows) * 100, 2)
        
        column_stats = {}
        for col in df.columns:
            series = df[col]
            null_count = series.null_count()
            null_pct = round((null_count / total_rows) * 100, 2)
            
            stat = {
                "null_count": null_count,
                "null_percentage": null_pct,
                "data_type": str(series.dtype),
                "is_numeric": series.dtype.is_numeric()
            }
            
            # Additional metrics for numeric columns
            if series.dtype.is_numeric():
                # Drop nulls for statistics
                clean_series = series.drop_nulls()
                if clean_series.len() > 0:
                    min_val = clean_series.min()
                    max_val = clean_series.max()
                    mean_val = clean_series.mean()
                    median_val = clean_series.median()
                    std_val = clean_series.std()
                    
                    # Calculate Outliers using IQR (Interquartile Range)
                    # Q1 (25th percentile) and Q3 (75th percentile)
                    q1 = clean_series.quantile(0.25)
                    q3 = clean_series.quantile(0.75)
                    
                    # Check if Q1 and Q3 are not None (in case of empty series or errors)
                    if q1 is not None and q3 is not None:
                        iqr = q3 - q1
                        lower_bound = q1 - 1.5 * iqr
                        upper_bound = q3 + 1.5 * iqr
                        
                        outlier_count = clean_series.filter((clean_series < lower_bound) | (clean_series > upper_bound)).len()
                    else:
                        outlier_count = 0
                        
                    stat.update({
                        "min": round(min_val, 2) if isinstance(min_val, float) else min_val,
                        "max": round(max_val, 2) if isinstance(max_val, float) else max_val,
                        "mean": round(mean_val, 2) if mean_val is not None else None,
                        "median": round(median_val, 2) if median_val is not None else None,
                        "std": round(std_val, 2) if std_val is not None else None,
                        "outlier_count": outlier_count,
                        "outlier_percentage": round((outlier_count / total_rows) * 100, 2)
                    })
                else:
                    stat.update({
                        "min": None, "max": None, "mean": None, "median": None,
                        "std": None, "outlier_count": 0, "outlier_percentage": 0.0
                    })
            else:
                # String columns stats (unique values count)
                unique_vals = series.unique().len()
                stat.update({
                    "unique_values_count": unique_vals,
                    "unique_values_percentage": round((unique_vals / total_rows) * 100, 2)
                })
                
            column_stats[col] = stat
            
        return {
            "total_rows": total_rows,
            "duplicate_rows": duplicate_rows,
            "duplicate_percentage": duplicate_pct,
            "column_stats": column_stats
        }
    except Exception as e:
        return {"error": f"Failed to analyze dataset quality: {str(e)}"}
