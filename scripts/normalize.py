#!/usr/bin/env python3
"""
Standalone script: Normalize recipes from CSV to JSON
Scans rawCSV folder for CSV files and outputs to normalized folder
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.pipeline import get_orchestrator


def find_csv_files(folder: Path) -> list[Path]:
    """Find all CSV files in a folder"""
    if not folder.exists():
        return []
    return sorted(folder.glob("*.csv"))


def get_output_path(input_file: Path, output_dir: Path) -> Path:
    """Convert input CSV to output JSON path"""
    json_filename = input_file.stem + ".json"
    return output_dir / json_filename


def main():
    parser = argparse.ArgumentParser(
        description="Normalize recipes from CSV to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode - scan rawCSV/ folder
  python scripts/normalize.py
  
  # Specify custom input file
  python scripts/normalize.py -i rawCSV/recipes.csv
  
  # Specify custom input and output folder
  python scripts/normalize.py -i rawCSV/recipes.csv -o custom_output/
  
  # Process all CSV files in rawCSV/
  python scripts/normalize.py --batch
        """
    )
    
    parser.add_argument(
        "-i", "--input",
        type=str,
        default=None,
        help="Input CSV file path (scans rawCSV/ by default)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default=None,
        help="Output directory for JSON files (default: normalized/)"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Batch mode - process all CSV files in rawCSV/ folder"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("🧹 NORMALIZE RECIPES")
    print("=" * 70 + "\n")
    
    config = Config()
    project_root = Path(config.project_root)
    raw_csv_dir = project_root / "rawCSV"
    normalized_dir = Path(args.output_dir) if args.output_dir else (project_root / "normalized")
    
    # Create output directory if it doesn't exist
    normalized_dir.mkdir(parents=True, exist_ok=True)
    print(f"📂 Output directory: {normalized_dir}\n")
    
    # Find CSV files
    if args.input:
        # Specific input file
        input_file = Path(args.input)
        if not input_file.exists():
            print(f"❌ Error: Input file not found: {input_file}")
            sys.exit(1)
        csv_files = [input_file]
    else:
        # Scan rawCSV folder
        csv_files = find_csv_files(raw_csv_dir)
        
        if not csv_files:
            print(f"❌ No CSV files found in {raw_csv_dir}")
            sys.exit(1)
        
        print(f"📁 Found {len(csv_files)} CSV file(s) in rawCSV/:\n")
        for idx, file in enumerate(csv_files, 1):
            print(f"  {idx}. {file.name}")
    
    # Batch mode or interactive selection
    if args.batch:
        selected_files = csv_files
    else:
        if len(csv_files) == 1:
            selected_files = csv_files
            print(f"\n✓ Using: {csv_files[0].name}")
        else:
            print()
            while True:
                try:
                    choice_input = input(f"Select file(s) to process (e.g., 1 or 1,2,3 or 'all'): ").strip().lower()
                    
                    if choice_input == 'all':
                        selected_files = csv_files
                        break
                    else:
                        indices = [int(x.strip()) - 1 for x in choice_input.split(",")]
                        if all(0 <= i < len(csv_files) for i in indices):
                            selected_files = [csv_files[i] for i in indices]
                            break
                        else:
                            print(f"❌ Please enter valid number(s) between 1 and {len(csv_files)}")
                except (ValueError, IndexError):
                    print(f"❌ Invalid input. Please enter numbers separated by commas")
    
    # Process files
    print(f"\n{'=' * 70}\n")
    
    orchestrator = get_orchestrator(config)
    
    for input_file in selected_files:
        output_file = get_output_path(input_file, normalized_dir)
        
        print(f"📥 Input:  {input_file}")
        print(f"📤 Output: {output_file}")
        print()
        
        # Update config with current paths
        config.raw_recipe_csv = input_file
        config.recipe_file = output_file
        
        try:
            orchestrator.step_normalize()
            print(f"✅ Completed: {output_file.name}\n")
        except Exception as e:
            print(f"❌ Error processing {input_file.name}: {e}\n")
            sys.exit(1)
    
    print("=" * 70)
    print(f"✅ All files normalized successfully!")
    print(f"📂 Output folder: {normalized_dir}")


if __name__ == "__main__":
    main()
