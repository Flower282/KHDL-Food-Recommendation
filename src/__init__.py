"""
Food Recommendation System - Core Package

Refactored structure for better control and maintainability
"""

from src.config import Config
from src.pipeline import get_orchestrator, PipelineOrchestrator
from src.ontology import ONTOLOGY_NODES, ONTOLOGY_RELATIONS, print_ontology

__version__ = "1.0.0"
__all__ = [
    "Config",
    "get_orchestrator",
    "PipelineOrchestrator",
    "ONTOLOGY_NODES",
    "ONTOLOGY_RELATIONS",
    "print_ontology",
]
