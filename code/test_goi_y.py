import json
import os
import re
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
RESULT_DIR = os.path.join(PROJECT_ROOT, 'result')
USER_INPUT_FILE = os.path.join(DATA_DIR, 'Kho.json')
RECIPE_FILE = os.path.join(RESULT_DIR, 'data_monan_day_du.json')

TOP_N = 5
INGREDIENT_MATCH_THRESHOLD = 0.65
NAME_WEIGHT = 0.8
QUANTITY_WEIGHT = 0.2

GROUP_WEIGHTS = {
	'nguyên liệu chính': 0.9,
	'nguyên liệu phụ_1 cần thiết': 0.1,
	'nguyên liệu phụ_2 có thể bỏ qua': 0.05,
}

UNIT_ALIASES = {
	'gr': 'g',
	'gram': 'g',
	'kg': 'kg',
	'ml': 'ml',
	'l': 'l',
	'lit': 'l',
	'lít': 'l',
	'trái': 'quả',
}


print('Đang tải mô hình NLP...')
model = SentenceTransformer('keepitreal/vietnamese-sbert')


def load_json_file(file_path):
	with open(file_path, 'r', encoding='utf-8') as file:
		data = json.load(file)

	if not isinstance(data, list):
		raise ValueError(f'Dữ liệu trong {file_path} phải là một mảng JSON.')

	return data


def parse_minutes(time_text):
	if time_text is None:
		return None

	match = re.search(r'(\d+)', str(time_text))
	if not match:
		return None

	return int(match.group(1))


def parse_number(text):
	token = str(text).strip().replace(',', '.')
	if '/' in token:
		parts = token.split('/', 1)
		try:
			numerator = float(parts[0])
			denominator = float(parts[1])
			if denominator == 0:
				return None
			return numerator / denominator
		except ValueError:
			return None

	try:
		return float(token)
	except ValueError:
		return None


def parse_quantity_and_unit(quantity_text):
	if quantity_text is None:
		return None, None

	cleaned = re.sub(r'\s+', ' ', str(quantity_text).strip().lower())
	if not cleaned:
		return None, None

	parts = cleaned.split(' ', 1)
	number_value = parse_number(parts[0])
	if number_value is None:
		return None, None

	unit = parts[1].strip() if len(parts) > 1 else None
	if unit:
		unit = UNIT_ALIASES.get(unit, unit)

	return number_value, unit


def compare_quantity(user_quantity, recipe_quantity):
	user_value, user_unit = parse_quantity_and_unit(user_quantity)
	recipe_value, recipe_unit = parse_quantity_and_unit(recipe_quantity)

	# Không có dữ liệu khối lượng ở một trong hai bên thì cho điểm trung tính.
	if user_value is None or recipe_value is None:
		return 0.5

	if user_unit and recipe_unit and user_unit != recipe_unit:
		return 0.0

	if recipe_value <= 0:
		return 0.5

	relative_diff = abs(user_value - recipe_value) / recipe_value
	return max(0.0, 1.0 - min(1.0, relative_diff))


def normalize_user_ingredients(user_data):
	normalized = []
	for item in user_data:
		if not isinstance(item, dict):
			continue

		name = str(item.get('tên', '')).strip()
		if not name:
			continue

		normalized.append(
			{
				'tên': name,
				'khối lượng': item.get('khối lượng'),
			}
		)

	return normalized


def score_ingredient_group(group_items, user_ingredients, user_vectors):
	if not group_items:
		return 0.0, []

	valid_recipe_items = [item for item in group_items if str(item.get('tên', '')).strip()]
	recipe_names = [str(item.get('tên', '')).strip() for item in valid_recipe_items]
	if not valid_recipe_items:
		return 0.0, []

	recipe_vectors = model.encode(recipe_names, show_progress_bar=False)
	similarity_matrix = cosine_similarity(recipe_vectors, user_vectors)

	detailed_status = []
	ingredient_scores = []

	for idx, recipe_item in enumerate(valid_recipe_items):
		recipe_name = str(recipe_item.get('tên', '')).strip()

		best_user_idx = int(np.argmax(similarity_matrix[idx]))
		best_name_score = float(similarity_matrix[idx][best_user_idx])
		best_user_item = user_ingredients[best_user_idx]

		if best_name_score >= INGREDIENT_MATCH_THRESHOLD:
			quantity_score = compare_quantity(best_user_item.get('khối lượng'), recipe_item.get('khối lượng'))
			final_item_score = (NAME_WEIGHT * best_name_score) + (QUANTITY_WEIGHT * quantity_score)
			tag = 'CO'
		else:
			quantity_score = 0.0
			final_item_score = NAME_WEIGHT * best_name_score
			tag = 'KHONG'

		ingredient_scores.append(final_item_score)

		detailed_status.append(
			{
				'nguyên liệu công thức': recipe_name,
				'khối lượng công thức': recipe_item.get('khối lượng'),
				'nguyên liệu kho gần nhất': best_user_item.get('tên'),
				'khối lượng kho': best_user_item.get('khối lượng'),
				'điểm tên': round(best_name_score, 4),
				'điểm khối lượng': round(quantity_score, 4),
				'trạng thái': tag,
			}
		)

	if not ingredient_scores:
		return 0.0, detailed_status

	return float(np.mean(ingredient_scores)), detailed_status


def filter_recipes(recipes, max_minutes=None, difficulty='Tất cả'):
	filtered = []
	for recipe in recipes:
		recipe_minutes = parse_minutes(recipe.get('thời gian'))
		recipe_difficulty = str(recipe.get('độ khó', '')).strip()

		if max_minutes is not None and (recipe_minutes is None or recipe_minutes > max_minutes):
			continue

		if difficulty != 'Tất cả' and recipe_difficulty != difficulty:
			continue

		filtered.append(recipe)

	return filtered


def calculate_top_recipes(user_input_json, recipe_json, max_minutes=None, difficulty='Tất cả'):
	user_data = load_json_file(user_input_json)
	recipes = load_json_file(recipe_json)

	user_ingredients = normalize_user_ingredients(user_data)
	if not user_ingredients:
		return []

	filtered_recipes = filter_recipes(recipes, max_minutes=max_minutes, difficulty=difficulty)
	if not filtered_recipes:
		return []

	user_names = [item['tên'] for item in user_ingredients]
	user_vectors = model.encode(user_names, show_progress_bar=False)

	ranked = []
	for recipe in filtered_recipes:
		main_score, main_status = score_ingredient_group(
			recipe.get('nguyên liệu chính', []),
			user_ingredients,
			user_vectors,
		)
		sub1_score, sub1_status = score_ingredient_group(
			recipe.get('nguyên liệu phụ_1 cần thiết', []),
			user_ingredients,
			user_vectors,
		)
		sub2_score, sub2_status = score_ingredient_group(
			recipe.get('nguyên liệu phụ_2 có thể bỏ qua', []),
			user_ingredients,
			user_vectors,
		)

		final_score = (
			GROUP_WEIGHTS['nguyên liệu chính'] * main_score
			+ GROUP_WEIGHTS['nguyên liệu phụ_1 cần thiết'] * sub1_score
			+ GROUP_WEIGHTS['nguyên liệu phụ_2 có thể bỏ qua'] * sub2_score
		)

		ranked.append(
			{
				'tên': recipe.get('tên', 'Không rõ tên'),
				'thời gian': recipe.get('thời gian', ''),
				'độ khó': recipe.get('độ khó', ''),
				'score_nguyen_lieu_chinh': round(main_score, 4),
				'score_nguyen_lieu_phu_1': round(sub1_score, 4),
				'score_nguyen_lieu_phu_2': round(sub2_score, 4),
				'compatibility_score': round(final_score, 4),
				'nguyên liệu chính_trạng thái': main_status,
				'nguyên liệu phụ_1_trạng thái': sub1_status,
				'nguyên liệu phụ_2_trạng thái': sub2_status,
			}
		)

	ranked.sort(key=lambda item: item['compatibility_score'], reverse=True)
	return ranked[:TOP_N]


class SuggestionApp:
	def __init__(self, root):
		self.root = root
		self.root.title('Gợi ý món ăn từ kho')
		self.root.geometry('1080x700')

		self.results = []
		self._build_ui()

	def _build_ui(self):
		controls = ttk.Frame(self.root, padding=12)
		controls.pack(fill=tk.X)

		ttk.Label(controls, text='Thời gian tối đa (phút):').grid(row=0, column=0, sticky=tk.W, padx=(0, 8))
		self.max_time_var = tk.StringVar()
		self.max_time_entry = ttk.Entry(controls, textvariable=self.max_time_var, width=12)
		self.max_time_entry.grid(row=0, column=1, sticky=tk.W)

		ttk.Label(controls, text='Độ khó:').grid(row=0, column=2, sticky=tk.W, padx=(18, 8))
		difficulties = self._load_difficulty_values()
		self.difficulty_var = tk.StringVar(value='Tất cả')
		self.difficulty_box = ttk.Combobox(
			controls,
			textvariable=self.difficulty_var,
			values=difficulties,
			state='readonly',
			width=20,
		)
		self.difficulty_box.grid(row=0, column=3, sticky=tk.W)

		self.search_button = ttk.Button(controls, text='Tìm top 5', command=self.on_search)
		self.search_button.grid(row=0, column=4, padx=(18, 0))

		table_frame = ttk.Frame(self.root, padding=(12, 0, 12, 8))
		table_frame.pack(fill=tk.BOTH, expand=True)

		columns = ('tên', 'thời gian', 'độ khó', 'score')
		self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=12)
		self.tree.heading('tên', text='Tên món')
		self.tree.heading('thời gian', text='Thời gian')
		self.tree.heading('độ khó', text='Độ khó')
		self.tree.heading('score', text='Điểm phù hợp')

		self.tree.column('tên', width=420)
		self.tree.column('thời gian', width=130, anchor=tk.CENTER)
		self.tree.column('độ khó', width=120, anchor=tk.CENTER)
		self.tree.column('score', width=120, anchor=tk.CENTER)

		scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
		self.tree.configure(yscrollcommand=scrollbar.set)

		self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
		scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
		self.tree.bind('<<TreeviewSelect>>', self.on_select_result)

		detail_frame = ttk.LabelFrame(self.root, text='Chi tiết so sánh nguyên liệu', padding=12)
		detail_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

		self.detail_text = tk.Text(detail_frame, wrap='word', height=14)
		detail_scroll = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=self.detail_text.yview)
		self.detail_text.configure(yscrollcommand=detail_scroll.set)

		self.detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
		detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)

	def _load_difficulty_values(self):
		recipes = load_json_file(RECIPE_FILE)
		values = sorted({str(item.get('độ khó', '')).strip() for item in recipes if str(item.get('độ khó', '')).strip()})
		return ['Tất cả'] + values

	def on_search(self):
		raw_max_time = self.max_time_var.get().strip()
		max_minutes = None

		if raw_max_time:
			if not raw_max_time.isdigit():
				messagebox.showerror('Lỗi nhập liệu', 'Thời gian tối đa phải là số nguyên dương.')
				return
			max_minutes = int(raw_max_time)

		selected_difficulty = self.difficulty_var.get().strip() or 'Tất cả'

		try:
			self.results = calculate_top_recipes(
				USER_INPUT_FILE,
				RECIPE_FILE,
				max_minutes=max_minutes,
				difficulty=selected_difficulty,
			)
		except Exception as exc:
			messagebox.showerror('Lỗi xử lý', str(exc))
			return

		for item in self.tree.get_children():
			self.tree.delete(item)

		self.detail_text.delete('1.0', tk.END)

		if not self.results:
			messagebox.showinfo('Kết quả', 'Không tìm thấy món ăn phù hợp với điều kiện lọc.')
			return

		for idx, recipe in enumerate(self.results, start=1):
			self.tree.insert(
				'',
				tk.END,
				iid=str(idx - 1),
				values=(
					recipe['tên'],
					recipe['thời gian'],
					recipe['độ khó'],
					f"{recipe['compatibility_score']:.4f}",
				),
			)

	def on_select_result(self, _event):
		selected = self.tree.selection()
		if not selected:
			return

		result_index = int(selected[0])
		recipe = self.results[result_index]

		lines = [
			f"Món: {recipe['tên']}",
			f"Thời gian: {recipe['thời gian']} | Độ khó: {recipe['độ khó']}",
			f"Điểm tổng: {recipe['compatibility_score']:.4f}",
			f"- Điểm nguyên liệu chính: {recipe['score_nguyen_lieu_chinh']:.4f}",
			f"- Điểm nguyên liệu phụ_1: {recipe['score_nguyen_lieu_phu_1']:.4f}",
			f"- Điểm nguyên liệu phụ_2: {recipe['score_nguyen_lieu_phu_2']:.4f}",
			'',
			'Chi tiết nguyên liệu chính:',
		]

		lines.extend(self._format_status_block(recipe['nguyên liệu chính_trạng thái']))
		lines.append('')
		lines.append('Chi tiết nguyên liệu phụ_1 cần thiết:')
		lines.extend(self._format_status_block(recipe['nguyên liệu phụ_1_trạng thái']))
		lines.append('')
		lines.append('Chi tiết nguyên liệu phụ_2 có thể bỏ qua:')
		lines.extend(self._format_status_block(recipe['nguyên liệu phụ_2_trạng thái']))

		self.detail_text.delete('1.0', tk.END)
		self.detail_text.insert(tk.END, '\n'.join(lines))

	@staticmethod
	def _format_status_block(items):
		if not items:
			return ['(Không có dữ liệu)']

		lines = []
		for item in items:
			lines.append(
				f"- {item['nguyên liệu công thức']} ({item['khối lượng công thức']}) -> "
				f"{item['nguyên liệu kho gần nhất']} ({item['khối lượng kho']}), "
				f"điểm tên={item['điểm tên']}, điểm khối lượng={item['điểm khối lượng']} [{item['trạng thái']}]"
			)
		return lines


def main():
	root = tk.Tk()
	app = SuggestionApp(root)
	root.mainloop()


if __name__ == '__main__':
	main()
