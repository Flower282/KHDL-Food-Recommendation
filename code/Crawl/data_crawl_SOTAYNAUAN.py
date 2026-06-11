import csv
import os
import random
import re
import time
from typing import Dict, List, Tuple

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

BASE_LIST_URL = "https://sotaynauan.com/chuyen-muc/mon-an-viet-nam/mon-an-mien-bac"

# Lưu file ở thư mục hiện tại (nơi chạy script)
PROJECT_ROOT = os.getcwd()
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "rawCSV")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "mon_an_sotaynauan.csv")


def build_list_url(page: int) -> str:
    """Tạo URL cho các trang danh sách (Pagination)"""
    if page <= 1:
        return f"{BASE_LIST_URL}/"
    return f"{BASE_LIST_URL}/page/{page}/"


def get_article_links(page_url: str) -> List[str]:
    """Crawl tất cả link công thức nấu ăn từ một trang danh sách"""
    links: List[str] = []
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=10)
        # Sotaynauan khi hết trang thường trả về 404, đây là dấu hiệu tốt để dừng
        if response.status_code != 200:
            return links

        soup = BeautifulSoup(response.content, "html.parser")
        
        # Tìm tất cả link nằm trong khối .category (chứa danh sách món ăn)
        for a_tag in soup.select(".category a"):
            href = a_tag.get("href")
            if href and href.startswith("https://sotaynauan.com/"):
                # Bỏ qua các link phân trang, chuyên mục, thẻ tag, tác giả
                if not any(x in href for x in ["/page/", "/chuyen-muc/", "/tag/", "/author/"]):
                    if href not in links:
                        links.append(href)
    except Exception as exc:
        print(f"Lỗi khi quét danh sách link: {exc}")
    return links


def clean_title(raw_title: str) -> str:
    """Loại bỏ các từ khóa thừa ở đầu tên món ăn"""
    if not raw_title or raw_title == "N/A":
        return "N/A"
        
    # Danh sách các từ cần loại bỏ ở ĐẦU câu (sử dụng Regex, không phân biệt hoa thường)
    prefixes = r"^(hướng dẫn cách làm|hướng dẫn cách nấu|hướng dẫn làm|hướng dẫn nấu|hướng dẫn|cách làm|cách nấu|cách)\s+"
    
    # Thực hiện thay thế/loại bỏ
    cleaned = re.sub(prefixes, "", raw_title, flags=re.IGNORECASE).strip()
    
    # Viết hoa chữ cái đầu tiên cho chuẩn tên món ăn
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
        
    return cleaned if cleaned else "N/A"


def parse_article(url: str) -> Tuple[str, str, str, str, str, str]:
    """Bóc tách dữ liệu chi tiết của từng công thức món ăn"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return "N/A", "60 phút", "4 người", "Dễ", "N/A", "N/A"

        soup = BeautifulSoup(response.content, "html.parser")

        # 1. Lấy tên món ăn và làm sạch
        title_tag = soup.select_one("h2.entry-title, h1.entry-title")
        raw_title = title_tag.get_text(strip=True) if title_tag else "N/A"
        title = clean_title(raw_title)

        # 2. Lấy thời gian nấu (Mặc định 60 phút)
        time_val = "60 phút"
        
        # 3. Lấy số lượng người ăn (Mặc định 4 người)
        servings = "4 người"
        
        # 4. Độ khó (Mặc định Dễ)
        difficulty = "Dễ"
        
        time_items = soup.select("ul.recipe-metadata li")
        for item in time_items:
            text = item.get_text(strip=True)
            # Quét tìm thời gian nấu
            if "Thời gian nấu" in text or "Tổng" in text or "Thời gian thực hiện" in text:
                # Trích xuất giá trị thời gian thực tế
                extracted_time = text.split(":")[-1].strip() if ":" in text else text
                if extracted_time:
                    time_val = extracted_time
                
            # Quét tìm khẩu phần ăn (nếu có)
            if "Khẩu phần" in text or "người" in text.lower():
                extracted_servings = text.split(":")[-1].strip()
                if extracted_servings:
                    servings = extracted_servings

        # 5. Lấy danh sách nguyên liệu
        ingredients = []
        for li in soup.select("ul.ingredients li"):
            ingredients.append(li.get_text(strip=True))
        ingredients_str = " | ".join(ingredients) if ingredients else "N/A"

        # 6. Lấy cách chế biến
        steps = []
        instructions_block = soup.select_one(".instructions")
        if instructions_block:
            for tag in instructions_block.find_all(["p", "li"]):
                text = tag.get_text(strip=True)
                # Bỏ qua các text trống hoặc quá ngắn, lọc lấy hướng dẫn cụ thể
                if text and len(text) > 3:
                    steps.append(text)
        instructions_str = " | ".join(steps) if steps else "N/A"

        return title, time_val, servings, difficulty, ingredients_str, instructions_str
    except Exception as exc:
        print(f"Lỗi bài viết {url}: {exc}")
        return "N/A", "60 phút", "4 người", "Dễ", "N/A", "N/A"


def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def write_rows(rows: List[Dict]) -> None:
    """Lưu dữ liệu vào file CSV"""
    if not rows:
        return

    file_exists = os.path.isfile(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["ten", "thoi gian", "so nguoi", "do kho", "nguyen lieu", "cach che bien"],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ensure_output_dir()
    print(f"Bắt đầu thu thập dữ liệu. File sẽ được lưu tại: {OUTPUT_FILE}")

    page = 1
    total_articles = 0

    while True:
        page_url = build_list_url(page)
        print(f"\n--- Đang thu thập link món ăn từ Trang {page}: {page_url} ---")

        links = get_article_links(page_url)
        
        # Điều kiện thoát vòng lặp: Khi không còn link bài viết nào trên trang hiện tại
        if not links:
            print(f"Đã duyệt hết các trang hoặc trang {page} không tồn tại. Kết thúc quá trình cào dữ liệu!")
            break

        page_rows: List[Dict] = []
        
        for link in links:
            print(f"Đang phân tích: {link}")
            title, time_val, servings, difficulty, ingredients, instructions = parse_article(link)
            
            # KIỂM TRA ĐIỀU KIỆN BẮT BUỘC: Nếu thiếu Tên, Nguyên liệu hoặc Cách chế biến thì bỏ qua
            if title == "N/A" or ingredients == "N/A" or instructions == "N/A":
                print(" -> Bỏ qua bài viết này (Thiếu thông tin bắt buộc: Tên/Nguyên Liệu/Cách chế biến).")
                continue

            row = {
                "ten": title,
                "thoi gian": time_val,
                "so nguoi": servings,
                "do kho": difficulty,
                "nguyen lieu": ingredients,
                "cach che bien": instructions,
            }
            page_rows.append(row)
            total_articles += 1

            # Tạm dừng ngẫu nhiên từ 1 - 2.5 giây giữa các bài để mô phỏng người dùng thật
            time.sleep(random.uniform(1.0, 2.5))

        # Lưu dữ liệu ngay sau khi cào xong 1 trang
        write_rows(page_rows)
        print(f"Đã lưu {len(page_rows)} bài viết hợp lệ từ Trang {page}.")
        
        # Chuyển sang trang tiếp theo
        page += 1

    print(f"\n✅ HOÀN THÀNH! Tổng cộng đã cào được {total_articles} món ăn hợp lệ.")

if __name__ == "__main__":
    main()