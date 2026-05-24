"""
Main CLI entry point for pipeline control
"""
import logging
import sys
from pathlib import Path
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)

from src.config import Config
from src.pipeline import get_orchestrator


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║       🍜 FOOD RECOMMENDATION SYSTEM - PIPELINE CONTROL 🍜   ║
║                    v1.0 - Refactored                        ║
╚══════════════════════════════════════════════════════════════╝
    """)


def print_commands():
    """Print available commands"""
    commands = """
AVAILABLE COMMANDS:
  
  1. Status
     python -m src.main status
     → Check pipeline status & file existence
  
  2. Config
     python -m src.main config
     → Show current configuration
  
  3. Normalize
     python -m src.main normalize [--input INPUT] [--output OUTPUT]
     → Process CSV to normalized JSON recipes
  
  4. Build KG
     python -m src.main build-kg [--recipes RECIPES]
     → Build Knowledge Graph payload
  
  5. Load Neo4j
     python -m src.main load-neo4j [--uri URI] [--user USER] [--password PASS] [--clear]
     → Load KG into Neo4j database
  
  6. Recommend
     python -m src.main recommend [--top-k 10] [--max-dishes 3]
     → Generate meal recommendations
  
  7. Full Pipeline
     python -m src.main pipeline [--crawl] [--normalize] [--build-kg] [--load-neo4j] [--recommend]
     → Run complete pipeline with selected steps
  
EXAMPLES:
  
  # Check what's available
  python -m src.main status
  
  # Just process recipes to JSON
  python -m src.main normalize
  
  # Build KG and show structure
  python -m src.main build-kg
  
  # Run full pipeline (crawl, normalize, build KG, recommend)
  python -m src.main pipeline --crawl --normalize --build-kg --recommend
  
  # Load into Neo4j and generate recommendations
  python -m src.main pipeline --build-kg --load-neo4j --recommend \\
      --neo4j-password YOUR_PASSWORD --max-dishes 3
    """.strip()
    print(commands)


def main():
    """Main CLI interface"""
    print_banner()
    
    if len(sys.argv) < 2:
        print_commands()
        sys.exit(0)
    
    command = sys.argv[1]
    config = Config()
    orchestrator = get_orchestrator(config)
    
    try:
        if command == "status":
            # Show pipeline status
            print("\n📊 PIPELINE STATUS:")
            print("=" * 60)
            status = orchestrator.get_status()
            for key, value in status.items():
                if key != "config":
                    status_icon = "✅" if value else "❌"
                    print(f"{status_icon} {key:30} {value}")
            print("=" * 60)
        
        elif command == "config":
            # Show configuration
            config.info()
        
        elif command == "normalize":
            # Normalize recipes
            orchestrator.step_normalize()
        
        elif command == "build-kg":
            # Build KG
            orchestrator.step_build_kg()
            print(f"\n📄 KG Payload: {config.kg_payload_file}")
            print(f"💾 Cypher Script: {config.kg_cypher_file}")
        
        elif command == "load-neo4j":
            # Load to Neo4j
            uri = next((sys.argv[sys.argv.index(arg) + 1] for i, arg in enumerate(sys.argv) 
                       if arg == "--uri"), config.neo4j_uri)
            user = next((sys.argv[sys.argv.index(arg) + 1] for i, arg in enumerate(sys.argv) 
                        if arg == "--user"), config.neo4j_user)
            password = next((sys.argv[sys.argv.index(arg) + 1] for i, arg in enumerate(sys.argv) 
                            if arg == "--password"), None)
            clear = "--clear" in sys.argv
            
            if not password:
                print("❌ Error: --password required for Neo4j")
                sys.exit(1)
            
            orchestrator.step_load_to_neo4j(
                uri=uri, user=user, password=password, clear=clear
            )
        
        elif command == "recommend":
            # Generate recommendations
            top_k = int(next((sys.argv[sys.argv.index(arg) + 1] for i, arg in enumerate(sys.argv) 
                             if arg == "--top-k"), 10))
            max_dishes = int(next((sys.argv[sys.argv.index(arg) + 1] for i, arg in enumerate(sys.argv) 
                                  if arg == "--max-dishes"), 3))
            
            result = orchestrator.step_recommend(top_k=top_k, max_dishes=max_dishes)
        
        elif command == "pipeline":
            # Run full pipeline
            crawl = "--crawl" in sys.argv
            normalize = "--normalize" in sys.argv or (not any(f in sys.argv for f in ["--build-kg", "--load-neo4j", "--recommend"]))
            build_kg = "--build-kg" in sys.argv or (not any(f in sys.argv for f in ["--build-kg", "--load-neo4j", "--recommend"]))
            load_neo4j = "--load-neo4j" in sys.argv
            recommend = "--recommend" in sys.argv or (not any(f in sys.argv for f in ["--build-kg", "--load-neo4j", "--recommend"]))
            neo4j_clear = "--clear" in sys.argv
            
            # Extract parameters
            kwargs = {}
            for i, arg in enumerate(sys.argv[2:], 2):
                if arg.startswith("--") and "=" not in arg and i + 1 < len(sys.argv):
                    next_arg = sys.argv[i + 1]
                    if not next_arg.startswith("--"):
                        key = arg.lstrip("--").replace("-", "_")
                        kwargs[key] = next_arg
            
            orchestrator.run_full_pipeline(
                crawl=crawl,
                normalize=normalize,
                build_kg=build_kg,
                load_neo4j=load_neo4j,
                recommend=recommend,
                neo4j_clear=neo4j_clear,
                **kwargs
            )
        
        elif command == "help" or command in ["-h", "--help"]:
            print_commands()
        
        else:
            print(f"❌ Unknown command: {command}")
            print("\nRun 'python -m src.main help' for available commands")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
