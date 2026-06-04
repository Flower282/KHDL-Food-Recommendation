#!/usr/bin/env python3
"""
Standalone script: Build Knowledge Graph
"""
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.pipeline import get_orchestrator
from src.ontology import print_ontology


def find_json_files(folder: Path) -> list[Path]:
    """Find all JSON files in a folder"""
    if not folder.exists():
        return []
    return sorted(folder.glob("*.json"))


def main():
    parser = argparse.ArgumentParser(
        description="Build Knowledge Graph from recipe JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode - scan normalized/ folder
  python scripts/build_kg.py
  
  # Specify custom recipe file
  python scripts/build_kg.py -r normalized/afamily.json
  
  # Specify custom recipe and stock files
  python scripts/build_kg.py -r normalized/afamily.json -s data/Kho.json
  
  # Batch mode - process all JSON files in normalized/
  python scripts/build_kg.py --batch
        """
    )
    
    parser.add_argument(
        "-r", "--recipe",
        type=str,
        default=None,
        help="Input recipe JSON file (scans normalized/ by default)"
    )
    parser.add_argument(
        "-s", "--stock",
        type=str,
        default=None,
        help="Input stock JSON file (default: data/Kho.json)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default=None,
        help="Output directory for KG files (default: result/)"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Batch mode - process all JSON files in normalized/"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("🏗️  BUILD KNOWLEDGE GRAPH")
    print("=" * 70 + "\n")
    
    config = Config()
    project_root = Path(config.project_root)
    normalized_dir = project_root / "normalized"
    
    # Handle recipe file selection
    if args.recipe:
        recipe_file = Path(args.recipe)
        if not recipe_file.exists():
            print(f"❌ Error: Recipe file not found: {recipe_file}")
            sys.exit(1)
        json_files = [recipe_file]
    else:
        json_files = find_json_files(normalized_dir)
        if not json_files:
            print(f"❌ No JSON files found in {normalized_dir}")
            sys.exit(1)
        
        print(f"📁 Found {len(json_files)} JSON file(s) in normalized/:\n")
        for idx, file in enumerate(json_files, 1):
            print(f"  {idx}. {file.name}")
        
        # Interactive selection
        if not args.batch:
            print()
            if len(json_files) == 1:
                selected_file = json_files[0]
                print(f"✓ Using: {json_files[0].name}")
            else:
                while True:
                    try:
                        choice = input(f"\nSelect file to process (1-{len(json_files)}): ").strip()
                        idx = int(choice) - 1
                        if 0 <= idx < len(json_files):
                            selected_file = json_files[idx]
                            break
                        else:
                            print(f"❌ Please enter a number between 1 and {len(json_files)}")
                    except ValueError:
                        print(f"❌ Please enter a valid number")
            json_files = [selected_file]
    
    # Handle stock file
    stock_file = Path(args.stock) if args.stock else (project_root / "data" / "Kho.json")
    if not stock_file.exists():
        print(f"⚠️  Warning: Stock file not found: {stock_file}")
        print(f"   Proceeding without stock data...\n")
    
    # Handle output directory
    output_dir = Path(args.output_dir) if args.output_dir else (project_root / "result")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'=' * 70}\n")
    
    # Show ontology
    print_ontology()
    
    # Process recipe files
    for recipe_file in json_files:
        print(f"📥 Recipe: {recipe_file}")
        print(f"📥 Stock:  {stock_file}")
        print()
        
        # Update config with current paths
        config.recipe_file = recipe_file
        config.stock_file = stock_file
        config.kg_payload_file = output_dir / f"{recipe_file.stem}_kg_payload.json"
        config.kg_cypher_file = output_dir / f"{recipe_file.stem}_kg.cypher"
        
        try:
            orchestrator = get_orchestrator(config)
            
            # Build KG
            payload = orchestrator.step_build_kg()
            
            # Print statistics
            print("📊 KG STATISTICS:")
            print("-" * 70)
            print(f"  Dishes:        {len(payload.get('dish_rows', []))}")
            print(f"  Ingredients:   {len(payload.get('ingredient_rows', []))}")
            print(f"  Stock Items:   {len(payload.get('stock_rows', []))}")
            print("-" * 70)
            
            print(f"\n✅ Knowledge Graph built successfully!")
            print(f"\n📄 Output files created:")
            print(f"  • {config.kg_payload_file}")
            print(f"  • {config.kg_cypher_file}\n")
            
        except Exception as e:
            print(f"\n❌ Error processing {recipe_file.name}: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
