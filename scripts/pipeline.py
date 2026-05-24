#!/usr/bin/env python3
"""
Main Pipeline Orchestrator Script
Run entire workflow: Crawl → Normalize → Build KG → Load Neo4j → Recommend
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.pipeline import get_orchestrator
from src.ontology import print_ontology


def main():
    parser = argparse.ArgumentParser(
        description="Food Recommendation System - Pipeline Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:

  # Check pipeline status
  python scripts/pipeline.py --status
  
  # Normalize recipes only
  python scripts/pipeline.py --normalize
  
  # Build KG payload and Cypher script
  python scripts/pipeline.py --build-kg
  
  # Full pipeline: normalize → build KG → recommend
  python scripts/pipeline.py --normalize --build-kg --recommend
  
  # Full pipeline with Neo4j: normalize → build KG → load Neo4j → recommend
  python scripts/pipeline.py --normalize --build-kg --load-neo4j --recommend \\
      --neo4j-password YOUR_PASSWORD --max-dishes 3
  
  # Just generate recommendations (assumes KG is ready)
  python scripts/pipeline.py --recommend --top-k 15
        """.strip()
    )
    
    # Pipeline steps
    parser.add_argument("--status", action="store_true", help="Show pipeline status")
    parser.add_argument("--crawl", action="store_true", help="Crawl recipe data")
    parser.add_argument("--normalize", action="store_true", help="Normalize recipes to JSON")
    parser.add_argument("--build-kg", action="store_true", help="Build Knowledge Graph payload")
    parser.add_argument("--load-neo4j", action="store_true", help="Load KG into Neo4j")
    parser.add_argument("--recommend", action="store_true", help="Generate recommendations")
    
    # Neo4j options
    parser.add_argument("--neo4j-uri", default=None, help="Neo4j connection URI")
    parser.add_argument("--neo4j-user", default=None, help="Neo4j username")
    parser.add_argument("--neo4j-password", required=False, help="Neo4j password")
    parser.add_argument("--neo4j-database", default=None, help="Neo4j database name")
    parser.add_argument("--clear", action="store_true", help="Clear Neo4j graph before loading")
    
    # Recommendation options
    parser.add_argument("--top-k", type=int, default=10, help="Top dishes to consider (default: 10)")
    parser.add_argument("--max-dishes", type=int, default=3, help="Dishes in meal set (default: 3)")
    
    # File options
    parser.add_argument("--input", default=None, help="Custom input file")
    parser.add_argument("--output", default=None, help="Custom output file")
    
    args = parser.parse_args()
    
    # If no action specified, show status
    if not any([args.status, args.crawl, args.normalize, args.build_kg, 
                args.load_neo4j, args.recommend]):
        args.status = True
    
    config = Config()
    orchestrator = get_orchestrator(config)
    
    print("\n" + "=" * 80)
    print("🚀 FOOD RECOMMENDATION SYSTEM - PIPELINE ORCHESTRATOR")
    print("=" * 80 + "\n")
    
    try:
        # Status
        if args.status:
            print("📊 PIPELINE STATUS:")
            print("-" * 80)
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
                print(f"{icon} {name:20} → {path}")
            print("-" * 80 + "\n")
        
        # Run requested steps
        if args.normalize or args.build_kg or args.load_neo4j or args.recommend:
            print_ontology()
            orchestrator.run_full_pipeline(
                crawl=args.crawl,
                normalize=args.normalize,
                build_kg=args.build_kg,
                load_neo4j=args.load_neo4j,
                recommend=args.recommend,
                neo4j_clear=args.clear,
                neo4j_uri=args.neo4j_uri,
                neo4j_user=args.neo4j_user,
                neo4j_password=args.neo4j_password,
                neo4j_database=args.neo4j_database,
                top_k=args.top_k,
                max_dishes=args.max_dishes,
            )
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
