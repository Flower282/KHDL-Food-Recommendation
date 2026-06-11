import json
from pathlib import Path
import sys

# Setup path to import from KG package
current_dir = Path(__file__).resolve().parent
if str(current_dir.parent) not in sys.path:
    sys.path.insert(0, str(current_dir.parent))

try:
    from KG.neo4j_pipeline import payload_to_cypher_commands
except ImportError:
    # Fallback to local import if run differently
    from neo4j_pipeline import payload_to_cypher_commands

def main():
    # Resolve file paths relative to where the script is executed
    payload_path = Path("result/kg_payload.json")
    cypher_path = Path("result/load_kg.cypher")
    
    if not payload_path.exists():
        payload_path = current_dir.parent.parent / "result" / "kg_payload.json"
        cypher_path = current_dir.parent.parent / "result" / "load_kg.cypher"
        
    if not payload_path.exists():
        # Fallback to absolute path
        payload_path = Path("d:/Data_crawl/result/kg_payload.json")
        cypher_path = Path("d:/Data_crawl/result/load_kg.cypher")

    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print(f"Master payload path: {payload_path.resolve()}")
    if not payload_path.exists():
        print(f"Error: File '{payload_path}' does not exist.")
        return

    # Load master payload
    with open(payload_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Deduplicate dish_rows by name
    original_dish_count = len(data.get("dish_rows", []))
    seen_dishes = set()
    unique_dish_rows = []
    
    for dish in data.get("dish_rows", []):
        name = dish.get("name")
        if name and name not in seen_dishes:
            seen_dishes.add(name)
            unique_dish_rows.append(dish)
            
    data["dish_rows"] = unique_dish_rows
    new_dish_count = len(unique_dish_rows)
    removed_dishes = original_dish_count - new_dish_count

    # 2. Filter and deduplicate ingredient_rows
    original_ing_count = len(data.get("ingredient_rows", []))
    seen_ingredients = set()
    unique_ingredient_rows = []
    
    for ing in data.get("ingredient_rows", []):
        dish_name = ing.get("dish_name")
        # Keep ingredients only if the dish is in the deduplicated dishes list
        if dish_name in seen_dishes:
            # Avoid exact duplicate ingredient records (dish_name, ingredient_canonical)
            canonical = ing.get("ingredient_canonical")
            key = (dish_name, canonical)
            if key not in seen_ingredients:
                seen_ingredients.add(key)
                unique_ingredient_rows.append(ing)
                
    data["ingredient_rows"] = unique_ingredient_rows
    new_ing_count = len(unique_ingredient_rows)
    removed_ingredients = original_ing_count - new_ing_count

    # Save the updated payload
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Deduplicated master payload saved to: {payload_path}")

    # Generate and write the Cypher script
    print(f"Generating updated Cypher script: {cypher_path}...")
    try:
        commands = payload_to_cypher_commands(data)
        cypher_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cypher_path, "w", encoding="utf-8") as file:
            file.write("\n".join(commands))
        print(f"Cypher script written to: {cypher_path}")
    except Exception as e:
        print(f"Error generating Cypher script: {e}")

    print("\nSummary of deduplication:")
    print(f"  - Dishes: {original_dish_count} -> {new_dish_count} (Removed {removed_dishes})")
    print(f"  - Ingredients: {original_ing_count} -> {new_ing_count} (Removed {removed_ingredients})")

if __name__ == "__main__":
    main()
