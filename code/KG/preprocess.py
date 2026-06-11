import json
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

GROUP_MAIN = "main_ingredients"
GROUP_REQUIRED = "required_ingredients"
GROUP_OPTIONAL = "optional_ingredients"

GROUP_KEY_MAPPING = {
    "main_ingredients": GROUP_MAIN,
    "required_ingredients": GROUP_REQUIRED,
    "optional_ingredients": GROUP_OPTIONAL,
}

GROUP_WEIGHT = {
    GROUP_MAIN: 0.60,
    GROUP_REQUIRED: 0.35,
    GROUP_OPTIONAL: 0.05,
}

UNIT_ALIASES = {
    "g": "g",
    "gr": "g",
    "gram": "g",
    "kg": "kg",
    "ml": "ml",
    "l": "l",
    "lit": "l",
    "litre": "l",
    "qua": "piece",
    "cay": "piece",
    "cu": "piece",
    "lat": "piece",
    "con": "piece",
    "muong": "spoon",
    "thia": "spoon",
}

STOP_WORDS = {
    "tuoi",
    "kho",
    "nguyen",
    "co",
    "the",
    "neu",
    "hoac",
    "va",
    "bam",
    "cat",
    "lua",
    "ta",
}

DISHTYPE_ALIASES = {
    "mon man": "mon man",
    "man": "mon man",
    "canh": "canh",
    "rau": "rau",
    "salad": "rau",
    "kho": "kho",
    "sup": "soup",
    "soup": "soup",
    "chay": "chay",
    "khai vi": "khai vi",
    "trang mieng": "trang mieng",
}

DISHTYPE_HINTS = [
    ("rau", "rau"),
    ("salad", "rau"),
    ("canh", "canh"),
    ("soup", "canh"),
    ("sup", "canh"),
    ("chay", "chay"),
    ("món chay", "chay"),
    ("mon chay", "chay"),
    ("mặn", "mon man"),
    ("man", "mon man"),
    ("thit", "mon man"),
    ("ga", "mon man"),
    ("bo", "mon man"),
    ("tom", "mon man"),
    ("ca", "mon man"),
]

CANONICAL_HINTS = {
    "tom": "tom",
    "bong cai": "bong cai",
    "ca rot": "ca rot",
    "hanh tay": "hanh tay",
    "thit bo": "thit bo",
    "thit ga": "thit ga",
    "ga": "thit ga",
    "nam": "nam",
    "cai": "rau cai",
    "toi": "toi",
    "chanh": "chanh",
    "dau": "dau",
    "ca hoi": "ca hoi",
    "trung": "trung",
    "muoi": "muoi",
    "duong": "duong",
    "nuoc mam": "nuoc mam",
    "mi y": "mi y",
    "my y": "mi y",
    "spaghetti": "mi y",
}


@dataclass
class IngredientRecord:
    name: str
    canonical_name: str
    raw_quantity: Any
    value: float | None
    unit: str | None
    value_base: float | None
    group: str


@dataclass
class StockRecord:
    name: str
    canonical_name: str
    raw_quantity: Any
    value: float | None
    unit: str | None
    value_base: float | None


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def normalize_text(text: str) -> str:
    lowered = strip_accents(str(text).lower())
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def tokenize_name(name: str) -> list[str]:
    tokens = [token for token in normalize_text(name).split(" ") if token and token not in STOP_WORDS]
    return tokens


def canonical_ingredient_name(name: str) -> str:
    normalized = normalize_text(name)
    for hint, canonical in CANONICAL_HINTS.items():
        if hint in normalized:
            return canonical

    tokens = tokenize_name(name)
    if not tokens:
        return normalized or "unknown"

    return " ".join(tokens[:3])


def parse_number(token: str) -> float | None:
    cleaned = token.strip().replace(",", ".")
    if not cleaned:
        return None

    if "/" in cleaned:
        left, right = cleaned.split("/", 1)
        try:
            denominator = float(right)
            if denominator == 0:
                return None
            return float(left) / denominator
        except ValueError:
            return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_quantity(raw_quantity: Any) -> tuple[float | None, str | None]:
    if raw_quantity is None:
        return None, None

    text = normalize_text(str(raw_quantity))
    if not text:
        return None, None

    parts = text.split(" ")
    value = parse_number(parts[0])
    if value is None:
        return None, None

    unit = parts[1] if len(parts) > 1 else None
    if unit:
        unit = UNIT_ALIASES.get(unit, unit)

    return value, unit


def to_base_unit(value: float | None, unit: str | None) -> float | None:
    if value is None:
        return None

    if unit is None:
        return value
    if unit == "kg":
        return value * 1000.0
    if unit == "l":
        return value * 1000.0

    return value


def ingredient_name_similarity(name_a: str, name_b: str) -> float:
    a = normalize_text(name_a)
    b = normalize_text(name_b)
    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    ratio_score = SequenceMatcher(None, a, b).ratio()

    set_a = set(tokenize_name(name_a))
    set_b = set(tokenize_name(name_b))
    if not set_a or not set_b:
        return ratio_score

    jaccard = len(set_a.intersection(set_b)) / len(set_a.union(set_b))
    return 0.5 * ratio_score + 0.5 * jaccard


def normalize_group_key(group_name: str) -> str:
    normalized = normalize_text(group_name)
    return GROUP_KEY_MAPPING.get(normalized, normalized.replace(" ", "_"))


def normalize_dish_type(value: Any) -> tuple[str | None, str | None]:
    if value is None:
        return None, None

    raw_text = str(value).strip()
    if not raw_text:
        return None, None

    normalized = normalize_text(raw_text)
    if not normalized:
        return None, None

    dish_type_key = DISHTYPE_ALIASES.get(normalized, normalized.replace(" ", "_"))
    return raw_text, dish_type_key


def infer_dish_type_from_text(text: Any) -> tuple[str | None, str | None]:
    if text is None:
        return None, None

    normalized = normalize_text(str(text))
    if not normalized:
        return None, None

    for hint, dish_type_key in DISHTYPE_HINTS:
        if hint in normalized:
            if dish_type_key == "mon man" and "rau" in normalized and hint not in {"mặn", "man", "thit", "ga", "bo", "tom", "ca"}:
                continue
            if dish_type_key == "canh" and "rau luoc" in normalized:
                continue
            return dish_type_key.replace("_", " "), dish_type_key

    return None, None


def resolve_recipe_dish_type(recipe: dict[str, Any]) -> tuple[str | None, str | None]:
    raw_value = recipe.get("loại món") or recipe.get("loai mon") or recipe.get("loại món ăn") or recipe.get("loai mon an")
    explicit_value, explicit_key = normalize_dish_type(raw_value)
    if explicit_key is not None:
        return explicit_value, explicit_key

    inferred_value, inferred_key = infer_dish_type_from_text(recipe.get("name") or recipe.get("tên"))
    if inferred_key is not None:
        return inferred_value, inferred_key

    ingredient_text = " ".join(
        str(item.get("name") or item.get("tên") or "")
        for group_name in ["main_ingredients", "required_ingredients", "optional_ingredients"]  # Các group mới
        for item in (recipe.get(group_name, []) if isinstance(recipe.get(group_name, []), list) else [])
        if isinstance(item, dict)
    )
    return infer_dish_type_from_text(ingredient_text)


def load_json_array(path: str | Path) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in {path}")

    return [item for item in data if isinstance(item, dict)]


def normalize_stock(stock_rows: list[dict[str, Any]]) -> list[StockRecord]:
    normalized: list[StockRecord] = []
    for row in stock_rows:
        name = str(row.get("tên") or row.get("name") or row.get("ingredient") or "").strip()
        if not name:
            continue

        raw_quantity = row.get("khối lượng") or row.get("quantity") or row.get("weight")
        value, unit = parse_quantity(raw_quantity)
        normalized.append(
            StockRecord(
                name=name,
                canonical_name=canonical_ingredient_name(name),
                raw_quantity=raw_quantity,
                value=value,
                unit=unit,
                value_base=to_base_unit(value, unit),
            )
        )

    return normalized


def normalize_recipe_ingredients(recipe: dict[str, Any]) -> list[IngredientRecord]:
    normalized: list[IngredientRecord] = []

    groups = [
        ("main_ingredients", "nguyên liệu chính"),
        ("required_ingredients", "nguyên liệu phụ_1 cần thiết"),
        ("optional_ingredients", "nguyên liệu phụ_2 có thể bỏ qua"),
    ]

    for eng_group, vi_group in groups:
        group_key = normalize_group_key(eng_group)
        rows = recipe.get(eng_group) or recipe.get(vi_group) or []
        if not isinstance(rows, list):
            continue

        for row in rows:
            if not isinstance(row, dict):
                continue

            name = str(row.get("name") or row.get("tên") or "").strip()
            if not name:
                continue

            raw_quantity = row.get("weight") or row.get("khối lượng")
            value, unit = parse_quantity(raw_quantity)

            normalized.append(
                IngredientRecord(
                    name=name,
                    canonical_name=canonical_ingredient_name(name),
                    raw_quantity=raw_quantity,
                    value=value,
                    unit=unit,
                    value_base=to_base_unit(value, unit),
                    group=group_key,
                )
            )

    return normalized


def best_stock_match(
    ingredient: IngredientRecord,
    stock_items: list[StockRecord],
) -> tuple[StockRecord | None, float]:
    best_item = None
    best_score = 0.0

    for stock in stock_items:
        name_score = ingredient_name_similarity(ingredient.name, stock.name)
        canonical_bonus = 0.25 if ingredient.canonical_name == stock.canonical_name else 0.0
        score = min(1.0, name_score + canonical_bonus)

        if score > best_score:
            best_score = score
            best_item = stock

    return best_item, best_score


def quantity_coverage(required_value_base: float | None, available_value_base: float | None) -> float:
    if required_value_base is None:
        return 0.5
    if available_value_base is None:
        return 0.35
    if required_value_base <= 0:
        return 1.0

    return max(0.0, min(1.0, available_value_base / required_value_base))
