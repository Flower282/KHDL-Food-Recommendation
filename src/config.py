"""
Food Recommendation System - Core Configuration
"""
from pathlib import Path
from typing import Optional

# Project paths
# __file__ = /path/to/KHDL-Food-Recommendation/src/config.py
# So we need: .parent (src) → .parent (project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULT_DIR = PROJECT_ROOT / "result"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

# Data file paths
DEFAULT_STOCK_FILE = DATA_DIR / "Kho.json"
DEFAULT_RECIPE_FILE = RESULT_DIR / "recipes_processed.json"
DEFAULT_RAW_RECIPE_CSV = RESULT_DIR / "raw_data_CP.csv"
DEFAULT_NLP_OUTPUT_FILE = RESULT_DIR / "recipes_processed.json"

# Neo4j Configuration (from environment or defaults)
DEFAULT_NEO4J_URI = "bolt://localhost:7687"
DEFAULT_NEO4J_USER = "neo4j"
DEFAULT_NEO4J_PASSWORD = "password"
DEFAULT_NEO4J_DATABASE = "neo4j"

# Output files
KG_PAYLOAD_FILE = RESULT_DIR / "kg_payload.json"
KG_CYPHER_FILE = RESULT_DIR / "load_kg.cypher"
RECOMMENDATION_OUTPUT_FILE = RESULT_DIR / "recommendation_kg.json"

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = LOGS_DIR / "pipeline.log"


class Config:
    """Centralized configuration"""
    
    # Paths
    project_root = PROJECT_ROOT
    data_dir = DATA_DIR
    result_dir = RESULT_DIR
    logs_dir = LOGS_DIR
    
    # Neo4j
    neo4j_uri = DEFAULT_NEO4J_URI
    neo4j_user = DEFAULT_NEO4J_USER
    neo4j_password = DEFAULT_NEO4J_PASSWORD
    neo4j_database = DEFAULT_NEO4J_DATABASE
    
    # Files
    stock_file = DEFAULT_STOCK_FILE
    recipe_file = DEFAULT_RECIPE_FILE
    raw_recipe_csv = DEFAULT_RAW_RECIPE_CSV
    kg_payload_file = KG_PAYLOAD_FILE
    kg_cypher_file = KG_CYPHER_FILE
    recommendation_file = RECOMMENDATION_OUTPUT_FILE
    
    @classmethod
    def update_from_dict(cls, config_dict: dict):
        """Update config from dictionary"""
        for key, value in config_dict.items():
            if hasattr(cls, key):
                setattr(cls, key, value)
    
    @classmethod
    def to_dict(cls):
        """Convert config to dictionary"""
        return {
            k: v for k, v in cls.__dict__.items()
            if not k.startswith("_") and not callable(v)
        }
    
    @classmethod
    def info(cls):
        """Print configuration info"""
        print("=" * 60)
        print("📋 PIPELINE CONFIGURATION")
        print("=" * 60)
        print(f"Project Root: {cls.project_root}")
        print(f"Data Dir: {cls.data_dir}")
        print(f"Result Dir: {cls.result_dir}")
        print(f"Logs Dir: {cls.logs_dir}")
        print(f"\nNeo4j URI: {cls.neo4j_uri}")
        print(f"Neo4j Database: {cls.neo4j_database}")
        print(f"Neo4j User: {cls.neo4j_user}")
        print(f"\nRecipe File: {cls.recipe_file}")
        print(f"Stock File: {cls.stock_file}")
        print(f"KG Payload: {cls.kg_payload_file}")
        print("=" * 60)
