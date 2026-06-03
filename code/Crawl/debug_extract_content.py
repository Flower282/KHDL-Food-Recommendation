import requests
from bs4 import BeautifulSoup
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# Fetch bài viết mẫu
url = "https://afamily.vn/luoc-lac-chi-cho-muoi-chua-du-lam-cach-nay-lac-se-ngot-mem-khong-tham-den-20250813145801644.chn"
print(f"Testing URL: {url}\n")

response = requests.get(url, headers=HEADERS, timeout=10)
soup = BeautifulSoup(response.content, 'html.parser')

# Lấy h1
h1 = soup.find('h1')
title = h1.get_text(strip=True) if h1 else "N/A"
print(f"Title: {title}\n")

# Lấy content div
content_div = soup.find('div', class_=lambda x: x and 'afcbc-body' in str(x) and 'vceditor-content' in str(x))

if content_div:
    print("Found content div")
    print("=" * 60)
    
    # Lấy các h3 (các tiêu đề chính)
    h3_tags = content_div.find_all('h3')
    print(f"\nTìm thấy {len(h3_tags)} H3 tags:")
    for i, h3 in enumerate(h3_tags):
        print(f"{i+1}. {h3.get_text(strip=True)}\n")
    
    # Lấy các p tags (các đoạn văn)
    p_tags = content_div.find_all('p')
    print(f"\nTìm thấy {len(p_tags)} P tags:")
    for i, p in enumerate(p_tags[:8]):
        text = p.get_text(strip=True)
        print(f"{i+1}. {text[:100]}...\n")
    
    # Lấy tất cả elements (h3, p, strong, em)
    print("\n" + "=" * 60)
    print("FULL CONTENT EXTRACTION:")
    print("=" * 60 + "\n")
    
    elements = content_div.find_all(['h3', 'p'])
    
    ingredients_list = []
    instructions_list = []
    current_section = "intro"
    
    for elem in elements:
        text = elem.get_text(strip=True)
        
        if not text or len(text) < 3:
            continue
        
        # Detect sections
        text_lower = text.lower()
        if 'nguyên liệu' in text_lower or 'ingredient' in text_lower:
            current_section = "ingredients"
            print(f"[SECTION CHANGE] -> ingredients\n")
            continue
        elif 'bước' in text_lower or 'cách làm' in text_lower or 'hướng dẫn' in text_lower:
            current_section = "instructions"
            print(f"[SECTION CHANGE] -> instructions\n")
        
        # In content
        if current_section == "intro":
            print(f"[INTRO] {text[:80]}...")
        elif current_section == "ingredients":
            print(f"[INGREDIENT] {text[:80]}...")
            ingredients_list.append(text)
        elif current_section == "instructions":
            print(f"[INSTRUCTION] {text[:80]}...")
            instructions_list.append(text)
        
        print()
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    print(f"\nNguyên liệu ({len(ingredients_list)} items):")
    for i, ing in enumerate(ingredients_list[:5]):
        print(f"{i+1}. {ing[:100]}")
    
    print(f"\nHướng dẫn ({len(instructions_list)} items):")
    for i, inst in enumerate(instructions_list[:5]):
        print(f"{i+1}. {inst[:100]}")
