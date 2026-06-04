#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NLP Processor for Vietnamese Recipe Ingredient Parsing
Dependencies: pip install underthesea pyvi
Usage: python3 nlp-processor.py <input_csv> [output_json]
"""

from underthesea import word_tokenize
import re
import json
import csv
import sys
from pprint import pprint
from pathlib import Path

# ============================================================================
# DICTIONARIES: Unit Conversions & Mass Definitions
# ============================================================================

# Từ điển quy đổi khối lượng trung bình
avg_unit_mass = {
    # Rau củ quả
    "hành tây": {"củ": 150},
    "tỏi": {"củ": 40, "tép": 5},
    "gừng": {"củ": 80},
    "khoai tây": {"củ": 180},
    "cà chua": {"quả": 120},
    "chanh": {"quả": 70},
    "cam": {"quả": 250},
    "trứng gà": {"quả": 55},
    "ớt": {"quả": 8},
    "dưa leo": {"quả": 200},
    "cà rốt": {"củ": 100},
    "bắp cải": {"cây": 1000, "củ": 800},
    "xà lách": {"cây": 300},
    "bí đỏ": {"quả": 2000},
    "bí xanh": {"quả": 800},
    "đu đủ": {"quả": 1500},
    "dứa": {"quả": 900},
    "thơm": {"quả": 900},
    "chuối": {"quả": 120},

    # Đơn vị bó
    "rau muống": {"bó": 200},
    "rau cải": {"bó": 250},
    "rau ngót": {"bó": 200},
    "rau dền": {"bó": 200},
    "rau má": {"bó": 150},
    "rau lang": {"bó": 200},
    "rau mồng tơi": {"bó": 250},
    "cải xanh": {"bó": 250},
    "cải ngọt": {"bó": 250},
    "hành lá": {"bó": 100},
    "rau răm": {"bó": 100},
    "rau thơm": {"bó": 100},
    "tía tô": {"bó": 100},
    "kinh giới": {"bó": 100},
    "ngò rí": {"bó": 80},
    "ngò gai": {"bó": 80},
    "cần tây": {"bó": 300},
}

# Từ điển quy đổi cho đơn vị đo lường
weight_units = {
    "kg": 1000,
    "ký": 1000,
    "cân": 1000,
    "lạng": 100,
    "g": 1,
    "gram": 1
}

# Đơn vị đếm
count_units = {
    "miếng": 40,
    "khoanh": 60
}

# ============================================================================
# INGREDIENT LISTS
# ============================================================================

veg = [
    "rau muống","rau cải","rau ngót","rau dền","rau má","rau lang","rau mồng tơi",
    "cải xanh","cải ngọt","cải thảo","bắp cải","cải xoăn","xà lách","diếp cá",
    "hành lá","hẹ","cần tây","cần nước","rau răm","rau thơm",
    "tía tô","kinh giới","ngò rí","ngò gai","lá lốt",
    "lá chanh","lá quế","đọt bí","bông bí","rau sam","hành tím","hành khô",
    "cà chua","dưa leo","dưa chuột","bí đỏ","bí xanh","bí đao",
    "mướp","khổ qua","cà tím","khoai tây"
]

meat = [
    "thịt bò","thịt heo","thịt lợn","thịt gà","thịt vịt","thịt dê","thịt cừu","thịt trâu","thịt ngan","thịt ngỗng","thịt thỏ",
    "sườn bò","bắp bò","gân bò","đuôi bò","tim bò","gan bò","lưỡi bò","óc bò",
    "sườn heo","sườn non","ba chỉ heo","ba rọi","nạc heo","mỡ heo","giò heo","chân giò","tai heo","đuôi heo","tim heo","gan heo","lòng heo","bao tử heo","cật heo","óc heo","phèo heo",
    "ức gà","đùi gà","cánh gà","chân gà","tim gà","gan gà","mề gà","cổ gà",
    "ức vịt","đùi vịt","cánh vịt","tim vịt","gan vịt","cổ vịt",
    "thịt xay","thịt băm",
    "tôm","cua","chả cua","ghẹ","mực","bạch tuộc",
    "cá hồi","cá thu","cá ngừ","cá basa",
    "cá rô","cá lóc","cá diêu hồng",
    "cá trê","cá cơm","cá chép",
    "sò","nghêu","hến","ốc",
    "lòng bò","lá lách bò","phổi bò","thực quản bò","bầu dục bò",
    "móng giò heo","đầu heo","mũi heo","má heo","lưỡi heo","huyết heo","tiết heo","mỡ heo non","bì heo","da heo","sụn heo","xương heo","xương ống heo","xương cục heo","lòng non heo","lòng già heo","dồi lòng","dạ dày heo",
    "lòng gà","mề vịt","da gà","da vịt","lòng ngan","mề ngan","gan ngan",
    "lòng dê","xương dê","đuôi cừu","sụn cừu",
    "đầu cá","xương cá","lườn cá","bụng cá","vây cá","đuôi cá","da cá","trứng cá","bao tử cá","gan cá","bong bóng cá","mỡ cá hồi",
    "đầu tôm","vỏ tôm","chân tôm","ruột tôm","mai mực","xương mực","lưỡi mực","thịt chân ốc","ruột ốc"
]

fruit = [
    "xoài","đu đủ","dứa","thơm","chuối",
    "táo","lê","cam","quýt","bưởi",
    "nho","dưa hấu","dưa lưới","thanh long",
    "vải","nhãn","mận"
]

spice = [
    "nước mắm","muối","đường","hạt nêm","bột ngọt",
    "tiêu","ớt","ớt bột","ớt tươi",
    "tỏi","gừng","sả","riềng","nghệ",
    "dầu ăn","dầu hào","nước tương","xì dầu",
    "hành tây"
]

starch = [
    "bánh phở", "bún", "miến", "mì", "mì tôm", "mì sợi",
    "nui", "macaroni", "spaghetti", "bánh đa", "bánh đa cua",
    "bánh canh", "hủ tiếu"
]

all_ing = set(veg + meat + fruit + spice + starch)

# Mapping tên con vật (ngắn) -> danh sách các biến thể nguyên liệu
animal_variants = {
    "cua": ["cua", "chả cua", "ghẹ"],
    "bò": ["thịt bò", "sườn bò", "bắp bò", "gân bò", "đuôi bò", "tim bò", "gan bò",
           "lưỡi bò", "óc bò", "lòng bò", "lá lách bò", "phổi bò", "thực quản bò", "bầu dục bò"],
    "heo": ["thịt heo", "thịt lợn", "sườn heo", "sườn non", "ba chỉ heo", "ba rọi",
            "nạc heo", "mỡ heo", "giò heo", "chân giò", "tai heo", "đuôi heo", "tim heo",
            "gan heo", "lòng heo", "bao tử heo", "cật heo", "óc heo", "phèo heo",
            "móng giò heo", "đầu heo", "mũi heo", "má heo", "lưỡi heo", "huyết heo",
            "tiết heo", "mỡ heo non", "bì heo", "da heo", "sụn heo", "xương heo",
            "xương ống heo", "xương cục heo", "lòng non heo", "lòng già heo", "dồi lòng",
            "dạ dày heo"],
    "lợn": ["thịt heo", "thịt lợn", "sườn heo", "sườn non", "ba chỉ heo", "ba rọi",
            "nạc heo", "mỡ heo", "giò heo", "chân giò", "tai heo", "đuôi heo", "tim heo",
            "gan heo", "lòng heo", "bao tử heo", "cật heo", "óc heo", "phèo heo"],
    "gà": ["thịt gà", "ức gà", "đùi gà", "cánh gà", "chân gà", "tim gà", "gan gà",
           "mề gà", "cổ gà", "lòng gà", "da gà"],
    "vịt": ["thịt vịt", "ức vịt", "đùi vịt", "cánh vịt", "tim vịt", "gan vịt",
            "cổ vịt", "mề vịt", "da vịt"],
    "ngan": ["thịt ngan", "lòng ngan", "mề ngan", "gan ngan"],
    "dê": ["thịt dê", "lòng dê", "xương dê"],
    "cừu": ["thịt cừu", "đuôi cừu", "sụn cừu"],
    "tôm": ["tôm", "đầu tôm", "vỏ tôm", "chân tôm", "ruột tôm"],
    "mực": ["mực", "bạch tuộc", "mai mực", "xương mực", "lưỡi mực"],
    "cá": ["cá hồi", "cá thu", "cá ngừ", "cá basa", "cá rô", "cá lóc", "cá diêu hồng",
           "cá trê", "cá cơm", "cá chép", "đầu cá", "xương cá", "lườn cá", "bụng cá",
           "vây cá", "đuôi cá", "da cá", "trứng cá", "bao tử cá", "gan cá", "bong bóng cá",
           "mỡ cá hồi"],
    "ốc": ["ốc", "sò", "nghêu", "hến", "thịt chân ốc", "ruột ốc"]
}

# ============================================================================
# PROCESSING FUNCTIONS
# ============================================================================

def get_dish(text):
    """Trích xuất tên món ăn"""
    text = text.lower()
    first = text.strip().split("\n")[0]

    if "nguyên liệu" in text:
        first = text.split("nguyên liệu")[0]

    tokens = word_tokenize(first, format="text")
    return tokens.strip()


def contains_phrase(text, phrase):
    """Kiểm tra cụm từ có trong văn bản"""
    pattern = r"\b" + re.escape(phrase) + r"\b"
    return re.search(pattern, text) is not None


def get_main(name, max_main=4):
    """Xác định nguyên liệu chính từ tên món ăn"""
    if not name:
        return []

    name = name.lower().strip()
    mains = []

    # Món ăn -> tinh bột
    dish_to_starch = {
        "phở": "bánh phở",
        "bún": "bún",
        "miến": "miến",
        "mì": "mì",
        "hủ tiếu": "hủ tiếu",
        "bánh canh": "bánh canh",
        "bánh đa": "bánh đa"
    }

    # Món ăn -> protein
    dish_to_protein = {
        "phở bò": "thịt bò",
        "phở gà": "thịt gà",
        "bún bò": "thịt bò",
        "bún riêu": "cua",
        "miến gà": "thịt gà",
        "cháo lòng": "lòng heo",
        "bún chả": "thịt heo",
        "mì quảng": "thịt heo",
        "phở cuốn": "thịt bò"
    }

    # 1. Tìm tinh bột
    for keyword, starch_item in sorted(dish_to_starch.items(), key=lambda x: len(x[0]), reverse=True):
        if contains_phrase(name, keyword):
            mains.append(starch_item)
            break

    # 2. Tìm protein chính
    for dish, protein in sorted(dish_to_protein.items(), key=lambda x: len(x[0]), reverse=True):
        if contains_phrase(name, dish):
            if protein not in mains:
                mains.append(protein)

    # 3. Tìm nguyên liệu khác
    all_items = meat + veg + fruit
    all_items = sorted(all_items, key=len, reverse=True)

    for item in all_items:
        if len(mains) >= max_main:
            break
        if contains_phrase(name, item):
            if item not in mains:
                mains.append(item)

    return mains[:max_main]


def convert_to_grams(value, unit, ingredient_name=None):
    """Chuyển đổi giá trị và đơn vị thành gram"""
    if not unit:
        return {"value": value, "unit": unit}

    unit = unit.lower()

    # Xử lý đơn vị trọng lượng
    if unit in weight_units:
        value *= weight_units[unit]
        return {"value": value, "unit": "g"}

    # Xử lý đơn vị đếm đặc biệt (củ, quả, tép, cây, bó)
    elif unit in ["củ", "quả", "tép", "cây", "bó"]:
        if ingredient_name and ingredient_name in avg_unit_mass:
            if unit in avg_unit_mass[ingredient_name]:
                avg_mass = avg_unit_mass[ingredient_name][unit]
                value *= avg_mass
                return {"value": value, "unit": "g"}

    # Xử lý đơn vị đếm có sẵn (miếng, khoanh)
    elif unit in count_units:
        value *= count_units[unit]
        return {"value": value, "unit": "g"}

    # Không thể chuyển đổi, giữ nguyên
    return {"value": value, "unit": unit}


def parse_quantity(quantity_text, ingredient_name=None):
    """Parse chuỗi số lượng và đơn vị"""
    if not quantity_text:
        return None

    quantity_text = quantity_text.lower().strip()

    # Pattern cho số thập phân
    pattern = r"(\d+(?:\.\d+)?)\s*([a-zàáãạảăắằặẵâấầậẫẩđêễệểếéèẻẽẹóòỏõọôốồổỗộơớờởỡợíìỉĩịúùủũụưứừửữựýỳỷỹỵ]+)?"

    match = re.search(pattern, quantity_text)
    if not match:
        return None

    try:
        value = float(match.group(1))
    except ValueError:
        return None

    unit = match.group(2) if match.group(2) else None

    if unit:
        return convert_to_grams(value, unit, ingredient_name)

    return {"value": value, "unit": None}


def find_ingredients_with_quantity(text):
    """Tìm tất cả nguyên liệu và số lượng trong văn bản"""
    if not text:
        return []

    text = text.lower()
    matches = []

    # Pattern cho số lượng
    quantity_pattern = r"(\d+(?:\.\d+)?)\s*([a-zàáãạảăắằặẵâấầậẫẩđêễệểếéèẻẽẹóòỏõọôốồổỗộơớờởỡợíìỉĩịúùủũụưứừửữựýỳỷỹỵ]+)?"

    # Sắp xếp nguyên liệu theo độ dài giảm dần
    sorted_ing = sorted(all_ing, key=len, reverse=True)

    for ing in sorted_ing:
        pattern = r"\b" + re.escape(ing) + r"\b"

        for match in re.finditer(pattern, text):
            quantity_text = None

            # Tìm số lượng đằng trước
            before_start = max(0, match.start() - 20)
            before_text = text[before_start:match.start()]
            quantity_match = re.search(quantity_pattern + r"\s*$", before_text)

            if quantity_match:
                quantity_text = quantity_match.group(0).strip()
            else:
                # Tìm số lượng đằng sau
                after_end = min(len(text), match.end() + 20)
                after_text = text[match.end():after_end]
                quantity_match = re.search(r"^\s*" + quantity_pattern, after_text)
                if quantity_match:
                    quantity_text = quantity_match.group(0).strip()

            matches.append({
                "ingredient": ing,
                "quantity_text": quantity_text,
                "start": match.start(),
                "end": match.end(),
                "length": len(ing)
            })

    # Xử lý overlap
    matches.sort(key=lambda x: (x["start"], -x["length"]))

    filtered = []
    occupied = []

    for m in matches:
        overlap = False
        for s, e in occupied:
            if not (m["end"] <= s or m["start"] >= e):
                overlap = True
                break

        if not overlap:
            filtered.append((m["ingredient"], m["quantity_text"], m["start"]))
            occupied.append((m["start"], m["end"]))

    return filtered


def is_main_ingredient(ing, mains):
    """Kiểm tra nguyên liệu có phải main dựa trên tên món ăn (chỉ cần trùng tên con vật)"""
    if ing in mains:
        return True

    for animal, variants in animal_variants.items():
        if animal in mains:
            if ing in variants:
                return True

    return False


def extract(name, ingredients_text, include_spice_quantity=True):
    """Trích xuất danh sách nguyên liệu từ tên món ăn và văn bản nguyên liệu

    Args:
        name: Tên món ăn
        ingredients_text: Văn bản chứa nguyên liệu
        include_spice_quantity:
            - True  -> giữ số lượng/đơn vị của gia vị
            - False -> bỏ số lượng/đơn vị của gia vị
    """

    if not ingredients_text:
        return []

    text = ingredients_text.lower()
    mains = get_main(name)

    out = []
    ingredients_found = find_ingredients_with_quantity(text)

    for ing, quantity_text, _ in ingredients_found:
        item = {
            "ingredient": ing,
            "value": None,
            "unit": None,
            "type": None
        }

        # Phân loại nguyên liệu trước
        if ing in spice:
            item["type"] = "optional"
        elif is_main_ingredient(ing, mains):
            item["type"] = "main"
        else:
            item["type"] = "required"

        # Nếu là spice và không muốn lưu quantity
        if item["type"] == "optional" and not include_spice_quantity:
            pass
        else:
            # Parse số lượng nếu có
            if quantity_text:
                parsed = parse_quantity(quantity_text, ing)
                if parsed:
                    item["value"] = parsed["value"]
                    item["unit"] = parsed["unit"]

        out.append(item)

    return out


def group(data):
    """Nhóm nguyên liệu theo loại"""
    res = {}
    res["main"] = []
    res["required"] = []
    res["optional"] = []

    for x in data:
        res[x["type"]].append(x)

    return res


def format_weight(value, unit):
    """Format weight for display"""
    if value is None:
        return None
    
    # Format number: remove .0 if integer
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    
    if unit and unit != "g":
        return f"{value} {unit}"
    elif unit == "g":
        return f"{value} g"
    elif value:
        return str(value)
    else:
        return None


def convert_to_json_format(dish_name, grouped_data):
    """Convert grouped result to format expected by KG pipeline"""
    output = {
        "tên": dish_name,
        "thời gian": None,
        "số người": None,
        "độ khó": None,
        "nguyên liệu chính": [],
        "nguyên liệu phụ_1 cần thiết": [],
        "nguyên liệu phụ_2 có thể bỏ qua": [],
        "cách chế biến": None
    }
    
    # Main ingredients
    for item in grouped_data.get("main", []):
        ingredient = item["ingredient"]
        quantity = item["value"] if item["value"] is not None else 1
        unit = item["unit"] if item["unit"] else ""
        khoi_luong = f"{quantity} {unit}".strip() if quantity else ingredient
        
        output["nguyên liệu chính"].append({
            "tên": ingredient,
            "khối lượng": khoi_luong
        })

    # Required ingredients
    for item in grouped_data.get("required", []):
        ingredient = item["ingredient"]
        quantity = item["value"] if item["value"] is not None else 1
        unit = item["unit"] if item["unit"] else ""
        khoi_luong = f"{quantity} {unit}".strip() if quantity else ingredient
        
        output["nguyên liệu phụ_1 cần thiết"].append({
            "tên": ingredient,
            "khối lượng": khoi_luong
        })

    # Optional ingredients
    for item in grouped_data.get("optional", []):
        ingredient = item["ingredient"]
        output["nguyên liệu phụ_2 có thể bỏ qua"].append({
            "tên": ingredient,
            "khối lượng": None
        })

    return output


# ============================================================================
# MAIN / TESTING
# ============================================================================

def process_csv(input_csv, output_json=None):
    """Process CSV file and output JSON with cooking procedure"""
    if not Path(input_csv).exists():
        print(f"❌ Error: File '{input_csv}' not found")
        return False
    
    if output_json is None:
        output_json = Path(input_csv).stem + "_processed.json"
    
    print(f"📖 Reading CSV: {input_csv}\n")
    
    recipes = []
    error_count = 0
    skipped_count = 0
    total_rows = 0
    
    try:
        with open(input_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            if reader.fieldnames:
                print(f"📋 Columns detected: {reader.fieldnames}")
            
            for idx, row in enumerate(reader, start=1):
                total_rows = idx
                dish_name = row.get('tên', '').strip()
                ingredients_text = row.get('nguyên liệu', '').strip()
                
                # Extract cooking procedure
                procedure_text = row.get('cách chế biến', '').strip()
                
                # Extract metadata
                cooking_time = row.get('thời gian', '').strip()
                servings = row.get('số người', '').strip()
                difficulty = row.get('độ khó', '').strip()
                
                if not dish_name or dish_name == 'N/A':
                    skipped_count += 1
                    continue
                
                if not ingredients_text:
                    skipped_count += 1
                    if idx <= 10:
                        print(f"  ⊘ Skipped [{idx}] {dish_name[:50]}... (no ingredients)")
                    continue
                
                try:
                    if idx <= 5:
                        print(f"  ✓ Processing [{idx}] {dish_name[:50]}...")
                    
                    extracted = extract(dish_name, ingredients_text)
                    grouped = group(extracted)
                    
                    # Convert to JSON format with procedure
                    json_item = convert_to_json_format(dish_name, grouped)
                    
                    # Add metadata
                    json_item["thời gian"] = cooking_time if cooking_time else None
                    json_item["số người"] = servings if servings else None
                    json_item["độ khó"] = difficulty if difficulty else None
                    
                    # Add cooking procedure (parse steps if needed)
                    if procedure_text:
                        # Split into steps if separated by "|"
                        if '|' in procedure_text:
                            steps = [step.strip() for step in procedure_text.split('|') if step.strip()]
                            json_item["cách chế biến"] = steps
                        elif 'Bước' in procedure_text or 'Step' in procedure_text:
                            # Keep as text but preserve structure
                            json_item["cách chế biến"] = procedure_text
                        else:
                            json_item["cách chế biến"] = procedure_text
                    else:
                        json_item["cách chế biến"] = None
                    
                    recipes.append(json_item)
                    
                except Exception as e:
                    error_count += 1
                    print(f"  ✗ Error processing row {idx}: {str(e)}")
                    continue
    
    except Exception as e:
        print(f"❌ Error reading CSV: {str(e)}")
        return False
    
    # Save to JSON
    try:
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(recipes, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Success!")
        print(f"   Total rows: {total_rows}")
        print(f"   Processed: {len(recipes)} recipes")
        print(f"   Skipped: {skipped_count} rows (missing name or ingredients)")
        if error_count > 0:
            print(f"   Errors: {error_count}")
        print(f"   Output: {output_json}")
        return True
        
    except Exception as e:
        print(f"❌ Error writing JSON: {str(e)}")
        return False


def test_sample():
    """Test with sample data"""
    name = "Bún cua"

    ingredients = """
    0.5kg bún tươi, 3 lạng thịt bò, 2 khoanh giò heo, 0.2kg chả cua,
    1 bó rau muống, 1 bó rau răm, 1 củ hành tây, 3 cây sả,
    1 miếng riềng, 2 muỗng mắm ruốc, 1 muỗng ớt bột, 1 muỗng dầu ăn,
    2 muỗng nước mắm, 1 muỗng đường, 1 ít muối, 2 quả chanh, ớt tươi
    """

    print("=" * 50)
    print("New JSON Output Format:")
    print("=" * 50)
    result = group(extract(name, ingredients))
    json_data = convert_to_json_format(name, result, "30 phút", "4 người", "trung bình")
    print(json.dumps(json_data, ensure_ascii=False, indent=2))


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python3 nlp-processor.py <input_csv> [output_json]")
        print("\nExample:")
        print("  python3 nlp-processor.py raw_data_CP.csv recipes.json")
        print("\nOr run test:")
        print("  python3 nlp-processor.py --test")
        sys.exit(1)
    
    if sys.argv[1] == "--test":
        test_sample()
    else:
        input_csv = sys.argv[1]
        output_json = sys.argv[2] if len(sys.argv) > 2 else None
        process_csv(input_csv, output_json)


if __name__ == "__main__":
    main()