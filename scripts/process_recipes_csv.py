#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script xử lý file CSV công thức nấu ăn
Gộp các dòng nguyên liệu và cách nấu thành từng dòng duy nhất
Output: CSV với 3 cột - Tên Món, Nguyên Liệu, Cách Nấu
"""

import csv
import re

def clean_text(text):
    """Làm sạch text"""
    text = str(text).strip()
    text = re.sub(r'\s+', ' ', text)
    # Bỏ dấu phẩy lặp ở cuối
    text = re.sub(r',+;$', ';', text)
    text = re.sub(r',,+', ',', text)
    return text

def clean_title(text):
    """Làm sạch tiêu đề - loại bỏ phần dấu phẩy, dấu ngoặc thừa"""
    text = text.strip()
    # Bỏ ngoặc kép thừa ở đầu cuối
    text = re.sub(r'^"+|"+$', '', text)
    
    # Tìm điểm dừng: nếu có "," hoặc ";" theo sau bởi số/dash (dấu hiệu nguyên liệu)
    # Ví dụ: "Tiêu đề,100g" hoặc "Tiêu đề,- Nguyên liệu"
    match = re.search(r'[,;]\s*[\d\-"]', text)
    if match:
        text = text[:match.start()]
    
    # Bỏ "," hoặc ";" hoặc "-" thừa ở cuối
    text = re.sub(r'[,;\-\s]+$', '', text)
    text = text.strip()
    
    return text

def is_recipe_title_line(text):
    """Kiểm tra nếu dòng là tiêu đề công thức chính"""
    if not text or len(text) < 20:
        return False
    
    text_lower = text.lower()
    
    # Loại bỏ keyword không phải tiêu đề
    if any(kw in text_lower for kw in ['bước', 'cách làm', 'cách chế biến', 'thành phẩm', 'http', 'ảnh:', 'nơi mua', 'link']):
        return False
    
    # Loại bỏ dòng nguyên liệu phụ (vd "Nguyên liệu nước lọc:")
    if text_lower.startswith('nguyên liệu') and ':' in text and len(text) < 60:
        return False
    
    return True

def has_ingredient_marker(text):
    """Kiểm tra nếu dòng chứa dấu hiệu của nguyên liệu"""
    text_lower = text.lower()
    
    # Từ khóa
    if 'nguyên liệu' in text_lower:
        return True
    
    # Bắt đầu bằng số hoặc dash + số (ví dụ "1.", "2.", "-", "- 1", "½")
    if re.match(r'^[\d\-\*\+]', text) or re.match(r'^-\s+\d', text):
        return True
    
    # Chứa đơn vị lượng
    units = ['g;', 'ml;', 'kg;', 'cốc', 'thìa', 'muỗng', 'chén', 'lít', 'tép ', 'quả ', 'cây ', 'lá ', 'g,', 'ml,', 'kg,']
    if any(unit in text_lower for unit in units):
        return True
    
    return False

def has_instruction_marker(text):
    """Kiểm tra nếu dòng chứa dấu hiệu của cách nấu"""
    text_lower = text.lower()
    return 'bước' in text_lower

def is_description_line(text):
    """Kiểm tra nếu dòng là miêu tả (không phải tiêu đề, nguyên liệu, cách nấu)"""
    text_lower = text.lower()
    
    # Nếu quá dài và không chứa số, có thể là miêu tả
    if len(text) > 80 and not any(c.isdigit() for c in text[:30]):
        return True
    
    # Chứa các keyword miêu tả
    if any(kw in text_lower for kw in ['cách chế biến', 'công thức', 'giới thiệu', 'từng', 'được', 'đặc biệt']):
        return True
    
    return False

def main():
    input_file = '/home/duonglt/KHDL-Food-Recommendation/result/toi_vao_bep_afamily_categories.csv'
    output_file = '/home/duonglt/KHDL-Food-Recommendation/result/recipes_processed_clean.csv'
    
    print(f"📖 Đang xử lý file: {input_file}\n")
    
    # Đọc tất cả dòng
    all_lines = []
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f, quotechar='"')
        next(reader)  # Skip header
        
        for row in reader:
            # Nối tất cả cột thành text
            text = ' '.join(col.strip() for col in row if col.strip())
            if text:
                all_lines.append(clean_text(text))
    
    print(f"✅ Đã đọc {len(all_lines)} dòng\n")
    
    # Phân tích
    recipes = []
    i = 0
    
    while i < len(all_lines):
        line = all_lines[i]
        
        # Tìm tiêu đề công thức
        if is_recipe_title_line(line):
            current_title = clean_title(line)
            i += 1
            
            # Bỏ qua các dòng miêu tả trước khi gặp nguyên liệu
            while i < len(all_lines) and is_description_line(all_lines[i]):
                i += 1
            
            # Gộp các dòng nguyên liệu
            ingredients = []
            while i < len(all_lines):
                if has_ingredient_marker(all_lines[i]) and not has_instruction_marker(all_lines[i]):
                    ingredients.append(all_lines[i])
                    i += 1
                elif has_instruction_marker(all_lines[i]):
                    # Gặp phần cách nấu, dừng lấy nguyên liệu
                    break
                elif is_recipe_title_line(all_lines[i]):
                    # Gặp tiêu đề mới, dừng
                    break
                else:
                    # Bỏ qua dòng khác
                    i += 1
            
            # Gộp các dòng cách nấu
            instructions = []
            while i < len(all_lines):
                if has_instruction_marker(all_lines[i]):
                    instructions.append(all_lines[i])
                    i += 1
                elif is_recipe_title_line(all_lines[i]):
                    # Gặp tiêu đề mới, dừng
                    break
                else:
                    # Bỏ qua các dòng khác
                    i += 1
            
            # Lưu công thức
            if current_title and (ingredients or instructions):
                recipes.append({
                    'Tên Món': current_title,
                    'Nguyên Liệu': ' | '.join(ingredients) if ingredients else '',
                    'Cách Nấu': ' | '.join(instructions) if instructions else ''
                })
                print(f"✅ [{len(recipes):3d}] {current_title[:55]}")
        else:
            i += 1
    
    # Ghi file
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Tên Món', 'Nguyên Liệu', 'Cách Nấu'], quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(recipes)
    
    print(f"\n✨ Hoàn thành!")
    print(f"📁 Output: {output_file}")
    print(f"📊 Tổng: {len(recipes)} công thức\n")
    
    # Preview
    if recipes:
        print("📋 Preview 5 công thức đầu:\n")
        for i, r in enumerate(recipes[:5], 1):
            print(f"{i}. {r['Tên Món'][:65]}")
            ing = r['Nguyên Liệu'][:100] if r['Nguyên Liệu'] else "(trống)"
            print(f"   📌 NL: {ing}")
            cach = r['Cách Nấu'][:100] if r['Cách Nấu'] else "(trống)"
            print(f"   👨‍🍳 CC: {cach}\n")

if __name__ == '__main__':
    main()
