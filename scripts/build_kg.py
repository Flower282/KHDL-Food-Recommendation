#!/usr/bin/env python3
"""
Standalone script: Build Knowledge Graph
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.pipeline import get_orchestrator
from src.ontology import print_ontology


def main():
    print("\n" + "=" * 70)
    print("🏗️  BUILD KNOWLEDGE GRAPH")
    print("=" * 70 + "\n")
    
    config = Config()
    orchestrator = get_orchestrator(config)
    
    # Show ontology
    print_ontology()
    
    print(f"📥 Recipes: {config.recipe_file}")
    print(f"📥 Stock:   {config.stock_file}")
    print(f"📤 KG Payload: {config.kg_payload_file}")
    print(f"📤 Cypher Script: {config.kg_cypher_file}")
    print()
    
    try:
        # Build KG
        payload = orchestrator.step_build_kg()
        
        # Print statistics
        print("\n📊 KG STATISTICS:")
        print("-" * 70)
        print(f"  Dishes:        {len(payload.get('dish_rows', []))}")
        print(f"  Ingredients:   {len(payload.get('ingredient_rows', []))}")
        print(f"  Stock Items:   {len(payload.get('stock_rows', []))}")
        print("-" * 70)
        
        print("\n✅ Knowledge Graph built successfully!")
        print(f"\n📄 Output files created:")
        print(f"  • {config.kg_payload_file}")
        print(f"  • {config.kg_cypher_file}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
