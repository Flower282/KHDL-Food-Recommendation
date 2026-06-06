import requests
from bs4 import BeautifulSoup
import csv
import time
import random
import os
from pathlib import Path
from typing import Optional

# Cấu hình header
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAWCSV_DIR = PROJECT_ROOT / 'rawCSV'
FILE_NAME = RAWCSV_DIR / 'tong_hop_mon_an_viet_nam.csv'

def get_recipe_list_data(page_url):
    """Lấy link, thời gian, số người và độ khó ngay tại trang danh sách"""
    data_list = []
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            items = soup.find_all('div', class_=lambda x: x and 'flex-recipe' in x)
            
            for item in items:
                link_tag = item.find('a', href=True)
                if not link_tag: continue
                
                link = link_tag['href']
                
                # Khởi tạo giá trị mặc định
                recipe_time = "N/A"
                servings = "N/A"
                difficulty = "N/A"
                
                # Lấy tất cả các thẻ div có class 'tag' trong card món ăn
                tags = item.find_all('div', class_='tag')
                
                for t in tags:
                    txt = t.get_text(strip=True)
                    # 1. Nhận diện số người (thường chứa chữ 'Người')
                    if "Người" in txt:
                        servings = txt
                    # 2. Nhận diện thời gian (chứa chữ 'Phút' hoặc 'Giờ')
                    elif "Phút" in txt or "Giờ" in txt:
                        recipe_time = txt
                    # 3. Nhận diện độ khó (Các từ khóa: Dễ, Trung bình, Khó)
                    elif any(d in txt for d in ["Dễ", "Trung bình", "Khó"]):
                        difficulty = txt
                
                data_list.append({
                    'link': link, 
                    'time': recipe_time,
                    'servings': servings,
                    'difficulty': difficulty
                })
    except Exception as e:
        print(f" Lỗi trang danh sách {page_url}: {e}")
    return data_list

def get_recipe_ingredients(url):
    """Vào trang chi tiết để lấy Tên và Nguyên liệu"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return None, None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        name = soup.find('h1').get_text(strip=True) if soup.find('h1') else "N/A"
        
        ingredients = []
        ingre_section = soup.find('div', class_='block-nguyenlieu')
        if ingre_section:
            li_tags = ingre_section.find_all('li')
            ingredients = [li.get_text(strip=True) for li in li_tags]
            
        return name, " | ".join(ingredients)
    except Exception as e:
        print(f" Lỗi khi lấy chi tiết {url}: {e}")
        return None, None

def ensure_output_folder() -> None:
    RAWCSV_DIR.mkdir(parents=True, exist_ok=True)


def crawl(start_page: int = 1, end_page: int = 1, output_file: Optional[str] = None) -> str:
    ensure_output_folder()
    if output_file is None:
        output_file = str(FILE_NAME)

    file_exists = os.path.isfile(output_file)
    keys = ['tên', 'thời gian', 'số người', 'độ khó', 'nguyên liệu', 'cách chế biến', 'link']

    rows = []
    for page in range(start_page, end_page + 1):
        page_url = f"https://monngonmoingay.com/tim-kiem-mon-ngon/page/{page}/"
        print(f"\n--- ĐANG XỬ LÝ TRANG {page} ---")

        recipes_in_page = get_recipe_list_data(page_url)

        count = 0
        for item in recipes_in_page:
            name, ingredients = get_recipe_ingredients(item['link'])

            if name:
                row = {
                    'tên': name,
                    'thời gian': item['time'],
                    'số người': item['servings'],
                    'độ khó': item['difficulty'],
                    'nguyên liệu': ingredients,
                    'cách chế biến': '',
                    'link': item['link']
                }
                rows.append(row)
                count += 1
                print(f"   + Đã ghi: {name} | {item['servings']} | {item['difficulty']}")

            time.sleep(random.uniform(1.2, 2.8))

        print(f"==> Xong trang {page}. Thêm mới {count} món.")

    if rows:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'a', encoding='utf-8-sig', newline='') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            if not file_exists:
                dict_writer.writeheader()
            dict_writer.writerows(rows)

        print(f"\n HOÀN THÀNH! Dữ liệu được lưu tại: {output_file}")
    else:
        print("\n⚠️  Không có dữ liệu mới.")

    return output_file


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Crawl MonNgonMoiNgay recipes into rawCSV/tong_hop_mon_an_viet_nam.csv")
    parser.add_argument("--start-page", type=int, default=1, help="Trang bắt đầu")
    parser.add_argument("--end-page", type=int, default=5, help="Trang kết thúc")
    parser.add_argument("--output", type=str, default=str(FILE_NAME), help="Đường dẫn file CSV đầu ra")
    args = parser.parse_args()

    if args.start_page < 1 or args.end_page < args.start_page:
        parser.error("--end-page phải >= --start-page và cả hai phải >= 1")

    crawl(start_page=args.start_page, end_page=args.end_page, output_file=args.output)


if __name__ == "__main__":
    main()