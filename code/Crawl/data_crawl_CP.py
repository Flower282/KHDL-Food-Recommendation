import argparse
import requests
from bs4 import BeautifulSoup
import time
import random
import pandas as pd
import os
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAWCSV_DIR = os.path.join(PROJECT_ROOT, 'rawCSV')
OUTPUT_FILE = os.path.join(RAWCSV_DIR, 'raw_data_CP.csv')

class CookpadCrawler:
    def __init__(self):
        self.base_url = "https://cookpad.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        self.results = []

    def get_recipe_links(self, search_query, start_page=1, end_page=1):
        """Lấy danh sách link các món ăn từ trang tìm kiếm (từ trang start_page đến end_page)"""
        recipe_links = []
        for page in range(start_page, end_page + 1):
            url = f"{self.base_url}/vn/tim-kiem/{search_query}?page={page}"
            print(f"Đang lấy danh sách từ: {url}")
            
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                print(f"Lỗi trang {page}: HTTP {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            # Tìm các thẻ a chứa link bài viết (dựa trên cấu trúc class của Cookpad)
            for link in soup.select('a[href*="/vn/cong-thuc/"]'):
                full_url = self.base_url + link['href'].split('?')[0]
                if full_url not in recipe_links:
                    recipe_links.append(full_url)
            
            time.sleep(random.uniform(1, 3)) # Nghỉ để an toàn
        return recipe_links

    def parse_recipe(self, url):
        """Crawl chi tiết từng món ăn"""
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. Tên món
            name = soup.find('h1').get_text(strip=True) if soup.find('h1') else "N/A"
            
            # 2. Thời gian & 3. Số người (Dựa vào icon trong screenshot của bạn)
            time_val = "15 phút"
            servings = "2 người"
            
            # Tìm các div chứa thông tin thời gian và khẩu phần
            stats = soup.select('.mise-icon-text')
            for stat in stats:
                text = stat.get_text(strip=True)
                if 'phút' in text or 'giờ' in text:
                    time_val = text
                if 'người' in text:
                    servings = text

            # 4. Nguyên liệu
            ingredients_list = []
            ingredient_elements = soup.select('.ingredient-list li')
            for ig in ingredient_elements:
                # Lấy text bao gồm cả định lượng và tên nguyên liệu
                ingredients_list.append(ig.get_text(separator=' ', strip=True))
            
            ingredients_str = "; ".join(ingredients_list)

            return {
                'tên': name,
                'thời gian': time_val,
                'số người': servings,
                'độ khó': 'dễ', # Mặc định là dễ như yêu cầu
                'nguyên liệu': ingredients_str,
                'cách chế biến': ''
            }
        except Exception as e:
            print(f"Lỗi khi crawl {url}: {e}")
            return None

    def save_to_csv(self, filename):
        df = pd.DataFrame(self.results)
        if df.empty:
            print("Không có dữ liệu mới để lưu.")
            return

        file_exists = os.path.exists(filename)
        # Ghi nối dữ liệu mới vào cuối file, chỉ ghi header ở lần đầu.
        df.to_csv(
            filename,
            mode='a',
            header=not file_exists,
            index=False,
            encoding='utf-8-sig',
        )
        print(f"Đã lưu thêm {len(self.results)} món ăn vào file {filename}")




def crawl(search_keyword: str = "món ăn hàng ngày", start_page: int = 1, end_page: int = 5, output_file: Optional[str] = None) -> None:
    os.makedirs(RAWCSV_DIR, exist_ok=True)
    crawler = CookpadCrawler()
    if output_file is None:
        output_file = OUTPUT_FILE

    print(f"Crawl '{search_keyword}' từ trang {start_page} đến trang {end_page}...")
    links = crawler.get_recipe_links(search_keyword, start_page=start_page, end_page=end_page)

    total_links = len(links)
    if total_links == 0:
        print("Không tìm thấy món ăn nào.")
        return

    print(f"Tìm thấy {total_links} món ăn. Bắt đầu crawl chi tiết...")
    for link in links:
        print(f"Đang crawl: {link}")
        data = crawler.parse_recipe(link)
        if data:
            crawler.results.append(data)
        time.sleep(random.uniform(2, 4))

    crawler.save_to_csv(output_file)


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl Cookpad recipes into rawCSV/raw_data_CP.csv")
    parser.add_argument("--search", type=str, default="món ăn hàng ngày", help="Từ khóa tìm kiếm trên Cookpad")
    parser.add_argument("--start-page", type=int, default=1, help="Trang bắt đầu")
    parser.add_argument("--end-page", type=int, default=5, help="Trang kết thúc")
    parser.add_argument("--output", type=str, default=OUTPUT_FILE, help="Đường dẫn file CSV đầu ra")
    args = parser.parse_args()

    if args.start_page < 1 or args.end_page < args.start_page:
        parser.error("--end-page phải >= --start-page và cả hai phải >= 1")

    crawl(search_keyword=args.search, start_page=args.start_page, end_page=args.end_page, output_file=args.output)


if __name__ == "__main__":
    main()
