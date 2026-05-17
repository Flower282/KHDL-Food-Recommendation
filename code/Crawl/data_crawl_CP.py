import requests
from bs4 import BeautifulSoup
import time
import random
import pandas as pd
import os

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
                'nguyên liệu': ingredients_str
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




# --- Chạy thử nghiệm ---
if __name__ == "__main__":
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RESULT_DIR = os.path.join(PROJECT_ROOT, 'result')
    OUTPUT_FILE = os.path.join(RESULT_DIR, 'raw_data_CP.csv')

    crawler = CookpadCrawler()
    os.makedirs(RESULT_DIR, exist_ok=True)
    
    # Bước 1: Nhập khoảng trang cần crawl
    search_keyword = "món ăn hàng ngày"
    try:
        start_page = int(input("Nhập số trang bắt đầu a (>=1): ").strip())
        end_page = int(input("Nhập số trang kết thúc b (>= a): ").strip())
    except ValueError:
        print("Giá trị a/b không hợp lệ. Vui lòng nhập số nguyên.")
        raise SystemExit(1)

    if start_page < 1 or end_page < start_page:
        print("Khoảng trang không hợp lệ (a phải >= 1 và b phải >= a).")
        raise SystemExit(1)

    print(f"Crawl từ trang {start_page} đến trang {end_page}...")
    
    # Bước 2: Tìm kiếm và lấy link các món ăn từ các trang
    links = crawler.get_recipe_links(search_keyword, start_page=start_page, end_page=end_page)
    
    total_links = len(links)
    if total_links == 0:
        print("Không tìm thấy món ăn nào.")
        raise SystemExit(0)

    print(f"Tìm thấy {total_links} món ăn từ trang {start_page} đến {end_page}.")
    print(f"Bắt đầu crawl chi tiết tất cả các món...")
    
    # Bước 3: Crawl chi tiết từng link
    for link in links:
        print(f"Đang crawl: {link}")
        data = crawler.parse_recipe(link)
        if data:
            crawler.results.append(data)
        
        # Quan trọng: Nghỉ ngẫu nhiên để tránh bị server Cookpad block
        time.sleep(random.uniform(2, 4)) 
    
    # Bước 4: Xuất file
    crawler.save_to_csv(OUTPUT_FILE)