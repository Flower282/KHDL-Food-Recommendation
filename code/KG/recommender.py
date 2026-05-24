from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .preprocess import (
    GROUP_MAIN,
    GROUP_REQUIRED,
    GROUP_WEIGHT,
    IngredientRecord,
    StockRecord,
    best_stock_match,
    load_json_array,
    normalize_dish_type,
    normalize_recipe_ingredients,
    normalize_stock,
    resolve_recipe_dish_type,
    quantity_coverage,
)

MATCH_THRESHOLD = 0.55
NAME_WEIGHT = 0.7
QUANTITY_WEIGHT = 0.3


@dataclass
class IngredientMatch:
    ingredient_name: str
    ingredient_group: str
    stock_name: str | None
    name_score: float
    quantity_score: float
    final_score: float


@dataclass
class DishScore:
    dish_name: str
    score: float
    missing_required: int
    ingredient_matches: list[IngredientMatch]
    required_consumption_base: dict[str, float]
    dish_type: str | None = None
    required_fulfilled: bool = True


def _group_score(matches: list[IngredientMatch], group: str) -> float:
    group_matches = [m for m in matches if m.ingredient_group == group]
    if not group_matches:
        return 0.0

    return sum(item.final_score for item in group_matches) / len(group_matches)


def score_dish(recipe: dict[str, Any], stock: list[StockRecord]) -> DishScore:
    # Updated: "tên" → "name"
    dish_name = str(recipe.get("name", "khong_ro")).strip() or "khong_ro"
    ingredients = normalize_recipe_ingredients(recipe)
    dish_type, _ = resolve_recipe_dish_type(recipe)

    if not ingredients:
        return DishScore(
            dish_name=dish_name,
            score=0.0,
            missing_required=0,
            ingredient_matches=[],
            required_consumption_base={},
            dish_type=dish_type,
        )

    matches: list[IngredientMatch] = []
    required_consumption_base: dict[str, float] = {}
    missing_required = 0

    for ingredient in ingredients:
        stock_item, name_score = best_stock_match(ingredient, stock)
        if name_score < MATCH_THRESHOLD:
            stock_item = None

        quantity_score = quantity_coverage(
            ingredient.value_base,
            stock_item.value_base if stock_item else None,
        )

        final_score = NAME_WEIGHT * name_score + QUANTITY_WEIGHT * quantity_score

        matches.append(
            IngredientMatch(
                ingredient_name=ingredient.name,
                ingredient_group=ingredient.group,
                stock_name=stock_item.name if stock_item else None,
                name_score=round(name_score, 4),
                quantity_score=round(quantity_score, 4),
                final_score=round(final_score, 4),
            )
        )

        if ingredient.group in {GROUP_MAIN, GROUP_REQUIRED} and name_score < MATCH_THRESHOLD:
            missing_required += 1

        if ingredient.group == GROUP_MAIN and ingredient.value_base is not None:
            required_consumption_base[ingredient.canonical_name] = (
                required_consumption_base.get(ingredient.canonical_name, 0.0) + ingredient.value_base
            )

    weighted_score = 0.0
    total_weight = 0.0
    for group, weight in GROUP_WEIGHT.items():
        group_value = _group_score(matches, group)
        if group_value <= 0 and group != "optional_ingredients":
            continue
        weighted_score += weight * group_value
        total_weight += weight

    score = weighted_score / total_weight if total_weight > 0 else 0.0

    # Determine whether all main/required ingredients are fulfilled (name match + quantity)
    required_fulfilled = True
    for m in matches:
        if m.ingredient_group in {GROUP_MAIN, GROUP_REQUIRED}:
            if m.name_score < MATCH_THRESHOLD or m.quantity_score < 1.0:
                required_fulfilled = False
                break

    return DishScore(
        dish_name=dish_name,
        score=round(score, 4),
        missing_required=missing_required,
        ingredient_matches=matches,
        required_consumption_base=required_consumption_base,
        dish_type=dish_type,
        required_fulfilled=required_fulfilled,
    )


def rank_dishes(recipe_rows: list[dict[str, Any]], stock_rows: list[dict[str, Any]], top_k: int = 10) -> list[DishScore]:
    normalized_stock = normalize_stock(stock_rows)
    scored = [score_dish(recipe, normalized_stock) for recipe in recipe_rows]

    scored.sort(key=lambda item: (item.score, -item.missing_required), reverse=True)
    return scored[:top_k]


def _recipe_matches_dish_type(recipe: dict[str, Any], dish_type_filter: str | None) -> bool:
    if not dish_type_filter:
        return True

    # Support both old and new field names
    recipe_type = (
        recipe.get("loại món") or 
        recipe.get("loai mon") or 
        recipe.get("loại món ăn") or 
        recipe.get("loai mon an") or
        recipe.get("dish_type")  # New field
    )
    if recipe_type is None:
        return False

    _, recipe_key = normalize_dish_type(recipe_type)
    _, filter_key = normalize_dish_type(dish_type_filter)
    return recipe_key == filter_key


def _parse_minutes(time_text: Any) -> int | None:
    if time_text is None:
        return None

    digits = re.findall(r"\d+", str(time_text))
    if not digits:
        return None

    try:
        return int(digits[0])
    except ValueError:
        return None


def _recipe_within_time_limit(recipe: dict[str, Any], max_minutes: int | None) -> bool:
    if max_minutes is None:
        return True

    # Support both old "thời gian" and new "time" fields
    time_value = recipe.get("time") or recipe.get("thời gian")
    minutes = _parse_minutes(time_value)
    return minutes is not None and minutes <= max_minutes


def _recipe_dish_type(recipe: dict[str, Any]) -> str | None:
    normalized_value, _ = resolve_recipe_dish_type(recipe)
    return normalized_value


def _normalize_selected_types(selected_types: list[str] | None) -> set[str]:
    normalized: set[str] = set()
    for item in selected_types or []:
        _, key = normalize_dish_type(item)
        if key:
            normalized.add(key)
    return normalized


def _matches_required_types(recipe_type: str | None, required_types: set[str]) -> bool:
    if not required_types:
        return True
    if recipe_type is None:
        return False
    _, recipe_key = normalize_dish_type(recipe_type)
    return recipe_key in required_types


def recommend_meal_set(
    recipe_rows: list[dict[str, Any]],
    stock_rows: list[dict[str, Any]],
    max_dishes: int = 3,
    candidate_pool: int = 15,
    dish_type_filter: str | None = None,
    required_types: list[str] | None = None,
    max_minutes: int | None = None,
) -> list[DishScore]:
    normalized_stock = normalize_stock(stock_rows)
    stock_remaining: dict[str, float | None] = {
        item.canonical_name: item.value_base for item in normalized_stock
    }

    filtered_recipe_rows = [
        recipe
        for recipe in recipe_rows
        if _recipe_matches_dish_type(recipe, dish_type_filter) and _recipe_within_time_limit(recipe, max_minutes)
    ]
    required_type_keys = _normalize_selected_types(required_types)
    if required_type_keys and len(required_type_keys) > max_dishes:
        return []

    scored = [score_dish(recipe, normalized_stock) for recipe in filtered_recipe_rows]
    scored.sort(key=lambda item: (item.score, -item.missing_required), reverse=True)
    candidates = scored if required_type_keys else scored[:candidate_pool]
    selected: list[DishScore] = []
    covered_types: set[str] = set()

    def candidate_pick_score(candidate: DishScore) -> float:
        feasibility_scores: list[float] = []
        for canonical_name, required_amount in candidate.required_consumption_base.items():
            available_amount = stock_remaining.get(canonical_name)
            feasibility_scores.append(quantity_coverage(required_amount, available_amount))

        feasibility = sum(feasibility_scores) / len(feasibility_scores) if feasibility_scores else 0.8

        new_ingredients = [
            key
            for key in candidate.required_consumption_base.keys()
            if all(key not in dish.required_consumption_base for dish in selected)
        ]
        diversity_bonus = min(0.1, 0.02 * len(new_ingredients))

        type_bonus = 0.0
        if candidate.dish_type:
            _, candidate_key = normalize_dish_type(candidate.dish_type)
            if candidate_key in required_type_keys and candidate_key not in covered_types:
                type_bonus = 0.35
            elif candidate_key not in required_type_keys:
                type_bonus = 0.05

        return 0.72 * candidate.score + 0.18 * feasibility + diversity_bonus + type_bonus

    if required_type_keys:
        for required_type_key in sorted(required_type_keys):
            best_pick = None
            best_pick_score = -1.0

            for candidate in candidates:
                if candidate.dish_name in {dish.dish_name for dish in selected}:
                    continue

                if not candidate.dish_type:
                    continue

                _, candidate_key = normalize_dish_type(candidate.dish_type)
                if candidate_key != required_type_key:
                    continue

                # Skip candidate if any required ingredient is not fully available given current remaining stock
                lacking = False
                for canonical_name, required_amount in candidate.required_consumption_base.items():
                    if quantity_coverage(required_amount, stock_remaining.get(canonical_name)) < 1.0:
                        lacking = True
                        break
                if lacking:
                    continue

                pick_score = candidate_pick_score(candidate)
                if pick_score > best_pick_score:
                    best_pick_score = pick_score
                    best_pick = candidate

            if best_pick is None:
                return []

            selected.append(best_pick)
            covered_types.add(required_type_key)

            for canonical_name, required_amount in best_pick.required_consumption_base.items():
                available_amount = stock_remaining.get(canonical_name)
                if available_amount is None:
                    continue
                stock_remaining[canonical_name] = max(0.0, available_amount - required_amount)

    while len(selected) < max_dishes:
        best_pick = None
        best_pick_score = -1.0

        selected_names = {dish.dish_name for dish in selected}

        for candidate in candidates:
            if candidate.dish_name in selected_names:
                continue

            if candidate.dish_type and required_type_keys and not _matches_required_types(candidate.dish_type, required_type_keys):
                continue

            # enforce full availability of required ingredients at selection time
            lacking = False
            for canonical_name, required_amount in candidate.required_consumption_base.items():
                if quantity_coverage(required_amount, stock_remaining.get(canonical_name)) < 1.0:
                    lacking = True
                    break
            if lacking:
                continue

            final_pick_score = candidate_pick_score(candidate)
            if final_pick_score > best_pick_score:
                best_pick_score = final_pick_score
                best_pick = candidate

        if best_pick is None:
            break

        selected.append(best_pick)

        if best_pick.dish_type:
            _, selected_key = normalize_dish_type(best_pick.dish_type)
            if selected_key:
                covered_types.add(selected_key)

        for canonical_name, required_amount in best_pick.required_consumption_base.items():
            available_amount = stock_remaining.get(canonical_name)
            if available_amount is None:
                continue
            stock_remaining[canonical_name] = max(0.0, available_amount - required_amount)

        if best_pick_score < 0.2:
            break

    if required_type_keys and not required_type_keys.issubset(covered_types):
        return []

    return selected


def load_and_recommend(
    recipe_path: str | Path,
    stock_path: str | Path,
    top_k: int = 10,
    max_dishes: int = 3,
    dish_type_filter: str | None = None,
    required_types: list[str] | None = None,
    max_minutes: int | None = None,
) -> dict[str, Any]:
    recipe_rows = load_json_array(recipe_path)
    stock_rows = load_json_array(stock_path)

    if dish_type_filter:
        filtered_recipe_rows = [recipe for recipe in recipe_rows if _recipe_matches_dish_type(recipe, dish_type_filter)]
    else:
        filtered_recipe_rows = recipe_rows

    filtered_recipe_rows = [recipe for recipe in filtered_recipe_rows if _recipe_within_time_limit(recipe, max_minutes)]

    # Updated: "tên" → "name"
    recipe_type_map = {
        str(recipe.get("name", "")).strip(): _recipe_dish_type(recipe)
        for recipe in filtered_recipe_rows
        if str(recipe.get("name", "")).strip()
    }

    ranked = rank_dishes(filtered_recipe_rows, stock_rows, top_k=top_k)
    # filter out dishes that do not have all main/required ingredients fulfilled
    ranked_filtered = [r for r in ranked if getattr(r, "required_fulfilled", True)]

    meal_set = recommend_meal_set(
        filtered_recipe_rows,
        stock_rows,
        max_dishes=max_dishes,
        dish_type_filter=dish_type_filter,
        required_types=required_types,
        max_minutes=max_minutes,
    )

    display_ranked = ranked_filtered or ranked

    return {
        "top_dishes": [
            {
                "dish_name": row.dish_name,
                "score": row.score,
                "missing_required": row.missing_required,
                "dish_type": row.dish_type or recipe_type_map.get(row.dish_name),
                "dish_type_filter": dish_type_filter,
                "ingredient_matches": [match.__dict__ for match in row.ingredient_matches],
            }
            for index, row in enumerate(display_ranked)
        ],
        "meal_set": [
            {
                "dish_name": row.dish_name,
                "score": row.score,
                "missing_required": row.missing_required,
                "dish_type": row.dish_type or recipe_type_map.get(row.dish_name),
                "dish_type_filter": dish_type_filter,
            }
            for index, row in enumerate(meal_set)
        ],
    }