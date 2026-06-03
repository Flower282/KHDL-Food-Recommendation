#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crawl tối đa công thức từ afamily.vn bằng cách:
1. Phát hiện tất cả danh mục từ homepage
2. Crawl tất cả trang trong mỗi danh mục
3. Trích xuất tất cả bài viết
"""

import os
import csv
import time
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

# Set up paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULT_DIR = os.path.join(PROJECT_ROOT, 'result')
OUTPUT_FILE = os.path.join(RESULT_DIR, 'toi_vao_bep_afamily_max.csv')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def discover_categories():
    """Tự động phát hiện danh mục từ homepage"""
    print("🔍 Đang phát hiện danh mục từ homepage...")
    try:
        response = requests.get("https://afamily.vn", headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        categories = {}
        
        # Tìm các link danh mục (filter để chỉ lấy recipe-related links)
        recipe_keywords = ['mon', 'banh', 'recipe', 'dac-san', 'an', 'kheo-tay', 'meo-vat']
        
        # Tìm tất cả <a> tags
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text().strip()
            
            # Filter để chỉ lấy category links
            if href.startswith('/') and text and len(text) < 50 and len(text) > 3:
                # Kiểm tra nếu link là recipe-related
                if any(keyword in href.lower() for keyword in recipe_keywords):
                    # Tránh duplicate
                    if href not in categories:
                        full_url = urljoin("https://afamily.vn", href)
                        categories[href] = (text, full_url)
        
        print(f"✅ Tìm thấy {len(categories)} danh mục")
        return categories
        
    except Exception as e:
        print(f"❌ Error discovering categories: {str(e)}")
        return {}

def get_recipe_articles_with_pagination(category_url, category_name, max_pages=5):
    """Fetch articles từ một danh mục với pagination"""
    all_recipes = []
    
    for page_num in range(1, max_pages + 1):
        try:
            # Thử multiple URL formats cho pagination
            page_urls = [
                category_url,  # Trang đầu
                f"{category_url}?page={page_num}",
                f"{category_url.rstrip('.html')}/page/{page_num}.html",
            ]
            
            page_content = None
            
            for test_url in page_urls:
                try:
                    response = requests.get(test_url, headers=HEADERS, timeout=10)
                    if response.status_code == 200:
                        page_content = response.content
                        break
                except:
                    continue
            
            if not page_content:
                if page_num == 1:
                    print(f"     ⚠️  Không tìm thấy trang")
                break
            
            soup = BeautifulSoup(page_content, 'html.parser')
            articles = soup.find_all('article')
            
            if not articles:
                if page_num == 1:
                    print(f"     ⚠️  Không tìm thấy articles")
                break
            
            # Extract articles từ trang này
            page_recipes = 0
            for article in articles:
                link = article.find('a')
                if not link:
                    continue
                
                title = link.get('title', '').strip()
                url = link.get('href', '').strip()
                
                # Build full URL nếu relative
                if url.startswith('/'):
                    url = 'https://afamily.vn' + url
                
                if title and url:
                    # Get description nếu có
                    description = ''
                    desc_elem = article.find('p', class_='afwblu-description')
                    if desc_elem:
                        description = desc_elem.get_text().strip()
                    
                    recipe = {
                        'tiêu đề': title,
                        'miêu tả': description,
                        'nguyên liệu': '',
                        'hướng dẫn': '',
                        'link': url
                    }
                    
                    # Tránh duplicate
                    if not any(r['link'] == recipe['link'] for r in all_recipes):
                        all_recipes.append(recipe)
                        page_recipes += 1
            
            if page_recipes == 0:
                break  # Không có bài viết mới, dừng
            
            print(f"     Page {page_num}: +{page_recipes} bài viết")
            time.sleep(random.uniform(0.5, 1.5))  # Delay nhỏ hơn
            
        except Exception as e:
            if page_num == 1:
                print(f"     ❌ Error: {str(e)}")
            break
    
    return all_recipes

def get_recipe_details(recipe_url):
    """Extract ingredients and instructions từ detail page"""
    try:
        response = requests.get(recipe_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get content từ detail page
        content_div = soup.find('div', class_='afcbc-body vceditor-content')
        if not content_div:
            content_div = soup.find('div', class_='vceditor-content')
        
        if not content_div:
            return '', ''
        
        # Extract tất cả paragraphs và lists
        ingredients = []
        instructions = []
        
        # Look for ingredient keywords
        ingredient_keywords = ['gram', 'g ', 'cốc', 'thìa', 'kg', 'lít', 'ml', 'muỗng', 'chén', 'nắm', 'chiếc', 'quả', 'bó']
        
        # Process tất cả children
        for elem in content_div.find_all(['p', 'li', 'strong', 'b']):
            text = elem.get_text().strip()
            if not text or len(text) < 5:
                continue
            
            # Check nếu giống ingredient
            is_ingredient = any(keyword in text.lower() for keyword in ingredient_keywords)
            
            if is_ingredient and not any(keyword in text.lower() for keyword in ['bước', 'cách', 'khuôn', 'phút', 'giờ', 'độ']):
                if text not in ingredients:
                    ingredients.append(text)
            elif text not in ingredients and text not in instructions:
                instructions.append(text)
        
        ingredients_str = '\n'.join(ingredients[:20])  # Limit 20 ingredients
        instructions_str = '\n'.join(instructions[:30])  # Limit 30 instruction lines
        
        return ingredients_str, instructions_str
        
    except Exception as e:
        return '', ''

def main():
    print("=" * 70)
    print("🔥 CRAWL TỐI ĐA CÔNG THỨC TỪ AFAMILY.VN")
    print("=" * 70)
    print(f"🕒 Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    all_recipes = []
    total_categories = 0
    
    # Step 1: Discover categories
    discovered_categories = discover_categories()
    
    if not discovered_categories:
        print("\n⚠️  Không phát hiện được danh mục, sử dụng danh mục mặc định")
        discovered_categories = {
            "/mon-an-han-quoc.html": ("Món ăn Hàn Quốc", "https://afamily.vn/mon-an-han-quoc.html"),
            "/mon-an-nhat-ban.html": ("Món ăn Nhật Bản", "https://afamily.vn/mon-an-nhat-ban.html"),
            "/banh-my.html": ("Bánh mì", "https://afamily.vn/banh-my.html"),
            "/banh-cupcake.html": ("Bánh ngọt", "https://afamily.vn/banh-cupcake.html"),
            "/dac-san-mien-bac.html": ("Đặc sản miền Bắc", "https://afamily.vn/dac-san-mien-bac.html"),
            "/dac-san-mien-nam.html": ("Đặc sản miền Nam", "https://afamily.vn/dac-san-mien-nam.html"),
            "/dac-san-mien-trung.html": ("Đặc sản miền Trung", "https://afamily.vn/dac-san-mien-trung.html"),
        }
    
    print("\n" + "=" * 70)
    print("📂 BẮT ĐẦU CRAWL TỪ CÁC DANH MỤC")
    print("=" * 70 + "\n")
    
    # Step 2: Crawl từ mỗi category
    for href, (cat_name, cat_url) in list(discovered_categories.items())[:20]:  # Limit 20 categories
        print(f"📂 {cat_name}")
        print(f"   URL: {cat_url}")
        
        # Get articles với pagination
        articles = get_recipe_articles_with_pagination(cat_url, cat_name, max_pages=3)
        print(f"   ✅ Tìm thấy {len(articles)} bài viết")
        
        if not articles:
            continue
        
        total_categories += 1
        
        # Process mỗi article
        for i, article in enumerate(articles[:15], 1):  # Process tối đa 15 per category
            title = article['tiêu đề']
            url = article['link']
            
            print(f"   {i:2d}. {title[:50]}...", end='', flush=True)
            
            # Get detail page content
            ingredients, instructions = get_recipe_details(url)
            
            article['nguyên liệu'] = ingredients
            article['hướng dẫn'] = instructions
            
            all_recipes.append(article)
            print(" ✓")
            
            # Politeness delay - dài hơn
            time.sleep(random.uniform(0.8, 1.5))
        
        print()
    
    # Step 3: Save to CSV
    print("=" * 70)
    print(f"💾 Saving {len(all_recipes)} recipes to {OUTPUT_FILE}")
    
    try:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['tiêu đề', 'miêu tả', 'nguyên liệu', 'hướng dẫn', 'link'])
            writer.writeheader()
            writer.writerows(all_recipes)
        
        print(f"✅ Thành công! Đã lưu {len(all_recipes)} công thức")
        print(f"   📊 Từ {total_categories} danh mục")
        
    except Exception as e:
        print(f"❌ Error saving file: {str(e)}")
    
    print(f"\n🕒 End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main()
