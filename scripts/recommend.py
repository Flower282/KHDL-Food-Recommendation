#!/usr/bin/env python3
"""
Standalone script: Generate recommendations
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.pipeline import get_orchestrator


def main():
    print("\n" + "=" * 70)
    print("🍽️  GENERATE MEAL RECOMMENDATIONS")
    print("=" * 70 + "\n")
    
    config = Config()
    orchestrator = get_orchestrator(config)
    
    # Parse arguments
    top_k = 10
    max_dishes = 3
    
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--top-k" and i + 1 < len(sys.argv) - 1:
            top_k = int(sys.argv[i + 2])
        elif arg == "--max-dishes" and i + 1 < len(sys.argv) - 1:
            max_dishes = int(sys.argv[i + 2])
    
    print(f"📥 Recipes:    {config.recipe_file}")
    print(f"📥 Stock:      {config.stock_file}")
    print(f"⚙️  Top-K:      {top_k}")
    print(f"⚙️  Max Dishes: {max_dishes}")
    print(f"📤 Output:     {config.recommendation_file}")
    print()
    
    try:
        result = orchestrator.step_recommend(top_k=top_k, max_dishes=max_dishes)
        
        # Print recommendations
        if result.get("meal_set"):
            print("\n" + "=" * 70)
            print("🎯 RECOMMENDED MEAL SET:")
            print("=" * 70)
            for i, dish in enumerate(result["meal_set"], 1):
                print(f"\n{i}. {dish['dish_name']}")
                print(f"   Score: {dish['score']:.2f}")
                if dish.get('used_ingredients'):
                    print(f"   Ingredients: {', '.join(dish['used_ingredients'][:5])}")
                    if len(dish['used_ingredients']) > 5:
                        print(f"               ... and {len(dish['used_ingredients']) - 5} more")
                if dish.get('missing_required'):
                    print(f"   Missing: {', '.join(dish['missing_required'])}")
            
            print("\n" + "-" * 70)
            print(f"Total Score: {result.get('total_score', 0):.2f}")
            print("=" * 70)
        
        print("\n✅ Recommendations generated successfully!")
        print(f"📄 Output: {config.recommendation_file}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
