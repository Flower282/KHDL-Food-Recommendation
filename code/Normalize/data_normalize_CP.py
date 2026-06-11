import json
import os
import re

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import pandas as pd

# Cấu hình file
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULT_DIR = os.path.join(PROJECT_ROOT, 'result')
INPUT_FILE = os.path.join(RESULT_DIR, 'raw_data_CP.csv')
OUTPUT_JSON_FILE = os.path.join(RESULT_DIR, 'data_monan_day_du_CP.json')

OPTIONAL_INGREDIENT_KEYWORDS = [
	'muối', 'đường', 'tiêu', 'ớt', 'tương', 'xì dầu', 'nước tương', 'nước mắm', 'gia vị', 'Aji-Quick',
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
	'gọt', 'tỉa', 'xếp', 'xay nhuyễn', 'xào sơ', 'phi thơm', 'món', 'chà rửa',
	'đánh tan', 'ướp với', 'ướp cùng', 'ướp trong', 'ướp ngoài', 'không', 'vạt', 'xiên', 'lột',
	'đổ', 'ăn', 'giữ', 'to', 'chần',
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
	'nhánh': 'nhánh',
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

QUANTITY_UNIT_PATTERN = r'(?:muỗng\s*cà\s*phê|muỗng\s*canh|thìa\s*cà\s*phê|thìa\s*canh|muỗng|thìa|chén|cốc|kg|gr|g|ml|lít|lit|l|M|m|trái|quả|củ|con|hộp|miếng|vắt|gói|hũ|cái|lát|bát|tép|tô|cây|bắp|nhánh)'


def _contains_keyword(text, keywords):
	normalized_text = re.sub(r'\s+', ' ', str(text).strip().lower())
	return any(re.search(rf'(?<!\w){re.escape(keyword)}(?!\w)', normalized_text) for keyword in keywords)


def normalize_unit(unit):
	if not unit:
		return unit

	normalized_unit = re.sub(r'\s+', ' ', str(unit).strip().lower())
	return STANDARD_UNIT_ALIASES.get(normalized_unit, normalized_unit)


def clean_special_characters(text):
	text = str(text).replace('_', ' ')
	text = re.sub(r'[®™©]', '', text)
	text = re.sub(r'[\(\)\[\]\{\}]', ' ', text)
	text = re.sub(r'[^\w\sÀ-ỹ\-\/]', '', text, flags=re.UNICODE)
	text = re.sub(r'\s+', ' ', text)
	return text.strip(' -/\t')


def extract_display_name(ingredient_text):
	base_text = clean_special_characters(str(ingredient_text).split(':', 1)[0].strip())
	# Dữ liệu CP thường có định lượng đứng trước tên (ví dụ: "200g thịt bò").
	name_text = re.sub(
		rf'\b(?:khoảng\s*)?\d+[\d\.,/]*\s*{QUANTITY_UNIT_PATTERN}\b',
		' ',
		base_text,
		flags=re.IGNORECASE,
	)
	name_text = re.sub(r'\s+', ' ', name_text).strip(' -/\t')

	if not name_text:
		name_text = re.sub(r'^\s*(?:khoảng\s*)?\d+[\d\.,/]*\s*', '', base_text, flags=re.IGNORECASE)
		name_text = re.sub(r'\s+', ' ', name_text).strip(' -/\t')

	return name_text


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
	cleaned = str(text).strip()
	# Dữ liệu CP thường có định lượng đứng đầu, cần giữ nguyên để tách tên phía sau.
	if re.match(r'^\d+[\d\.,/]*\s*', cleaned):
		return cleaned

	units = r'(g|gr|kg|ml|l|chén|muỗng|M|m|trái|củ|con|hộp|miếng|vắt|gói|hũ|cái|lát|bát|quả|tép|tô|thìa)'
	pattern = rf'^(.*?\d+\s*{units})\b.*'

	match = re.match(pattern, cleaned, flags=re.IGNORECASE)
	if match:
		return match.group(1).strip()
	return cleaned


def starts_with_excluded_prefix(text):
	normalized_text = re.sub(r'\s+', ' ', str(text).strip().lower())
	return any(
		normalized_text == prefix or normalized_text.startswith(prefix + ' ')
		for prefix in EXCLUDED_INGREDIENT_PREFIXES
	)


def split_ingredient_entries(raw_text):
	entries = []
	for line in str(raw_text).split('\n'):
		# Dữ liệu CP hiện tách bằng dấu ';'
		parts = re.split(r'[|;,]', line)
		for part in parts:
			part = part.strip()
			if part:
				entries.append(part)
	return entries


def deduplicate_preserve_order(items):
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


def extract_ingredient_name(ingredient_text):
	base_text = ingredient_text.split(':')[0].strip().lower()
	base_text = re.sub(
		r'\s+\d+[\d\.,/]*\s*(g|gr|kg|ml|l|chén|muỗng|M|m|trái|củ|con|hộp|miếng|vắt|gói|hũ|cái|lát|bát|quả|tép|tô|thìa)?\b.*$',
		'',
		base_text,
		flags=re.IGNORECASE,
	)
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

	if overlap_count >= 2:
		return True

	if overlap_count == 1 and any(word in CORE_MAIN_WORDS for word in overlap):
		return True

	ingredient_phrase = ' '.join(get_meaningful_words(ingredient_name)).strip()
	if ingredient_phrase and len(ingredient_phrase.split()) >= 2 and ingredient_phrase in dish_name.lower():
		return True

	return False


def parse_minutes(time_value):
	if pd.isna(time_value):
		return None

	text = str(time_value).strip().lower()
	match = re.search(r'(\d+)', text)
	if not match:
		return None

	return int(match.group(1))


def process_ingredients(row):
	dish_name = str(row['tên']).lower()
	raw_list = [] if pd.isna(row['nguyên liệu']) else str(row['nguyên liệu']).split('|')

	main_list = []
	sub_list = []
	sub_required_list = []
	sub_optional_list = []
	ingredient_details = []

	for raw_item in raw_list:
		for split_item in split_ingredient_entries(raw_item):
			cleaned_item = clean_description(split_item.strip())
			if not cleaned_item:
				continue
			if starts_with_excluded_prefix(cleaned_item):
				continue

			ingre_name = extract_ingredient_name(cleaned_item)
			is_main = False
			is_optional = is_optional_ingredient(cleaned_item)

			if not is_optional:
				is_main = is_main_ingredient(dish_name, ingre_name)

			standardized_ingredient = standardize_ingredient_text(cleaned_item, is_optional=is_optional)
			if not standardized_ingredient['name']:
				continue
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

	return pd.Series(
		{
			'nguyên liệu chính': '\n'.join(main_list),
			'nguyên liệu phụ': '\n'.join(sub_list),
			'nguyên liệu phụ_1 cần thiết': '\n'.join(sub_required_list),
			'nguyên liệu phụ_2 có thể bỏ qua': '\n'.join(sub_optional_list),
			'nguyên liệu chi tiết': ingredient_details,
		}
	)


def build_recipe_json_record(row):
	ingredient_details = to_json_compatible(row['nguyên liệu chi tiết']) or []

	def format_ingredient_payload(item):
		quantity = item.get('so_luong')
		unit = item.get('don_vi')

		if quantity and unit:
			normalized_amount = f'{quantity} {unit}'
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
		print(f'Đang xử lý file: {INPUT_FILE}...')
		df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')

		# Bỏ các dòng thiếu tên món hoặc dữ liệu lỗi "N/A".
		df = df[df['tên'].notna()].copy()
		df = df[df['tên'].astype(str).str.strip().str.lower() != 'n/a'].copy()

		original_count = len(df)
		df = df[df['thời gian'].apply(lambda x: parse_minutes(x) != 0)].copy()
		removed_count = original_count - len(df)

		new_data = df.apply(process_ingredients, axis=1)

		df['nguyên liệu chính'] = new_data['nguyên liệu chính']
		df['nguyên liệu phụ'] = new_data['nguyên liệu phụ']
		df['nguyên liệu phụ_1 cần thiết'] = new_data['nguyên liệu phụ_1 cần thiết']
		df['nguyên liệu phụ_2 có thể bỏ qua'] = new_data['nguyên liệu phụ_2 có thể bỏ qua']
		df['nguyên liệu chi tiết'] = new_data['nguyên liệu chi tiết']

		full_json_data = [build_recipe_json_record(row) for _, row in df.iterrows()]
		with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as json_file:
			json.dump(full_json_data, json_file, ensure_ascii=False, indent=2)

		print('-' * 30)
		print('THÀNH CÔNG!')
		print('1. Đã xóa mô tả thừa sau đơn vị (g, ml, con, trái...)')
		print(f'2. Đã loại bỏ {removed_count} dòng có thời gian bằng 0 phút.')
		print('3. Đã chuẩn hóa nguyên liệu thiếu định lượng theo 100g / 1 quả / 1 con / 1 cái.')
		print(f'4. Đã xuất file JSON đầy đủ tại: {OUTPUT_JSON_FILE}')
		print('-' * 30)

	except Exception as e:
		print(f'Lỗi: {e}')


if __name__ == '__main__':
	main()
