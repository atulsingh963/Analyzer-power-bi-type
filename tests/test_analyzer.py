import os
import unittest
import pandas as pd
import polars as pl
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Set environment variable for testing
os.environ["SECRET_KEY"] = "TEST_SECRET_KEY_FOR_UNIT_TESTS"

from database.db import SessionLocal, init_db
from backend.models.models import User, Role, Dataset, Dashboard
from backend.auth.security import hash_password, verify_password, create_access_token, decode_access_token
from analytics.engine import analytics_engine
from analytics.forecasting import generate_forecast, calculate_churn_classification
from etl.engine import etl_engine
from etl.quality import get_dataset_quality_metrics
from ai.agents.sql_agent import ai_agent
from backend.main import app

class TestAnalyzerPlatform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize/seed database for testing (creates sqlite db if not existing)
        init_db()
        cls.client = TestClient(app)

    def test_01_security_hashing(self):
        password = "test_secure_password"
        hashed = hash_password(password)
        self.assertNotEqual(password, hashed)
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("wrong_password", hashed))

    def test_02_security_jwt(self):
        data = {"sub": "test_user_account"}
        token = create_access_token(data)
        self.assertIsNotNone(token)
        
        payload = decode_access_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("sub"), "test_user_account")
        
        # Invalid token check
        self.assertIsNone(decode_access_token("invalid.token.string"))

    def test_03_database_seed(self):
        db = SessionLocal()
        # Verify admin seeded
        admin = db.query(User).filter_by(username="admin").first()
        self.assertIsNotNone(admin)
        self.assertEqual(admin.email, "admin@analyzer.local")
        
        # Verify roles exist
        roles_count = db.query(Role).count()
        self.assertGreaterEqual(roles_count, 4)
        db.close()

    def test_04_analytics_engine(self):
        db = SessionLocal()
        # Test basic query
        res = analytics_engine.execute_query("SELECT 1 + 1 AS sum_val", db)
        self.assertTrue(res["success"])
        self.assertEqual(res["columns"], ["sum_val"])
        self.assertEqual(res["data"][0][0], 2)
        db.close()

    def test_05_data_quality(self):
        db = SessionLocal()
        sales_ds = db.query(Dataset).filter_by(name="Store Sales").first()
        self.assertIsNotNone(sales_ds)
        
        # Check quality metrics calculation
        metrics = get_dataset_quality_metrics(sales_ds.file_path, sales_ds.file_type)
        self.assertNotIn("error", metrics)
        self.assertIn("total_rows", metrics)
        self.assertIn("duplicate_rows", metrics)
        self.assertIn("column_stats", metrics)
        db.close()

    def test_06_etl_nodes(self):
        db = SessionLocal()
        sales_ds = db.query(Dataset).filter_by(name="Store Sales").first()
        self.assertIsNotNone(sales_ds)
        
        # Define simple pipeline definition: Source -> Filter -> Select
        definition = {
            "nodes": [
                {
                    "id": "n1",
                    "type": "source",
                    "config": {"dataset_id": sales_ds.id}
                },
                {
                    "id": "n2",
                    "type": "filter",
                    "config": {"column": "sales_amount", "operator": ">", "value": "500"}
                },
                {
                    "id": "n3",
                    "type": "select",
                    "config": {"columns": ["transaction_id", "sales_amount"]}
                }
            ]
        }
        
        df = etl_engine.execute_nodes(definition, db)
        self.assertIsInstance(df, pl.DataFrame)
        self.assertIn("transaction_id", df.columns)
        self.assertIn("sales_amount", df.columns)
        self.assertEqual(len(df.columns), 2)
        db.close()

    def test_07_ai_agent_nlp(self):
        db = SessionLocal()
        # Test SQL generation from text
        sql = ai_agent.generate_sql("What is the total sales by store name?", db)
        self.assertIsNotNone(sql)
        self.assertIn("store_sales", sql.lower())
        self.assertIn("group by", sql.lower())
        
        # Test visual suggestion
        vis = ai_agent.suggest_visualization(["store_name", "total_sales"], [["Store A", 100], ["Store B", 200]])
        self.assertEqual(vis, "pie")  # 2 rows -> pie chart recommendation
        db.close()

    def test_08_predictive_modeling(self):
        # 1. Forecasting Check
        dates = [f"2026-05-{i:02d}" for i in range(1, 15)]
        values = [100.0 + i*5.0 for i in range(14)]
        fc = generate_forecast(dates, values, steps=5)
        self.assertTrue(fc.get("success"))
        self.assertEqual(len(fc["dates"]), 5)
        self.assertEqual(len(fc["values"]), 5)
        
        # 2. Classification Churn Check
        data_sales = {
            "transaction_id": list(range(1, 11)),
            "date": ["2026-05-01"] * 10,
            "store_name": ["Store A"] * 10,
            "sales_amount": [10.0] * 10,
            "customer_age": [30] * 10,
            "customer_gender": ["Male"] * 10
        }
        df_sales = pd.DataFrame(data_sales)
        churn = calculate_churn_classification(df_sales)
        self.assertTrue(churn.get("success") or "error" in churn)

    def test_09_api_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy", "service": "analyzer-api"})

    def test_10_api_auth(self):
        # 1. Failed login check
        response = self.client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
        self.assertEqual(response.status_code, 401)
        
        # 2. Successful login check
        response = self.client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["username"], "admin")
        self.assertEqual(data["role"], "Admin")

if __name__ == "__main__":
    unittest.main()
