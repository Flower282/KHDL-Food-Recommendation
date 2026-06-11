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
    ingredient_name_similarity,
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
            # pyrefly: ignore [missing-import]
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


def dish_name_similarity(name_a: str, name_b: str) -> float:
    """Computes similarity score between two dish names using ingredient_name_similarity."""
    return ingredient_name_similarity(name_a, name_b)


def merge_payloads(
    main_payload: dict[str, list[dict[str, Any]]],
    child_payload: dict[str, list[dict[str, Any]]],
    threshold: float = 0.8,
) -> tuple[dict[str, list[dict[str, Any]]], int, int]:
    """
    Merges child_payload into main_payload.
    For dishes in child_payload:
      - Finds the best matching dish in main_payload using dish_name_similarity.
      - If similarity >= threshold:
        - Resolves dish name to the matched one.
        - Merges ingredients.
        - Updates properties (time, difficulty, source).
        - Count as merged.
      - If similarity < threshold:
        - Appends dish and its ingredients as new.
        - Count as added.
    For stock_rows:
      - Updates availability or appends new stock items.
    For stock_mapping_rows:
      - Updates or appends new stock mappings.
    Returns: (updated_main_payload, num_merged, num_added)
    """
    if not main_payload:
        main_payload = {
            "dish_rows": [],
            "ingredient_rows": [],
            "stock_rows": [],
            "stock_mapping_rows": [],
        }

    # Helper mapping to lookup dishes by name in main payload
    main_dishes = {d["name"]: d for d in main_payload.get("dish_rows", [])}
    
    # We will build a helper lookup for ingredients of main dishes
    # Structure: (dish_name, ingredient_canonical) -> ingredient_row_dict
    main_ingredients = {}
    for r in main_payload.get("ingredient_rows", []):
        main_ingredients[(r["dish_name"], r["ingredient_canonical"])] = r

    num_merged = 0
    num_added = 0

    for c_dish in child_payload.get("dish_rows", []):
        c_name = c_dish["name"]
        
        # Find best match in main payload
        best_match_name = None
        best_score = -1.0
        
        for m_name in main_dishes:
            score = dish_name_similarity(c_name, m_name)
            if score > best_score:
                best_score = score
                best_match_name = m_name

        if best_match_name and best_score >= threshold:
            # Match found! Merge into existing dish
            num_merged += 1
            m_dish = main_dishes[best_match_name]
            
            # Update difficulty if "khong_ro"
            if m_dish.get("difficulty") == "khong_ro" and c_dish.get("difficulty") != "khong_ro":
                m_dish["difficulty"] = c_dish["difficulty"]
            
            # Update time minutes
            if c_dish.get("time_minutes") is not None:
                m_dish["time_minutes"] = c_dish["time_minutes"]
                m_dish["time_text"] = c_dish["time_text"]
                
            # Update dish type if null
            if not m_dish.get("dish_type") and c_dish.get("dish_type"):
                m_dish["dish_type"] = c_dish["dish_type"]
                m_dish["dish_type_key"] = c_dish["dish_type_key"]

            # Append source if not already present
            sources = [s.strip() for s in str(m_dish.get("source", "")).split(",") if s.strip()]
            new_source = c_dish.get("source")
            if new_source and new_source not in sources:
                sources.append(new_source)
                m_dish["source"] = ", ".join(sources)

            # Match child ingredients to the resolved dish name
            for c_ing in child_payload.get("ingredient_rows", []):
                if c_ing["dish_name"] == c_name:
                    canonical = c_ing["ingredient_canonical"]
                    key = (best_match_name, canonical)
                    
                    if key in main_ingredients:
                        # Update quantity / values of existing ingredient
                        m_ing = main_ingredients[key]
                        m_ing["required_raw"] = c_ing["required_raw"]
                        m_ing["required_value"] = c_ing["required_value"]
                        m_ing["required_unit"] = c_ing["required_unit"]
                        m_ing["required_value_base"] = c_ing["required_value_base"]
                        m_ing["weight"] = c_ing["weight"]
                        m_ing["optional"] = c_ing["optional"]
                    else:
                        # Add new ingredient to existing dish
                        new_ing = dict(c_ing)
                        new_ing["dish_name"] = best_match_name
                        main_payload["ingredient_rows"].append(new_ing)
                        main_ingredients[key] = new_ing
        else:
            # No match found. Add as a new dish
            num_added += 1
            new_dish = dict(c_dish)
            main_payload["dish_rows"].append(new_dish)
            main_dishes[c_name] = new_dish
            
            # Add all ingredients for this new dish
            for c_ing in child_payload.get("ingredient_rows", []):
                if c_ing["dish_name"] == c_name:
                    new_ing = dict(c_ing)
                    main_payload["ingredient_rows"].append(new_ing)
                    main_ingredients[(c_name, new_ing["ingredient_canonical"])] = new_ing

    # Merge stock_rows
    # Lookup by name
    main_stocks = {s["name"]: s for s in main_payload.get("stock_rows", [])}
    for c_stock in child_payload.get("stock_rows", []):
        s_name = c_stock["name"]
        if s_name in main_stocks:
            # Update stock level
            m_stock = main_stocks[s_name]
            m_stock["available_raw"] = c_stock["available_raw"]
            m_stock["available_value"] = c_stock["available_value"]
            m_stock["available_unit"] = c_stock["available_unit"]
            m_stock["available_value_base"] = c_stock["available_value_base"]
            m_stock["canonical_name"] = c_stock["canonical_name"]
        else:
            new_stock = dict(c_stock)
            main_payload["stock_rows"].append(new_stock)
            main_stocks[s_name] = new_stock

    # Merge stock_mapping_rows
    # Lookup by stock_name
    main_stock_maps = {m["stock_name"]: m for m in main_payload.get("stock_mapping_rows", [])}
    for c_map in child_payload.get("stock_mapping_rows", []):
        s_name = c_map["stock_name"]
        if s_name in main_stock_maps:
            m_map = main_stock_maps[s_name]
            m_map["ingredient_canonical"] = c_map["ingredient_canonical"]
            m_map["name_score"] = c_map["name_score"]
        else:
            new_map = dict(c_map)
            main_payload["stock_mapping_rows"].append(new_map)
            main_stock_maps[s_name] = new_map

    return main_payload, num_merged, num_added


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
                "time_minutes": _parse_minutes(recipe.get("thời gian") or recipe.get("time")),
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
