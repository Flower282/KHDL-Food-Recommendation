from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    current_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(current_dir.parent))

    from KG.config import DEFAULT_RECIPE_FILE, DEFAULT_STOCK_FILE  # type: ignore
    from KG.neo4j_pipeline import Neo4jKnowledgeGraph, build_kg_payload, payload_to_cypher_commands, merge_payloads  # type: ignore
    from KG.ontology import ONTOLOGY_NODES, ONTOLOGY_RELATIONS  # type: ignore
    from KG.recommender import load_and_recommend  # type: ignore
else:
    from .config import DEFAULT_RECIPE_FILE, DEFAULT_STOCK_FILE
    from .neo4j_pipeline import Neo4jKnowledgeGraph, build_kg_payload, payload_to_cypher_commands, merge_payloads
    from .ontology import ONTOLOGY_NODES, ONTOLOGY_RELATIONS
    from .recommender import load_and_recommend


def _print_ontology() -> None:
    print("=== Ontology Nodes ===")
    for node in ONTOLOGY_NODES:
        print(f"- {node.label} ({node.key_property}): {node.description}")

    print("\n=== Ontology Relations ===")
    for rel in ONTOLOGY_RELATIONS:
        print(f"- ({rel.from_label})-[:{rel.relation}]->({rel.to_label}): {rel.description}")


def _dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def command_export(args: argparse.Namespace) -> None:
    print(f"📖 Using recipe file: {args.recipe_file}")
    print(f"📖 Using stock file: {args.stock_file}\n")
    
    payload = build_kg_payload(args.recipe_file, args.stock_file)
    commands = payload_to_cypher_commands(payload)

    _dump_json(Path(args.payload_output), payload)

    cypher_path = Path(args.cypher_output)
    cypher_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cypher_path, "w", encoding="utf-8") as file:
        file.write("\n".join(commands))

    _print_ontology()
    print(f"\nPayload written to: {args.payload_output}")
    print(f"Cypher script written to: {args.cypher_output}")


def command_merge(args: argparse.Namespace) -> None:
    # 1. Resolve path of new recipe file (prompt user if not provided)
    new_recipe_file = args.new_recipe_file
    if not new_recipe_file:
        try:
            new_recipe_file = input("Nhập đường dẫn file JSON mới: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            return

    if not new_recipe_file:
        print("❌ Error: Path of the new recipe file cannot be empty.")
        return

    new_path = Path(new_recipe_file)
    if not new_path.exists():
        print(f"❌ Error: File '{new_path}' does not exist.")
        return

    # 2. Load the main payload (default payload path is args.payload_output)
    main_payload_path = Path(args.payload_output)
    print(f"📖 Master payload path: {main_payload_path}")
    
    if main_payload_path.exists():
        try:
            with open(main_payload_path, "r", encoding="utf-8") as f:
                main_payload = json.load(f)
            print(f"Loaded existing master payload with:")
            print(f"  - {len(main_payload.get('dish_rows', []))} dishes")
            print(f"  - {len(main_payload.get('ingredient_rows', []))} ingredients")
        except Exception as e:
            print(f"⚠️ Error reading master payload: {e}. Starting with an empty payload.")
            main_payload = {
                "dish_rows": [],
                "ingredient_rows": [],
                "stock_rows": [],
                "stock_mapping_rows": [],
            }
    else:
        print("ℹ️ Master payload file does not exist yet. Starting with a new payload.")
        main_payload = {
            "dish_rows": [],
            "ingredient_rows": [],
            "stock_rows": [],
            "stock_mapping_rows": [],
        }

    # 3. Build the child payload from the new file
    print(f"📖 Processing new recipe file: {new_path}")
    print(f"📖 Using stock file: {args.stock_file}")
    
    try:
        child_payload = build_kg_payload(new_path, args.stock_file)
        # Update source name for child dishes to be the basename of new file
        for dish in child_payload.get("dish_rows", []):
            dish["source"] = new_path.name
    except Exception as e:
        print(f"❌ Error building child payload: {e}")
        return

    # 4. Merge payloads
    print(f"🔄 Merging payloads (similarity threshold = {args.threshold})...")
    merged_payload, num_merged, num_added = merge_payloads(
        main_payload, child_payload, threshold=args.threshold
    )

    # 5. Save the updated main payload
    _dump_json(main_payload_path, merged_payload)
    print(f"✅ Master payload saved to: {main_payload_path}")
    print(f"Summary of merge:")
    print(f"  - Dishes merged (updated): {num_merged}")
    print(f"  - New dishes added: {num_added}")
    print(f"  - Total dishes now: {len(merged_payload.get('dish_rows', []))}")

    # 6. Generate and write the Cypher script
    cypher_path = Path(args.cypher_output)
    print(f"🔄 Generating updated Cypher script: {cypher_path}...")
    try:
        commands = payload_to_cypher_commands(merged_payload)
        cypher_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cypher_path, "w", encoding="utf-8") as file:
            file.write("\n".join(commands))
        print(f"✅ Cypher script written to: {cypher_path}")
    except Exception as e:
        print(f"⚠️ Error generating Cypher script: {e}")


def command_load_neo4j(args: argparse.Namespace) -> None:
    payload = build_kg_payload(args.recipe_file, args.stock_file)

    graph = Neo4jKnowledgeGraph(
        uri=args.uri,
        user=args.user,
        password=args.password,
        database=args.database,
    )

    try:
        if args.clear:
            graph.clear_graph()
        graph.create_schema()
        graph.load_payload(payload)
    finally:
        graph.close()

    print("Data loaded into Neo4j successfully.")


def command_recommend(args: argparse.Namespace) -> None:
    result = load_and_recommend(
        recipe_path=args.recipe_file,
        stock_path=args.stock_file,
        top_k=args.top_k,
        max_dishes=args.max_dishes,
        dish_type_filter=args.dish_type,
        required_types=args.required_type,
        max_minutes=args.max_minutes,
    )

    _dump_json(Path(args.output), result)

    print(f"Recommendation output written to: {args.output}")
    print("\nTop dishes:")
    for row in result["top_dishes"]:
        print(f"- {row['dish_name']}: score={row['score']} missing_required={row['missing_required']}")

    print("\nSelected meal set:")
    for row in result["meal_set"]:
        print(f"- {row['dish_name']}: score={row['score']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recipe Knowledge Graph pipeline",
        epilog="""
Examples:
  # Export using default recipe file (recipes_processed.json)
  python3 code/KG/run_pipeline.py export

  # Export using custom recipe file
  python3 code/KG/run_pipeline.py export --recipe-file result/your_recipes.json

  # Load into Neo4j
  python3 code/KG/run_pipeline.py load-neo4j --password YOUR_PASSWORD

  # Get recommendations
  python3 code/KG/run_pipeline.py recommend --max-dishes 3
        """
    )

    parser.add_argument(
        "--recipe-file",
        default=str(DEFAULT_RECIPE_FILE),
        help=f"Path to recipe JSON file (default: {DEFAULT_RECIPE_FILE})"
    )
    parser.add_argument(
        "--stock-file",
        default=str(DEFAULT_STOCK_FILE),
        help=f"Path to stock JSON file (default: {DEFAULT_STOCK_FILE})"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    export_cmd = subparsers.add_parser("export", help="Export payload and Cypher commands")
    export_cmd.add_argument(
        "--payload-output",
        default="result/kg_payload.json",
        help="Output path for payload JSON",
    )
    export_cmd.add_argument(
        "--cypher-output",
        default="result/load_kg.cypher",
        help="Output path for Cypher script",
    )
    export_cmd.set_defaults(func=command_export)

    merge_cmd = subparsers.add_parser("merge", help="Merge a new recipe JSON file incrementally into the master payload")
    merge_cmd.add_argument(
        "--new-recipe-file",
        default=None,
        help="Path to the new recipe JSON file to merge. If not provided, you will be prompted."
    )
    merge_cmd.add_argument(
        "--payload-output",
        default="result/kg_payload.json",
        help="Path to the master payload JSON file (default: result/kg_payload.json)",
    )
    merge_cmd.add_argument(
        "--cypher-output",
        default="result/load_kg.cypher",
        help="Output path for the updated Cypher script (default: result/load_kg.cypher)",
    )
    merge_cmd.add_argument(
        "--threshold",
        type=float,
        default=0.8,
        help="Similarity threshold for merging dishes (default: 0.8)",
    )
    merge_cmd.set_defaults(func=command_merge)

    load_cmd = subparsers.add_parser("load-neo4j", help="Load KG payload into Neo4j")
    load_cmd.add_argument("--uri", default="bolt://localhost:7687", help="Neo4j URI")
    load_cmd.add_argument("--user", default="neo4j", help="Neo4j user")
    load_cmd.add_argument("--password", required=True, help="Neo4j password")
    load_cmd.add_argument("--database", default="neo4j", help="Neo4j database")
    load_cmd.add_argument("--clear", action="store_true", help="Clear existing graph before load")
    load_cmd.set_defaults(func=command_load_neo4j)

    rec_cmd = subparsers.add_parser("recommend", help="Run recommendation algorithm")
    rec_cmd.add_argument("--top-k", type=int, default=10, help="Top dishes to keep")
    rec_cmd.add_argument("--max-dishes", type=int, default=3, help="Number of dishes in final meal set")
    rec_cmd.add_argument("--max-minutes", type=int, default=None, help="Optional maximum cooking time in minutes")
    rec_cmd.add_argument("--dish-type", default=None, help="Optional dish type filter such as mon man, canh, rau")
    rec_cmd.add_argument(
        "--required-type",
        action="append",
        default=[],
        help="Repeatable required type for meal-set coverage, e.g. --required-type canh --required-type rau",
    )
    rec_cmd.add_argument(
        "--output",
        default="result/recommendation_kg.json",
        help="Recommendation output path",
    )
    rec_cmd.set_defaults(func=command_recommend)

    return parser


def main() -> None:
    import sys
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
