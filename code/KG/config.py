from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RESULT_DIR = PROJECT_ROOT / "result"

DEFAULT_STOCK_FILE = DATA_DIR / "Kho.json"
DEFAULT_RECIPE_FILE = RESULT_DIR / "recipes_processed.json"  # Output from NLP processor

# Neo4j Aura credentials (updated 2026-05-13)
DEFAULT_NEO4J_URI = "neo4j+s://4ed018bf.databases.neo4j.io"
DEFAULT_NEO4J_USER = "4ed018bf"
DEFAULT_NEO4J_PASSWORD = "7he_IgP45assE3vsuO3GpWaxcNVmMxa-3npnUJAm1XM"
DEFAULT_NEO4J_DATABASE = "4ed018bf"
