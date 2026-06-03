from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import DEFAULT_NEO4J_DATABASE, DEFAULT_NEO4J_URI, DEFAULT_NEO4J_USER
from .ontology import schema_cypher_statements
from .preprocess import (
    load_json_array,
    normalize_recipe_ingredients,
    normalize_stock,
    resolve_recipe_dish_type,
)


class Neo4jKnowledgeGraph:
    def __init__(
        self,
        password: str,
        uri: str = DEFAULT_NEO4J_URI,
        user: str = DEFAULT_NEO4J_USER,
        database: str = DEFAULT_NEO4J_DATABASE,
    ) -> None:
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise ImportError("Missing neo4j package. Install with: pip install neo4j") from exc

        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database

    def close(self) -> None:
        self._driver.close()

    def _run(self, cypher: str, parameters: dict[str, Any] | None = None) -> None:
        with self._driver.session(database=self.database) as session:
            session.run(cypher, parameters or {})

    def create_schema(self) -> None:
        for statement in schema_cypher_statements():
            self._run(statement)

    def clear_graph(self) -> None:
        self._run("MATCH (n) DETACH DELETE n")

    def load_payload(self, payload: dict[str, Any]) -> None:
        self._run(
            """
            UNWIND $dish_rows AS row
            MERGE (d:Dish {name: row.name})
            SET d.time_text = row.time_text,
                d.serving_text = row.serving_text,
                d.time_minutes = row.time_minutes,
                d.dish_type = row.dish_type,
                d.dish_type_key = row.dish_type_key,
                d.source = row.source
            MERGE (f:Difficulty {name: row.difficulty})
            MERGE (d)-[:HAS_DIFFICULTY]->(f)
            """,
            {"dish_rows": payload["dish_rows"]},
        )

        self._run(
            """
            UNWIND $dish_rows AS row
            WITH row
            WHERE row.dish_type_key IS NOT NULL
            MATCH (d:Dish {name: row.name})
            MERGE (t:DishType {name: row.dish_type_key})
            ON CREATE SET t.display_name = row.dish_type
            SET t.display_name = coalesce(t.display_name, row.dish_type)
            MERGE (d)-[:HAS_TYPE]->(t)
            """,
            {"dish_rows": payload["dish_rows"]},
        )

        self._run(
            """
            UNWIND $ingredient_rows AS row
            MATCH (d:Dish {name: row.dish_name})
            MERGE (i:Ingredient {canonical_name: row.ingredient_canonical})
            ON CREATE SET i.display_name = row.ingredient_name
            MERGE (d)-[r:HAS_INGREDIENT {group: row.group, ingredient_name: row.ingredient_name}]->(i)
            SET r.required_raw = row.required_raw,
                r.required_value = row.required_value,
                r.required_unit = row.required_unit,
                r.required_value_base = row.required_value_base,
                r.weight = row.weight,
                r.optional = row.optional
            """,
            {"ingredient_rows": payload["ingredient_rows"]},
        )

        self._run(
            """
            UNWIND $stock_rows AS row
            MERGE (s:StockItem {name: row.name})
            SET s.available_raw = row.available_raw,
                s.available_value = row.available_value,
                s.available_unit = row.available_unit,
                s.available_value_base = row.available_value_base,
                s.canonical_name = row.canonical_name
            """,
            {"stock_rows": payload["stock_rows"]},
        )

        self._run(
            """
            UNWIND $stock_mapping_rows AS row
            MATCH (s:StockItem {name: row.stock_name})
            MERGE (i:Ingredient {canonical_name: row.ingredient_canonical})
            ON CREATE SET i.display_name = row.stock_name
            MERGE (s)-[r:REFERS_TO]->(i)
            SET r.name_score = row.name_score
            """,
            {"stock_mapping_rows": payload["stock_mapping_rows"]},
        )


def _parse_minutes(time_text: Any) -> int | None:
    if time_text is None:
        return None

    text = str(time_text)
    digits = "".join(ch if ch.isdigit() else " " for ch in text).split()
    if not digits:
        return None

    try:
        return int(digits[0])
    except ValueError:
        return None


def build_kg_payload(recipe_path: str | Path, stock_path: str | Path) -> dict[str, list[dict[str, Any]]]:
    recipe_rows = load_json_array(recipe_path)
    stock_rows_input = load_json_array(stock_path)

    normalized_stock = normalize_stock(stock_rows_input)

    dish_rows: list[dict[str, Any]] = []
    ingredient_rows: list[dict[str, Any]] = []

    for recipe in recipe_rows:
        # Support both Vietnamese and English field names
        dish_name = str(recipe.get("tên", "") or recipe.get("name", "")).strip()
        if not dish_name:
            continue

        dish_rows.append(
            {
                "name": dish_name,
                "time_text": recipe.get("thời gian") or recipe.get("time"),
                "serving_text": recipe.get("số người") or recipe.get("servings"),
                "difficulty": str(recipe.get("độ khó", "") or recipe.get("difficulty", "khong_ro")).strip() or "khong_ro",
                "time_minutes": _parse_minutes(recipe.get("thời gian")),
                "dish_type": resolve_recipe_dish_type(recipe)[0],
                "dish_type_key": resolve_recipe_dish_type(recipe)[1],
                "source": "data_monan_day_du_CP.json",
            }
        )

        for ingredient in normalize_recipe_ingredients(recipe):
            ingredient_rows.append(
                {
                    "dish_name": dish_name,
                    "ingredient_name": ingredient.name,
                    "ingredient_canonical": ingredient.canonical_name,
                    "group": ingredient.group,
                    "required_raw": ingredient.raw_quantity,
                    "required_value": ingredient.value,
                    "required_unit": ingredient.unit,
                    "required_value_base": ingredient.value_base,
                    "weight": 1.0,
                    "optional": ingredient.group.endswith("bo_qua"),
                }
            )

    stock_rows: list[dict[str, Any]] = []
    for item in normalized_stock:
        stock_rows.append(
            {
                "name": item.name,
                "available_raw": item.raw_quantity,
                "available_value": item.value,
                "available_unit": item.unit,
                "available_value_base": item.value_base,
                "canonical_name": item.canonical_name,
            }
        )

    all_ingredient_rows_for_matching = [
        {
            "name": row["ingredient_name"],
            "canonical": row["ingredient_canonical"],
        }
        for row in ingredient_rows
    ]

    stock_mapping_rows: list[dict[str, Any]] = []
    for stock in normalized_stock:
        best_canonical = stock.canonical_name
        best_score = 0.0

        for ingredient_row in all_ingredient_rows_for_matching:
            score = 0.25 if ingredient_row["canonical"] == stock.canonical_name else 0.0
            score += 0.75 if ingredient_row["name"].lower() == stock.name.lower() else 0.0
            if score > best_score:
                best_score = score
                best_canonical = ingredient_row["canonical"]

        stock_mapping_rows.append(
            {
                "stock_name": stock.name,
                "ingredient_canonical": best_canonical,
                "name_score": round(best_score, 4),
            }
        )

    return {
        "dish_rows": dish_rows,
        "ingredient_rows": ingredient_rows,
        "stock_rows": stock_rows,
        "stock_mapping_rows": stock_mapping_rows,
    }


def payload_to_cypher_commands(payload: dict[str, list[dict[str, Any]]]) -> list[str]:
    commands: list[str] = []
    for statement in schema_cypher_statements():
        commands.append(statement + ";")

    for row in payload["dish_rows"]:
        commands.append(
            "MERGE (d:Dish {name: "
            + quote(row["name"])
            + "}) SET d.time_text = "
            + quote(row.get("time_text"))
            + ", d.serving_text = "
            + quote(row.get("serving_text"))
            + ", d.time_minutes = "
            + to_cypher_value(row.get("time_minutes"))
            + ", d.dish_type = "
            + quote(row.get("dish_type"))
            + ", d.dish_type_key = "
            + quote(row.get("dish_type_key"))
            + ", d.source = "
            + quote(row.get("source"))
            + ";"
        )

        if row.get("dish_type_key") is not None:
            commands.append(
                "MERGE (t:DishType {name: "
                + quote(row.get("dish_type_key"))
                + "}) ON CREATE SET t.display_name = "
                + quote(row.get("dish_type"))
                + ";"
            )
            commands.append(
                "MATCH (d:Dish {name: "
                + quote(row["name"])
                + "}), (t:DishType {name: "
                + quote(row.get("dish_type_key"))
                + "}) MERGE (d)-[:HAS_TYPE]->(t);"
            )

        commands.append(
            "MERGE (f:Difficulty {name: "
            + quote(row["difficulty"])
            + "});"
        )
        commands.append(
            "MATCH (d:Dish {name: "
            + quote(row["name"])
            + "}), (f:Difficulty {name: "
            + quote(row["difficulty"])
            + "}) MERGE (d)-[:HAS_DIFFICULTY]->(f);"
        )

    for row in payload["ingredient_rows"]:
        commands.append(
            "MERGE (i:Ingredient {canonical_name: "
            + quote(row["ingredient_canonical"])
            + "}) ON CREATE SET i.display_name = "
            + quote(row["ingredient_name"])
            + ";"
        )
        commands.append(
            "MATCH (d:Dish {name: "
            + quote(row["dish_name"])
            + "}), (i:Ingredient {canonical_name: "
            + quote(row["ingredient_canonical"])
            + "}) MERGE (d)-[r:HAS_INGREDIENT {group: "
            + quote(row["group"])
            + ", ingredient_name: "
            + quote(row["ingredient_name"])
            + "}]->(i) SET r.required_raw = "
            + quote(row.get("required_raw"))
            + ", r.required_value = "
            + to_cypher_value(row.get("required_value"))
            + ", r.required_unit = "
            + quote(row.get("required_unit"))
            + ", r.required_value_base = "
            + to_cypher_value(row.get("required_value_base"))
            + ", r.weight = "
            + to_cypher_value(row.get("weight"))
            + ", r.optional = "
            + to_cypher_value(row.get("optional"))
            + ";"
        )

    for row in payload["stock_rows"]:
        commands.append(
            "MERGE (s:StockItem {name: "
            + quote(row["name"])
            + "}) SET s.available_raw = "
            + quote(row.get("available_raw"))
            + ", s.available_value = "
            + to_cypher_value(row.get("available_value"))
            + ", s.available_unit = "
            + quote(row.get("available_unit"))
            + ", s.available_value_base = "
            + to_cypher_value(row.get("available_value_base"))
            + ", s.canonical_name = "
            + quote(row.get("canonical_name"))
            + ";"
        )

    for row in payload["stock_mapping_rows"]:
        commands.append(
            "MERGE (i:Ingredient {canonical_name: "
            + quote(row["ingredient_canonical"])
            + "});"
        )
        commands.append(
            "MATCH (s:StockItem {name: "
            + quote(row["stock_name"])
            + "}), (i:Ingredient {canonical_name: "
            + quote(row["ingredient_canonical"])
            + "}) MERGE (s)-[r:REFERS_TO]->(i) SET r.name_score = "
            + to_cypher_value(row.get("name_score"))
            + ";"
        )

    return commands


def to_cypher_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return quote(value)


def quote(value: Any) -> str:
    if value is None:
        return "null"
    text = str(value).replace("\\", "\\\\").replace("\"", "\\\"")
    return f'"{text}"'
