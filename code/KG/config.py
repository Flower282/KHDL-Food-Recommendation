from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RESULT_DIR = PROJECT_ROOT / "result"

DEFAULT_STOCK_FILE = DATA_DIR / "Kho.json"
DEFAULT_RECIPE_FILE = RESULT_DIR / "data_monan_day_du_CP.json"

# Neo4j Aura credentials (updated 2026-05-13)
DEFAULT_NEO4J_URI = "neo4j+s://2e2fdb07.databases.neo4j.io"
DEFAULT_NEO4J_USER = "2e2fdb07"
DEFAULT_NEO4J_PASSWORD = "bKfubU3XukbxsGJ_6FzojFUWxTZ6EBk0I6lhbT7jLlc"
DEFAULT_NEO4J_DATABASE = "2e2fdb07"
