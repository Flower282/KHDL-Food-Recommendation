import pandas as pd
import re
import os
import json

# Cấu hình file
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULT_DIR = os.path.join(PROJECT_ROOT, 'result')
INPUT_FILE = os.path.join(RESULT_DIR, 'tong_hop_mon_an_viet_nam.csv')
OUTPUT_WITH_WEIGHT_FILE = os.path.join(RESULT_DIR, 'data_monan_sach_co_khoi_luong.csv')
OUTPUT_NO_WEIGHT_FILE = os.path.join(RESULT_DIR, 'data_monan_sach_khong_khoi_luong.csv')
OUTPUT_JSON_FILE = os.path.join(RESULT_DIR, 'data_monan_day_du.json')

OPTIONAL_INGREDIENT_KEYWORDS = [
    'muối', 'đường', 'tiêu', 'ớt', 'tương', 'xì dầu', 'nước tương', 'nước mắm', 'gia vị','Aji-Quick',
    'mắm', 'dầu ăn', 'dầu hào', 'bột ngọt', 'hạt nêm', 'bột nêm', 'giấm',
    'sa tế', 'ngũ vị hương', 'bơ', 'rượu', 'mật ong', 'mè', 'vừng'
]

COOKING_METHOD_KEYWORDS = [
    'xào', 'kho', 'canh', 'hấp', 'chiên', 'nướng', 'lẩu', 'sốt', 'ram', 'chưng', 'trộn', 'cuộn', 'xốt'
]

GENERIC_MATCH_WORDS = {
    'vị', 'gia', 'món', 'kiểu', 'đặc', 'biệt', 'thơm', 'ngon'
}

CORE_MAIN_WORDS = {
    'thịt', 'bò', 'lợn', 'heo', 'gà', 'vịt', 'cá', 'tôm', 'mực', 'cua', 'ghẹ',
    'ốc', 'lươn', 'ếch', 'trứng', 'đậu', 'sườn', 'hải', 'sản'
}

EXCLUDED_INGREDIENT_PREFIXES = [
    'lấy', 'cho', 'thêm', 'để', 'dùng', 'bỏ', 'trộn', 'rửa', 'ngâm', 'thái', 'cắt',
    'băm', 'xắt', 'chặt', 'đập', 'giã', 'xay', 'phi', 'ướp', 'nêm', 'nấu', 'luộc',
    'rán', 'chiên', 'xào', 'hấp', 'nướng', 'khuấy', 'đánh', 'vắt', 'lọc', 'bóc',
    'gọt', 'tỉa', 'xếp', 'xay nhuyễn', 'xào sơ', 'phi thơm','món','chà rửa',
    'đánh tan','ướp với','ướp cùng','ướp trong','ướp ngoài','không','vạt','xiên','lột',
    'đổ','ăn','giữ','to','chần',
]

STANDARD_UNIT_ALIASES = {
    'gr': 'g',
    'gram': 'g',
    'kilogram': 'kg',
    'lít': 'l',
    'lit': 'l',
    'ml': 'ml',
    'mL': 'ml',
    'trái': 'quả',
    'muỗng cà phê': 'muỗng cà phê',
    'muỗng canh': 'muỗng canh',
    'muỗng': 'muỗng',
    'thìa': 'thìa',
    'chén': 'chén',
    'cốc': 'cốc',
    'hộp': 'hộp',
    'miếng': 'miếng',
    'vắt': 'vắt',
    'gói': 'gói',
    'hũ': 'hũ',
    'cái': 'cái',
    'lát': 'lát',
    'bát': 'bát',
    'quả': 'quả',
    'tép': 'tép',
    'tô': 'tô',
    'con': 'con',
    'củ': 'củ',
}

COUNT_UNIT_KEYWORDS = {
    'con': [
        'gà', 'vịt', 'cá', 'tôm', 'mực', 'cua', 'ghẹ', 'lươn', 'ếch', 'ốc', 'sò',
        'hến', 'ngao', 'nghêu', 'bạch tuộc', 'chim', 'sứa', 'lòng', 'trứng vịt lộn',
    ],
    'quả': [
        'trứng', 'chanh', 'cam', 'quýt', 'bưởi', 'táo', 'lê', 'chuối', 'xoài', 'đu đủ',
        'dứa', 'thơm', 'dưa', 'cà chua', 'ớt', 'me', 'na', 'mận', 'ổi', 'cóc', 'sapoche',
    ],
    'cái': [
        'đậu hũ', 'đậu phụ', 'bánh tráng', 'bánh', 'lá', 'miếng', 'cái', 'hạt', 'viên',
        'quẩy', 'nem', 'chả', 'phở', 'bún', 'mì', 'bánh đa', 'tàu hũ', 'bánh mì',
    ],
}

QUANTITY_UNIT_PATTERN = r'(?:muỗng\s*cà\s*phê|muỗng\s*canh|muỗng|thìa|chén|cốc|kg|gr|g|ml|lít|lit|l|M|m|trái|quả|củ|con|hộp|miếng|vắt|gói|hũ|cái|lát|bát|tép|tô)'


def _contains_keyword(text, keywords):
    normalized_text = re.sub(r'\s+', ' ', str(text).strip().lower())
    return any(re.search(rf'(?<!\w){re.escape(keyword)}(?!\w)', normalized_text) for keyword in keywords)


def normalize_unit(unit):
    if not unit:
        return unit

    normalized_unit = re.sub(r'\s+', ' ', str(unit).strip().lower())
    return STANDARD_UNIT_ALIASES.get(normalized_unit, normalized_unit)


def extract_display_name(ingredient_text):
    base_text = str(ingredient_text).split(':', 1)[0].strip()
    base_text = re.sub(
        rf'\s*\d+[\d\.,/]*\s*{QUANTITY_UNIT_PATTERN}\b.*$',
        '',
        base_text,
        flags=re.IGNORECASE,
    )
    base_text = clean_special_characters(base_text)
    return re.sub(r'\s+', ' ', base_text).strip(' -/\t')


def extract_quantity_and_unit(ingredient_text):
    text = str(ingredient_text).strip()
    if not text:
        return None, None

    normalized_text = re.sub(r'\s+', ' ', text).strip()
    match = re.search(
        rf'(\d+[\d\.,/]*)\s*({QUANTITY_UNIT_PATTERN})\b',
        normalized_text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None, None

    quantity = match.group(1).replace(' ', '')
    unit = normalize_unit(match.group(2))
    return quantity, unit


def infer_default_unit(ingredient_name):
    normalized_name = re.sub(r'\s+', ' ', str(ingredient_name).strip().lower())

    for unit, keywords in COUNT_UNIT_KEYWORDS.items():
        if _contains_keyword(normalized_name, keywords):
            return unit

    return 'g'


def standardize_ingredient_text(ingredient_text, is_optional=False):
    display_name = extract_display_name(ingredient_text)
    quantity, unit = extract_quantity_and_unit(ingredient_text)

    if quantity and unit:
        standardized_text = f'{display_name} {quantity}{unit}'
        return {
            'raw': str(ingredient_text).strip(),
            'name': display_name,
            'quantity': quantity,
            'unit': unit,
            'standardized': standardized_text,
            'is_optional': is_optional,
            'is_defaulted': False,
        }

    if is_optional:
        return {
            'raw': str(ingredient_text).strip(),
            'name': display_name,
            'quantity': None,
            'unit': None,
            'standardized': display_name,
            'is_optional': True,
            'is_defaulted': False,
        }

    default_unit = infer_default_unit(display_name)
    if default_unit in {'con', 'quả', 'cái'}:
        standardized_text = f'{display_name} 1 {default_unit}'
        quantity = '1'
        unit = default_unit
    else:
        standardized_text = f'{display_name} 100g'
        quantity = '100'
        unit = 'g'

    return {
        'raw': str(ingredient_text).strip(),
        'name': display_name,
        'quantity': quantity,
        'unit': unit,
        'standardized': standardized_text,
        'is_optional': False,
        'is_defaulted': True,
    }


def split_text_block_to_list(text_block):
    if pd.isna(text_block) or not str(text_block).strip():
        return []

    return [line for line in str(text_block).split('\n') if line.strip()]


def to_json_compatible(value):
    if isinstance(value, (list, tuple)):
        return [to_json_compatible(item) for item in value]

    if isinstance(value, dict):
        return {key: to_json_compatible(item) for key, item in value.items()}

    if pd.isna(value):
        return None

    if hasattr(value, 'item'):
        try:
            return value.item()
        except Exception:
            pass

    return value

def clean_description(text):
    """
    Xóa phần mô tả thừa sau đơn vị định lượng.
    Ví dụ: 'Thịt bò 300g cắt lát mỏng' -> 'Thịt bò 300g'
    """
    # Danh sách các đơn vị phổ biến
    units = r'(g|gr|kg|ml|l|chén|muỗng|M|m|trái|củ|con|hộp|miếng|vắt|gói|hũ|cái|lát|bát|quả|tép|tô|thìa)'
    
    # Regex: Tìm phần text có chứa số + đơn vị, và lấy phần đó, bỏ phần sau
    # Giải thích: (.*?\d+\s*units) -> lấy đến hết đơn vị. \b.* -> bỏ qua mọi thứ sau ranh giới từ đó.
    pattern = rf'^(.*?\d+\s*{units})\b.*'
    
    match = re.match(pattern, text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


def remove_ingredient_quantity(ingredient_text):
    """
    Bỏ phần khối lượng khỏi một dòng nguyên liệu.
    Ví dụ: 'Tôm sú tươi: 250g' -> 'Tôm sú tươi'
    """
    text = ingredient_text.strip()
    if not text:
        return text

    if ':' in text:
        return text.split(':', 1)[0].strip()

    text = re.sub(
        r'\s*\d+[\d\.,/]*\s*(g|gr|kg|ml|l|chén|muỗng|m|M|trái|củ|con|hộp|miếng|vắt|gói|hũ|cái|lát|bát|quả|tép|tô|thìa)\b.*$',
        '',
        text,
        flags=re.IGNORECASE,
    )
    return text.strip()


def clean_special_characters(text):
    """
    Loại bỏ các ký tự lạ còn sót lại, nhưng giữ chữ tiếng Việt, số, khoảng trắng
    và một vài ký tự cần thiết trong tên nguyên liệu.
    """
    text = str(text).replace('_', ' ')
    text = re.sub(r'[®™©]', '', text)
    text = re.sub(r'[\(\)\[\]\{\}]', ' ', text)
    text = re.sub(r'[^\w\sÀ-ỹ\-\/]', '', text, flags=re.UNICODE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip(' -/\t')


def remove_number_and_after(text):
    """
    Nếu tên nguyên liệu còn chứa số thì cắt từ vị trí số đầu tiên trở đi.
    Ví dụ: 'rau muống 1 bó' -> 'rau muống'
    """
    cleaned_text = str(text).strip()
    match = re.search(r'\d', cleaned_text)
    if match:
        cleaned_text = cleaned_text[:match.start()]
    return cleaned_text.strip(' -/\t')


def starts_with_excluded_prefix(text):
    """
    Loại các dòng nguyên liệu bắt đầu bằng động từ/cụm động từ sai.
    """
    normalized_text = re.sub(r'\s+', ' ', str(text).strip().lower())
    return any(
        normalized_text == prefix or normalized_text.startswith(prefix + ' ')
        for prefix in EXCLUDED_INGREDIENT_PREFIXES
    )


def split_ingredient_entries(raw_text):
    """
    Tách một cụm nguyên liệu thành các dòng riêng lẻ.
    Ưu tiên tách theo dấu xuống dòng sẵn có, rồi tách thêm theo dấu |, dấu phẩy và chấm phẩy.
    """
    entries = []
    for line in str(raw_text).split('\n'):
        parts = re.split(r'[|;,]', line)
        for part in parts:
            part = part.strip()
            if part:
                entries.append(part)
    return entries


def deduplicate_preserve_order(items):
    """
    Loại bỏ phần tử trùng nhau nhưng vẫn giữ thứ tự xuất hiện ban đầu.
    So sánh theo dạng chữ thường và đã chuẩn hóa khoảng trắng.
    """
    seen = set()
    unique_items = []

    for item in items:
        clean_item = str(item).strip()
        normalized_key = re.sub(r'\s+', ' ', clean_item).lower()

        if not normalized_key or normalized_key in seen:
            continue

        seen.add(normalized_key)
        unique_items.append(clean_item)

    return unique_items


def remove_ingredient_quantities_block(block_text):
    """
    Bỏ phần khối lượng trên từng dòng nguyên liệu trong cả khối text.
    """
    if pd.isna(block_text):
        return block_text

    lines = [remove_ingredient_quantity(line) for line in split_ingredient_entries(block_text)]
    lines = [clean_special_characters(line) for line in lines]
    lines = [remove_number_and_after(line) for line in lines]
    lines = [line for line in lines if line and not starts_with_excluded_prefix(line)]
    lines = deduplicate_preserve_order(lines)
    return '\n'.join(line for line in lines if line)


def extract_ingredient_name(ingredient_text):
    """
    Lấy tên nguyên liệu cốt lõi để phân loại.
    Ví dụ: "Nước mắm: 2 muỗng" -> "nước mắm"
    """
    base_text = ingredient_text.split(':')[0].strip().lower()
    # Bỏ phần định lượng ở cuối để giữ lại tên nguyên liệu.
    base_text = re.sub(r'\s+\d+[\d\.,/]*\s*(g|gr|kg|ml|l|chén|muỗng|M|m|trái|củ|con|hộp|miếng|vắt|gói|hũ|cái|lát|bát|quả|tép|tô|thìa)?\b.*$', '', base_text, flags=re.IGNORECASE)
    return base_text.strip()


def is_optional_ingredient(ingredient_text):
    ingredient_name = extract_ingredient_name(ingredient_text)
    return any(keyword in ingredient_name for keyword in OPTIONAL_INGREDIENT_KEYWORDS)


def get_meaningful_words(text):
    words = re.findall(r'\w+', text.lower(), flags=re.UNICODE)
    return [w for w in words if w not in COOKING_METHOD_KEYWORDS and w not in GENERIC_MATCH_WORDS]


def is_main_ingredient(dish_name, ingredient_name):
    dish_words = set(get_meaningful_words(dish_name))
    ingredient_words = set(get_meaningful_words(ingredient_name))

    if not ingredient_words:
        return False

    overlap = dish_words & ingredient_words
    overlap_count = len(overlap)

    # Đủ mạnh khi trùng ít nhất 2 từ có nghĩa.
    if overlap_count >= 2:
        return True

    # Chỉ trùng 1 từ thì chỉ chấp nhận nếu là nhóm từ chính (thịt/cá/tôm...).
    if overlap_count == 1 and any(word in CORE_MAIN_WORDS for word in overlap):
        return True

    # Nếu tên nguyên liệu (có ít nhất 2 từ có nghĩa) nằm trọn trong tên món thì coi là chính.
    ingredient_phrase = " ".join(get_meaningful_words(ingredient_name)).strip()
    if ingredient_phrase and len(ingredient_phrase.split()) >= 2 and ingredient_phrase in dish_name.lower():
        return True

    return False


def parse_minutes(time_value):
    """
    Tách số phút từ cột thời gian.
    Trả về int phút nếu đọc được, ngược lại trả None.
    """
    if pd.isna(time_value):
        return None

    text = str(time_value).strip().lower()
    match = re.search(r'(\d+)', text)
    if not match:
        return None

    return int(match.group(1))

def process_ingredients(row):
    dish_name = str(row['tên']).lower()
    # Tách các nguyên liệu từ dấu |
    raw_list = [] if pd.isna(row['nguyên liệu']) else str(row['nguyên liệu']).split('|')
    
    main_list = []
    sub_list = []
    sub_required_list = []
    sub_optional_list = []
    ingredient_details = []
    
    for raw_item in raw_list:
        for split_item in split_ingredient_entries(raw_item):
            # 1. Làm sạch mô tả thừa
            cleaned_item = clean_description(split_item.strip())
            if not cleaned_item:
                continue
            if starts_with_excluded_prefix(cleaned_item):
                continue

            # 2. Phân loại chính/phụ (Dựa trên tên nguyên liệu trước dấu :)
            ingre_name = extract_ingredient_name(cleaned_item)
            is_main = False
            is_optional = is_optional_ingredient(cleaned_item)

            # Gia vị/nước chấm luôn không phải nguyên liệu chính.
            if not is_optional:
                is_main = is_main_ingredient(dish_name, ingre_name)

            standardized_ingredient = standardize_ingredient_text(cleaned_item, is_optional=is_optional)
            ingredient_details.append(
                {
                    'nhom': 'nguyên liệu chính' if is_main else ('nguyên liệu phụ_2 có thể bỏ qua' if is_optional else 'nguyên liệu phụ_1 cần thiết'),
                    'goc': standardized_ingredient['raw'],
                    'ten': standardized_ingredient['name'],
                    'so_luong': standardized_ingredient['quantity'],
                    'don_vi': standardized_ingredient['unit'],
                    'chuan_hoa': standardized_ingredient['standardized'],
                    'la_nguyen_lieu_phu_tu_nguyen': is_optional,
                    'da_mac_dinh_dinh_luong': standardized_ingredient['is_defaulted'],
                }
            )

            if is_main:
                main_list.append(standardized_ingredient['standardized'])
            else:
                sub_list.append(standardized_ingredient['standardized'])
                if is_optional:
                    sub_optional_list.append(standardized_ingredient['standardized'])
                else:
                    sub_required_list.append(standardized_ingredient['standardized'])

    main_list = deduplicate_preserve_order(main_list)
    sub_list = deduplicate_preserve_order(sub_list)
    sub_required_list = deduplicate_preserve_order(sub_required_list)
    sub_optional_list = deduplicate_preserve_order(sub_optional_list)
            
    # 3. Trả về kết quả nối bằng dấu xuống dòng (\n)
    return pd.Series({
        'nguyên liệu chính': "\n".join(main_list),
        'nguyên liệu phụ': "\n".join(sub_list),
        'nguyên liệu phụ_1 cần thiết': "\n".join(sub_required_list),
        'nguyên liệu phụ_2 có thể bỏ qua': "\n".join(sub_optional_list),
        'nguyên liệu chi tiết': ingredient_details,
    })


def build_recipe_json_record(row):
    ingredient_details = to_json_compatible(row['nguyên liệu chi tiết']) or []

    def format_ingredient_payload(item):
        quantity = item.get('so_luong')
        unit = item.get('don_vi')

        if quantity and unit:
            normalized_amount = f"{quantity} {unit}"
        elif quantity:
            normalized_amount = str(quantity)
        else:
            normalized_amount = None

        return {
            'tên': item.get('ten'),
            'khối lượng': normalized_amount,
        }

    main_items = [
        format_ingredient_payload(item)
        for item in ingredient_details
        if item.get('nhom') == 'nguyên liệu chính'
    ]
    sub_required_items = [
        format_ingredient_payload(item)
        for item in ingredient_details
        if item.get('nhom') == 'nguyên liệu phụ_1 cần thiết'
    ]
    sub_optional_items = [
        format_ingredient_payload(item)
        for item in ingredient_details
        if item.get('nhom') == 'nguyên liệu phụ_2 có thể bỏ qua'
    ]

    return {
        'tên': to_json_compatible(row['tên']),
        'thời gian': to_json_compatible(row['thời gian']),
        'số người': to_json_compatible(row['số người']),
        'độ khó': to_json_compatible(row['độ khó']),
        'nguyên liệu chính': main_items,
        'nguyên liệu phụ_1 cần thiết': sub_required_items,
        'nguyên liệu phụ_2 có thể bỏ qua': sub_optional_items,
    }

def main():
    try:
        os.makedirs(RESULT_DIR, exist_ok=True)
        print(f"Đang xử lý file: {INPUT_FILE}...")
        df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')

        # Bỏ các món có thời gian nấu bằng 0 phút.
        original_count = len(df)
        df = df[df['thời gian'].apply(lambda x: parse_minutes(x) != 0)].copy()
        removed_count = original_count - len(df)
        
        # Áp dụng hàm xử lý
        new_data = df.apply(process_ingredients, axis=1)
        
        # Ghép vào dataframe và sắp xếp cột
        df['nguyên liệu chính'] = new_data['nguyên liệu chính']
        df['nguyên liệu phụ'] = new_data['nguyên liệu phụ']
        df['nguyên liệu phụ_1 cần thiết'] = new_data['nguyên liệu phụ_1 cần thiết']
        df['nguyên liệu phụ_2 có thể bỏ qua'] = new_data['nguyên liệu phụ_2 có thể bỏ qua']
        df['nguyên liệu chi tiết'] = new_data['nguyên liệu chi tiết']
        
        final_df_with_weight = df[
            [
                'tên',
                'thời gian',
                'số người',
                'độ khó',
                'nguyên liệu chính',
                #'nguyên liệu phụ',
                'nguyên liệu phụ_1 cần thiết',
                'nguyên liệu phụ_2 có thể bỏ qua',
                'link'
            ]
        ]

        final_df_no_weight = final_df_with_weight.copy()
        for column in ['nguyên liệu chính', 'nguyên liệu phụ_1 cần thiết', 'nguyên liệu phụ_2 có thể bỏ qua']:
            final_df_no_weight[column] = final_df_no_weight[column].apply(remove_ingredient_quantities_block)
        final_df_no_weight = final_df_no_weight.drop(columns=['link'])

        full_json_data = [build_recipe_json_record(row) for _, row in df.iterrows()]
        
        # Lưu file CSV, giữ nguyên xuống dòng trong từng ô bằng cách để pandas tự quote khi cần.
        final_df_with_weight.to_csv(OUTPUT_WITH_WEIGHT_FILE, index=False, encoding='utf-8-sig')
        final_df_no_weight.to_csv(OUTPUT_NO_WEIGHT_FILE, index=False, encoding='utf-8-sig')
        with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as json_file:
            json.dump(full_json_data, json_file, ensure_ascii=False, indent=2)
        
        print("-" * 30)
        print(f"THÀNH CÔNG!")
        print(f"1. Đã xóa mô tả thừa sau đơn vị (g, ml, con, trái...)")
        print(f"2. Đã loại bỏ {removed_count} dòng có thời gian bằng 0 phút.")
        print(f"3. Đã chuẩn hóa nguyên liệu thiếu định lượng theo 100g / 1 quả / 1 con / 1 cái.")
        print(f"4. Đã xuất thêm JSON đầy đủ tại: {OUTPUT_JSON_FILE}")
        print(f"5. File 1 lưu tại: {OUTPUT_WITH_WEIGHT_FILE}")
        print(f"6. File 2 lưu tại: {OUTPUT_NO_WEIGHT_FILE}")
        print("-" * 30)

    except Exception as e:
        print(f"Lỗi: {e}")

if __name__ == "__main__":
    main()