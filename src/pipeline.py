"""
Pipeline Module - Orchestrate the entire workflow
"""
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from src.config import Config
from src.ontology import print_ontology

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Main orchestrator for the food recommendation pipeline"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def step_crawl(self, source: str = "CP"):
        """
        Step 1: Crawl recipe data from source
        
        Args:
            source: "CP" (Cookpad), "MNMN" (Mon Ngon Moi Ngay), "MAGGI", "KNORR", or "MAGGI_KNORR" for both.
        """
        self.logger.info(f"🕷️  Step 1: Crawling recipes from {source}")
        
        source_key = source.strip().upper()
        if source_key == "CP":
            from code.Crawl.data_crawl_CP import crawl as crawl_cp
            crawl_cp()
        elif source_key == "MNMN":
            from code.Crawl.data_crawl_MNMN import crawl as crawl_mnmn
            crawl_mnmn()
        elif source_key == "MAGGI":
            from code.Crawl.data_crawl_maggi_knorr import crawl_maggi_listing
            crawl_maggi_listing()
        elif source_key == "KNORR":
            from code.Crawl.data_crawl_maggi_knorr import KNORR_BASE, crawl_knorr_listing
            crawl_knorr_listing(KNORR_BASE)
        elif source_key in {"MAGGI_KNORR", "ALL", "DEFAULT"}:
            from code.Crawl.data_crawl_maggi_knorr import crawl_default
            crawl_default()
        else:
            raise ValueError(f"Unknown source: {source}")
        
        self.logger.info(f"✅ Crawling completed")
        return self.config.raw_recipe_csv
    
    def step_normalize(self, input_csv: Optional[Path] = None, output_json: Optional[Path] = None):
        """
        Step 2: Normalize recipe data
        
        Args:
            input_csv: Path to raw CSV file. If None, uses default
            output_json: Path to output JSON file. If None, uses config.recipe_file
        """
        self.logger.info("🧹 Step 2: Normalizing recipe data")
        input_file = input_csv or self.config.raw_recipe_csv
        
        # Import from nlp-processor folder
        import sys
        project_root = Path(__file__).parent.parent
        nlp_processor_path = project_root / "nlp-processor"
        
        # Add nlp-processor to path
        if str(nlp_processor_path) not in sys.path:
            sys.path.insert(0, str(nlp_processor_path))
        
        # Import from nlp_processor.py (file renamed from nlp-processor.py)
        from nlp_processor.nlp_processor import process_csv
        
        # Allow custom output path
        if output_json:
            output_file = output_json
        else:
            output_file = self.config.recipe_file
        
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        process_csv(str(input_file), str(output_file))
        self.logger.info(f"✅ Normalization completed → {output_file}")
        return output_file
    
    def step_build_kg(self, recipe_file: Optional[Path] = None):
        """
        Step 3: Build Knowledge Graph payload
        
        Args:
            recipe_file: Path to recipes JSON. If None, uses default
        """
        self.logger.info("🏗️  Step 3: Building Knowledge Graph")
        recipe_file = recipe_file or self.config.recipe_file
        
        from code.KG.neo4j_pipeline import build_kg_payload, payload_to_cypher_commands
        
        # Build payload
        payload = build_kg_payload(recipe_file, self.config.stock_file)
        
        # Save payload
        import json
        self.config.kg_payload_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config.kg_payload_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        
        # Generate Cypher commands
        commands = payload_to_cypher_commands(payload)
        with open(self.config.kg_cypher_file, "w", encoding="utf-8") as f:
            f.write("\n".join(commands))
        
        self.logger.info(f"✅ KG built → {self.config.kg_payload_file}")
        return payload
    
    def step_load_to_neo4j(self, uri: Optional[str] = None, 
                          user: Optional[str] = None,
                          password: Optional[str] = None,
                          database: Optional[str] = None,
                          clear: bool = False):
        """
        Step 4: Load KG into Neo4j
        
        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
            database: Neo4j database name
            clear: Whether to clear existing graph
        """
        self.logger.info("📤 Step 4: Loading KG into Neo4j")
        
        from code.KG.neo4j_pipeline import Neo4jKnowledgeGraph, build_kg_payload
        
        uri = uri or self.config.neo4j_uri
        user = user or self.config.neo4j_user
        password = password or self.config.neo4j_password
        database = database or self.config.neo4j_database
        
        graph = Neo4jKnowledgeGraph(uri=uri, user=user, password=password, database=database)
        
        try:
            if clear:
                self.logger.warning("🗑️  Clearing existing graph")
                graph.clear_graph()
            
            self.logger.info("📝 Creating schema")
            graph.create_schema()
            
            # Load payload
            payload = build_kg_payload(self.config.recipe_file, self.config.stock_file)
            self.logger.info(f"💾 Loading {len(payload['dish_rows'])} dishes")
            graph.load_payload(payload)
            
            self.logger.info("✅ KG loaded into Neo4j")
        finally:
            graph.close()
    
    def step_recommend(self, stock_file: Optional[Path] = None,
                      top_k: int = 10, max_dishes: int = 3) -> Dict[str, Any]:
        """
        Step 5: Generate recommendations
        
        Args:
            stock_file: Path to stock file
            top_k: Number of top dishes to consider
            max_dishes: Number of dishes in final meal set
            
        Returns:
            Recommendation result dictionary
        """
        self.logger.info("🍽️  Step 5: Generating recommendations")
        
        from code.KG.recommender import load_and_recommend
        
        stock_file = stock_file or self.config.stock_file
        
        result = load_and_recommend(
            recipe_path=self.config.recipe_file,
            stock_path=stock_file,
            top_k=top_k,
            max_dishes=max_dishes,
        )
        
        # Save result
        import json
        self.config.recommendation_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config.recommendation_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"✅ Recommendations generated → {self.config.recommendation_file}")
        return result
    
    def run_full_pipeline(self, crawl: bool = False, 
                         normalize: bool = True,
                         build_kg: bool = True,
                         load_neo4j: bool = False,
                         recommend: bool = True,
                         neo4j_clear: bool = False,
                         **kwargs):
        """
        Run the complete pipeline
        
        Args:
            crawl: Whether to crawl new data
            normalize: Whether to normalize recipes
            build_kg: Whether to build KG payload
            load_neo4j: Whether to load into Neo4j
            recommend: Whether to generate recommendations
            neo4j_clear: Whether to clear Neo4j before loading
            **kwargs: Additional arguments for each step
        """
        self.logger.info("\n" + "=" * 60)
        self.logger.info("🚀 STARTING FOOD RECOMMENDATION PIPELINE")
        self.logger.info("=" * 60 + "\n")
        
        print_ontology()
        
        try:
            # Step 1: Crawl (optional)
            if crawl:
                self.step_crawl(kwargs.get("crawl_source", "CP"))
            
            # Step 2: Normalize
            if normalize:
                self.step_normalize()
            
            # Step 3: Build KG
            if build_kg:
                self.step_build_kg()
            
            # Step 4: Load to Neo4j (optional)
            if load_neo4j:
                self.step_load_to_neo4j(clear=neo4j_clear, **{
                    k.replace("neo4j_", ""): v for k, v in kwargs.items() if k.startswith("neo4j_")
                })
            
            # Step 5: Recommend
            if recommend:
                result = self.step_recommend(
                    top_k=kwargs.get("top_k", 10),
                    max_dishes=kwargs.get("max_dishes", 3),
                )
                
                # Print recommendations
                if result.get("meal_set"):
                    print("\n" + "=" * 60)
                    print("🎯 RECOMMENDED MEAL SET:")
                    print("=" * 60)
                    for i, dish in enumerate(result["meal_set"], 1):
                        print(f"{i}. {dish['dish_name']}")
                        print(f"   Score: {dish['score']:.2f}")
                        print(f"   Used: {', '.join(dish.get('used_ingredients', []))}")
                    print("=" * 60 + "\n")
            
            self.logger.info("✅ PIPELINE COMPLETED SUCCESSFULLY\n")
            
        except Exception as e:
            self.logger.error(f"❌ PIPELINE FAILED: {e}", exc_info=True)
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status"""
        return {
            "raw_csv_exists": self.config.raw_recipe_csv.exists(),
            "recipes_processed_exists": self.config.recipe_file.exists(),
            "kg_payload_exists": self.config.kg_payload_file.exists(),
            "kg_cypher_exists": self.config.kg_cypher_file.exists(),
            "recommendations_exist": self.config.recommendation_file.exists(),
            "config": self.config.to_dict(),
        }


# Convenience functions
def get_orchestrator(config: Optional[Config] = None) -> PipelineOrchestrator:
    """Get pipeline orchestrator instance"""
    return PipelineOrchestrator(config)