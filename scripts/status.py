#!/usr/bin/env python3
"""
Standalone script: Check pipeline status
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.pipeline import get_orchestrator


def main():
    print("\n" + "=" * 70)
    print("📊 FOOD RECOMMENDATION PIPELINE - STATUS CHECK")
    print("=" * 70 + "\n")
    
    config = Config()
    orchestrator = get_orchestrator(config)
    
    # Configuration info
    config.info()
    
    # File status
    print("\n📁 FILE STATUS:")
    print("-" * 70)
    status = orchestrator.get_status()
    
    files = [
        ("Raw CSV", status["raw_csv_exists"], config.raw_recipe_csv),
        ("Recipes JSON", status["recipes_processed_exists"], config.recipe_file),
        ("KG Payload", status["kg_payload_exists"], config.kg_payload_file),
        ("KG Cypher", status["kg_cypher_exists"], config.kg_cypher_file),
        ("Recommendations", status["recommendations_exist"], config.recommendation_file),
    ]
    
    for name, exists, path in files:
        icon = "✅" if exists else "❌"
        status_text = "EXISTS" if exists else "MISSING"
        print(f"{icon} {name:20} {status_text:10} → {path}")
    
    print("-" * 70 + "\n")
    
    # Recommendations
    print("💡 NEXT STEPS:")
    if not status["recipes_processed_exists"]:
        print("  1. Normalize recipes: python scripts/normalize.py")
    if not status["kg_payload_exists"]:
        print("  2. Build KG: python scripts/build_kg.py")
    if not status["recommendations_exist"]:
        print("  3. Generate recommendations: python scripts/recommend.py")
    
    print()


if __name__ == "__main__":
    main()
