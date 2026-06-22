import os
import random
from datetime import datetime, timedelta
import polars as pl
import numpy as np

# Set directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "lakehouse", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

def generate_store_sales():
    print("Generating mock store sales dataset...")
    # Generate daily sales for the last 730 days
    start_date = datetime.now() - timedelta(days=730)
    records = []
    
    categories = ["Electronics", "Apparel", "Home & Kitchen", "Groceries", "Books"]
    stores = [
        (1, "New York Downtown"),
        (2, "San Francisco Bay"),
        (3, "Chicago Center"),
        (4, "Austin South"),
        (5, "Seattle North")
    ]
    genders = ["Male", "Female", "Non-binary", "Undisclosed"]
    
    # Set random seed for reproducibility
    np.random.seed(42)
    random.seed(42)
    
    for day in range(730):
        current_date = start_date + timedelta(days=day)
        # Generate between 20 and 50 transactions per day
        num_transactions = np.random.randint(20, 50)
        for _ in range(num_transactions):
            store_id, store_name = random.choice(stores)
            category = random.choice(categories)
            
            # Base price ranges by category
            if category == "Electronics":
                price = round(np.random.uniform(50.0, 1200.0), 2)
            elif category == "Apparel":
                price = round(np.random.uniform(15.0, 150.0), 2)
            elif category == "Home & Kitchen":
                price = round(np.random.uniform(10.0, 300.0), 2)
            elif category == "Groceries":
                price = round(np.random.uniform(2.0, 80.0), 2)
            else:  # Books
                price = round(np.random.uniform(5.0, 45.0), 2)
                
            units = int(np.random.randint(1, 5))
            sales_amount = round(price * units, 2)
            
            gender = np.random.choice(genders, p=[0.45, 0.45, 0.05, 0.05])
            age = int(np.random.normal(38, 12))
            age = max(18, min(80, age))  # clamp age
            
            records.append({
                "transaction_id": len(records) + 1,
                "date": current_date.strftime("%Y-%m-%d"),
                "store_id": store_id,
                "store_name": store_name,
                "product_category": category,
                "unit_price": price,
                "units_sold": units,
                "sales_amount": sales_amount,
                "customer_gender": gender,
                "customer_age": age
            })
            
    df = pl.DataFrame(records)
    output_path = os.path.join(RAW_DIR, "store_sales.parquet")
    df.write_parquet(output_path)
    print(f"Store sales saved to: {output_path} ({df.height} rows)")

def generate_web_metrics():
    print("Generating mock web metrics dataset...")
    # Generate web visitor details for the last 30 days
    start_date = datetime.now() - timedelta(days=30)
    records = []
    
    pages = ["/home", "/products", "/cart", "/checkout", "/blog", "/support"]
    devices = ["Desktop", "Mobile", "Tablet"]
    channels = ["Organic Search", "Direct", "Paid Ads", "Social Media", "Email"]
    
    np.random.seed(42)
    random.seed(42)
    
    total_records = 5000
    for i in range(total_records):
        # Distribute randomly over the last 30 days
        seconds_offset = np.random.randint(0, 30 * 24 * 3600)
        timestamp = start_date + timedelta(seconds=seconds_offset)
        
        visitor_id = f"VIS-{np.random.randint(1000, 9999)}"
        page = np.random.choice(pages, p=[0.35, 0.25, 0.15, 0.05, 0.10, 0.10])
        device = np.random.choice(devices, p=[0.40, 0.50, 0.10])
        channel = np.random.choice(channels, p=[0.30, 0.20, 0.25, 0.15, 0.10])
        
        # Session duration matches page type
        if page == "/checkout":
            duration = round(np.random.exponential(180) + 60, 1)
            bounce = False
        elif page == "/cart":
            duration = round(np.random.exponential(120) + 30, 1)
            bounce = False
        elif page in ["/home", "/products"]:
            duration = round(np.random.exponential(45) + 10, 1)
            bounce = np.random.choice([True, False], p=[0.4, 0.6])
        else:
            duration = round(np.random.exponential(30) + 5, 1)
            bounce = np.random.choice([True, False], p=[0.7, 0.3])
            
        records.append({
            "session_id": f"SESS-{100000 + i}",
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "visitor_id": visitor_id,
            "page_path": page,
            "device": device,
            "traffic_source": channel,
            "session_duration_sec": duration,
            "is_bounce": bounce
        })
        
    df = pl.DataFrame(records)
    # Sort by timestamp
    df = df.sort("timestamp")
    output_path = os.path.join(RAW_DIR, "web_metrics.parquet")
    df.write_parquet(output_path)
    print(f"Web metrics saved to: {output_path} ({df.height} rows)")

if __name__ == "__main__":
    generate_store_sales()
    generate_web_metrics()
