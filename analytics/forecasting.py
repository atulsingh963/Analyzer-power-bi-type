import datetime
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from statsmodels.tsa.holtwinters import ExponentialSmoothing

def generate_forecast(dates_str: list, values: list, steps: int = 15) -> dict:
    """
    Fits a Holt-Winters Exponential Smoothing model (or falls back to Linear Regression)
    to forecast the next N steps of a time series.
    Returns:
        - dates: list of predicted dates (ISO format strings)
        - values: list of predicted values
        - upper_bound: list of upper confidence values
        - lower_bound: list of lower confidence values
    """
    if len(values) < 5:
        # Not enough data points to do meaningful forecast - do a simple projection
        return {"error": "Insufficient historical data points to train model. Minimum 5 records required."}
        
    try:
        # Parse dates
        parsed_dates = [pd.to_datetime(d) for d in dates_str]
        
        # Create pandas Series with DatetimeIndex
        ts = pd.Series(values, index=parsed_dates)
        # Sort and resample to fill any gaps (daily)
        ts = ts.sort_index()
        ts = ts.resample('D').mean().ffill()  # Fill any gaps
        
        if len(ts) < 5:
            return {"error": "Insufficient resampled historical dates."}
            
        # 1. Try Holt-Winters Exponential Smoothing
        try:
            # Determine trend configuration
            model = ExponentialSmoothing(
                ts.values,
                trend='add',
                seasonal=None,  # No seasonality for simple daily forecasts unless seasonal period is defined
                initialization_method="estimated"
            )
            fit = model.fit(optimized=True)
            predictions = fit.forecast(steps)
            
            # Shaded bounds based on standard deviation
            std_dev = float(np.std(ts.values - fit.fittedvalues)) if len(ts.values) > 1 else float(np.std(ts.values))
            if std_dev == 0:
                std_dev = float(np.mean(values)) * 0.1
                
            lower_bounds = predictions - (1.96 * std_dev)
            upper_bounds = predictions + (1.96 * std_dev)
            
        except Exception:
            # 2. Fallback: Linear Regression model
            print("Forecasting: Holt-Winters failed, falling back to linear regression projection...")
            X = np.arange(len(ts)).reshape(-1, 1)
            y = ts.values
            reg = LinearRegression().fit(X, y)
            
            future_X = np.arange(len(ts), len(ts) + steps).reshape(-1, 1)
            predictions = reg.predict(future_X)
            
            # Set artificial bounds expanding into the future
            std_dev = float(np.std(y - reg.predict(X))) if len(y) > 1 else float(np.mean(y)) * 0.15
            if std_dev == 0:
                std_dev = 1.0
                
            lower_bounds = [predictions[i] - (1.96 * std_dev * (1 + i * 0.1)) for i in range(steps)]
            upper_bounds = [predictions[i] + (1.96 * std_dev * (1 + i * 0.1)) for i in range(steps)]
            
        # Generate future dates
        last_date = ts.index[-1]
        future_dates = [
            (last_date + datetime.timedelta(days=i+1)).strftime("%Y-%m-%d")
            for i in range(steps)
        ]
        
        # Clean negative numbers in bounds if values are strictly positive
        min_hist = min(values)
        if min_hist >= 0:
            lower_bounds = [max(0.0, float(b)) for b in lower_bounds]
        else:
            lower_bounds = [float(b) for b in lower_bounds]
            
        return {
            "success": True,
            "dates": future_dates,
            "values": [round(float(v), 2) for v in predictions],
            "upper_bound": [round(float(v), 2) for v in upper_bounds],
            "lower_bound": [round(float(v), 2) for v in lower_bounds]
        }
        
    except Exception as e:
        return {"error": f"Forecasting engine error: {str(e)}"}

def calculate_churn_classification(sales_df: pd.DataFrame) -> dict:
    """
    Groups sales transactions by store/customer properties and trains a
    Random Forest Churn Classifier. Returns top customers with high churn probability.
    """
    try:
        # Check required columns
        required_cols = ["transaction_id", "date", "store_name", "sales_amount", "customer_age", "customer_gender"]
        for c in required_cols:
            if c not in sales_df.columns:
                return {"error": f"Missing column '{c}' in data."}
                
        # Group sales by customer segment / virtual customer profile based on age & gender & store
        # Since we do not have specific customer_id in seed transactions, we build virtual customer profiles
        # to analyze segment retention rate
        sales_df = sales_df.copy()
        sales_df["date"] = pd.to_datetime(sales_df["date"])
        
        # Virtual customer key: store + gender + age
        sales_df["customer_key"] = (
            sales_df["store_name"].astype(str) + "_" + 
            sales_df["customer_gender"].astype(str) + "_" + 
            sales_df["customer_age"].astype(str)
        )
        
        # Aggregate features per customer
        agg = sales_df.groupby("customer_key").agg(
            total_spend=("sales_amount", "sum"),
            avg_spend=("sales_amount", "mean"),
            frequency=("transaction_id", "count"),
            last_purchase_date=("date", "max"),
            first_purchase_date=("date", "min"),
            age=("customer_age", "first"),
            gender=("customer_gender", "first"),
            store=("store_name", "first")
        ).reset_index()
        
        # Find study duration context
        max_date = sales_df["date"].max()
        
        # Recency (days since last purchase)
        agg["recency"] = (max_date - agg["last_purchase_date"]).dt.days
        
        # Churn definition: Recency > 180 days (or median recency if small timeline)
        threshold_days = max(30, int(agg["recency"].median() * 1.5))
        agg["churned"] = (agg["recency"] > threshold_days).astype(int)
        
        # Prepare training columns
        le_gender = LabelEncoder()
        le_store = LabelEncoder()
        
        agg["gender_encoded"] = le_gender.fit_transform(agg["gender"])
        agg["store_encoded"] = le_store.fit_transform(agg["store"])
        
        features = ["total_spend", "avg_spend", "frequency", "age", "gender_encoded", "store_encoded"]
        X = agg[features]
        y = agg["churned"]
        
        # Train Random Forest Classifier if we have distinct classes
        if len(y.unique()) > 1:
            clf = RandomForestClassifier(n_estimators=50, random_state=42)
            clf.fit(X, y)
            
            # Predict probabilities
            probabilities = clf.predict_proba(X)[:, 1]
        else:
            # Mock linear risk score based on recency if single class
            probabilities = (agg["recency"] / agg["recency"].max()).values
            
        agg["churn_risk"] = [round(float(p) * 100, 1) for p in probabilities]
        
        # Select top risk profiles
        top_risk = agg[agg["churn_risk"] >= 50.0].sort_values("churn_risk", ascending=False).head(10)
        
        results_list = []
        for _, row in top_risk.iterrows():
            results_list.append({
                "profile_id": row["customer_key"],
                "store": row["store"],
                "gender": row["gender"],
                "age": int(row["age"]),
                "frequency": int(row["frequency"]),
                "total_spend": round(float(row["total_spend"]), 2),
                "recency_days": int(row["recency"]),
                "risk_probability": row["churn_risk"]
            })
            
        return {
            "success": True,
            "total_segments_analyzed": len(agg),
            "churned_segments": int(agg["churned"].sum()),
            "overall_churn_rate": round(float(agg["churned"].mean()) * 100, 1),
            "top_risk_profiles": results_list
        }
    except Exception as e:
        return {"error": f"Churn analytics calculation error: {str(e)}"}
