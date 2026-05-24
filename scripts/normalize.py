#!/usr/bin/env python3
"""
Standalone script: Normalize recipes from CSV to JSON
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.pipeline import get_orchestrator


def main():
    print("\n" + "=" * 70)
    print("🧹 NORMALIZE RECIPES")
    print("=" * 70 + "\n")
    
    config = Config()
    orchestrator = get_orchestrator(config)
    
    print(f"📥 Input:  {config.raw_recipe_csv}")
    print(f"📤 Output: {config.recipe_file}")
    print()
    
    try:
        orchestrator.step_normalize()
        print("\n✅ Normalization completed successfully!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
