from dataclasses import dataclass


@dataclass(frozen=True)
class OntologyNode:
    label: str
    key_property: str
    description: str


@dataclass(frozen=True)
class OntologyRelation:
    relation: str
    from_label: str
    to_label: str
    description: str


ONTOLOGY_NODES = [
    OntologyNode("Dish", "name", "Recipe entity"),
    OntologyNode("DishType", "name", "Dish category such as mon man, canh, rau"),
    OntologyNode("Ingredient", "canonical_name", "Canonical ingredient entity"),
    OntologyNode("StockItem", "name", "Ingredient item available in stock"),
    OntologyNode("Difficulty", "name", "Recipe difficulty level"),
]

ONTOLOGY_RELATIONS = [
    OntologyRelation("HAS_TYPE", "Dish", "DishType", "Dish category relation"),
    OntologyRelation("HAS_INGREDIENT", "Dish", "Ingredient", "Ingredient requirement for a dish"),
    OntologyRelation("REFERS_TO", "StockItem", "Ingredient", "Stock item mapped to canonical ingredient"),
    OntologyRelation("HAS_DIFFICULTY", "Dish", "Difficulty", "Dish difficulty level"),
]


def schema_cypher_statements() -> list[str]:
    return [
        "CREATE CONSTRAINT dish_name_unique IF NOT EXISTS FOR (d:Dish) REQUIRE d.name IS UNIQUE",
        "CREATE CONSTRAINT dish_type_name_unique IF NOT EXISTS FOR (t:DishType) REQUIRE t.name IS UNIQUE",
        "CREATE CONSTRAINT ingredient_name_unique IF NOT EXISTS FOR (i:Ingredient) REQUIRE i.canonical_name IS UNIQUE",
        "CREATE CONSTRAINT stock_name_unique IF NOT EXISTS FOR (s:StockItem) REQUIRE s.name IS UNIQUE",
        "CREATE CONSTRAINT difficulty_name_unique IF NOT EXISTS FOR (f:Difficulty) REQUIRE f.name IS UNIQUE",
        "CREATE INDEX dish_type_key_idx IF NOT EXISTS FOR (d:Dish) ON (d.dish_type_key)",
        "CREATE INDEX ingredient_display_name_idx IF NOT EXISTS FOR (i:Ingredient) ON (i.display_name)",
        "CREATE INDEX dish_time_idx IF NOT EXISTS FOR (d:Dish) ON (d.time_minutes)",
    ]
