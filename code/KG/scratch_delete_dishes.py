import json
from pathlib import Path

payload_path = Path("result/kg_payload.json")
with open(payload_path, "r", encoding="utf-8") as f:
    data = json.load(f)

dishes_to_remove = {
    "MÌ spaghetti sốt tôm-rau củ",
    "Cơm Rang Dưa Bò",
    "Pate Nấm và Khoai Lang Chay"
}

# Filter dish_rows
original_dish_count = len(data["dish_rows"])
data["dish_rows"] = [d for d in data["dish_rows"] if d["name"] not in dishes_to_remove]
new_dish_count = len(data["dish_rows"])

# Filter ingredient_rows
original_ing_count = len(data["ingredient_rows"])
data["ingredient_rows"] = [i for i in data["ingredient_rows"] if i["dish_name"] not in dishes_to_remove]
new_ing_count = len(data["ingredient_rows"])

with open(payload_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Removed {original_dish_count - new_dish_count} dishes and {original_ing_count - new_ing_count} ingredients.")
