import csv
import json
import os
import re


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
INPUT_FILE = os.path.join(DATA_DIR, 'Kho.csv')
OUTPUT_FILE = os.path.join(DATA_DIR, 'Kho.json')

QUANTITY_PATTERN = re.compile(
	r'(?P<quantity>\d+[\d\.,/]*)\s*(?P<unit>kg|g|gr|ml|l|m|M|chén|muỗng|thìa|trái|quả|củ|con|cái|hộp|miếng|vắt|gói|hũ|lát|bát|tép|tô)\b',
	flags=re.IGNORECASE,
)


def parse_ingredient(raw_text):
	text = str(raw_text).strip()
	if not text:
		return None

	match = QUANTITY_PATTERN.search(text)
	if match:
		quantity = match.group('quantity').strip()
		unit = match.group('unit').strip()
		amount = f"{quantity} {unit}"
		name = (text[:match.start()] + text[match.end():]).strip(' :,-')
		name = re.sub(r'\s+', ' ', name)
	else:
		name = re.sub(r'\s+', ' ', text)
		amount = None

	if not name:
		return None

	return {
		'tên': name,
		'khối lượng': amount,
	}


def read_ingredients(csv_path):
	ingredients = []
	with open(csv_path, 'r', encoding='utf-8-sig', newline='') as file:
		reader = csv.reader(file)
		rows = list(reader)

	if not rows:
		return ingredients

	for row in rows[1:]:
		if not row:
			continue
		parsed = parse_ingredient(row[0])
		if parsed:
			ingredients.append(parsed)

	return ingredients


def main():
	os.makedirs(DATA_DIR, exist_ok=True)

	ingredients = read_ingredients(INPUT_FILE)
	with open(OUTPUT_FILE, 'w', encoding='utf-8') as file:
		json.dump(ingredients, file, ensure_ascii=False, indent=2)

	print(f"Đã chuyển {len(ingredients)} nguyên liệu từ {INPUT_FILE} sang {OUTPUT_FILE}")


if __name__ == '__main__':
	main()
