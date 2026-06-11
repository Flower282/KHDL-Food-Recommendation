import csv
import os
import random
import re
import time
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

# --- CẤU HÌNH ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

BASE_LIST_URL = "https://cookpad.com/vn/tim-kiem/món ăn hàng ngày"

PROJECT_ROOT = os.getcwd()
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "rawCSV")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "mon_an_cookpad.csv")


def build_list_url(page: int) -> str:
    """Tạo URL phân trang cho Cookpad"""
    if page <= 1:
        return BASE_LIST_URL
    return f"{BASE_LIST_URL}?page={page}"


def get_article_links(page_url: str) -> List[str]:
    """Crawl link công thức nấu ăn từ trang danh sách Cookpad"""
    links: List[str] = []
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return links

        soup = BeautifulSoup(response.content, "html.parser")
        
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # Lọc link bài viết chuẩn xác bằng Regex
            if re.search(r'/vn/cong-thuc/\d+', href):
                full_link = f"https://cookpad.com{href}" if href.startswith("/") else href
                # Cắt bỏ các tham số tracking (như ?ref=... hay #comments)
                clean_link = full_link.split('?')[0].split('#')[0]
                
                if clean_link not in links:
                    links.append(clean_link)
                    
    except Exception as exc:
        print(f"Lỗi khi quét danh sách link: {exc}")
    return links


def clean_title(title: str) -> str:
    """Loại bỏ từ khóa thừa, số thứ tự ở đầu và chuẩn hóa"""
    if not title or title == "N/A":
        return "N/A"
        
    patterns = [
        r"^(hướng dẫn cách làm|hướng dẫn cách nấu|hướng dẫn làm|hướng dẫn nấu|hướng dẫn|cách làm|cách nấu|cách)\s+",
        r"^([IVXLCDM]+|\d+)[\.\-\:]\s*"
    ]
    cleaned = title
    for p in patterns:
        cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE)
    
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned.strip()


def parse_article(url: str) -> Dict:
    """Bóc tách dữ liệu theo ID động của Cookpad"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return {}

        soup = BeautifulSoup(response.content, "html.parser")

        # 1. Tên món ăn
        title_tag = soup.find("h1")
        title = clean_title(title_tag.get_text(strip=True)) if title_tag else "N/A"

        # 2. Thời gian & Khẩu phần (Tìm theo prefix ID và class mise-icon-text)
        time_val = "60 phút"
        servings = "4 người"
        difficulty = "Dễ"

        time_node = soup.select_one("div[id^='cooking_time_recipe_'] .mise-icon-text")
        if time_node:
            time_val = time_node.get_text(strip=True)

        serving_node = soup.select_one("div[id^='serving_recipe_'] .mise-icon-text")
        if serving_node:
            servings = serving_node.get_text(strip=True)

        # 3. Nguyên liệu (Tìm theo prefix ID ingredient_)
        ingredients = []
        ing_items = soup.select("li[id^='ingredient_']")
        for item in ing_items:
            # get_text(" ", ...) sẽ nối số lượng <bdi> và tên <span> bằng 1 khoảng trắng
            text = item.get_text(" ", strip=True)
            if text and len(text) > 2:
                ingredients.append(text)
                
        ingredients_str = " | ".join(ingredients) if ingredients else "N/A"

        # 4. Cách làm (Tìm theo prefix ID step_)
        steps = []
        step_items = soup.select("li[id^='step_'], div[id^='step_']")
        for item in step_items:
            # Ưu tiên lấy text trong thẻ div có dir='auto' hoặc thẻ p để loại bỏ ảnh
            content_tag = item.select_one("div[dir='auto'], p")
            text = content_tag.get_text(" ", strip=True) if content_tag else item.get_text(" ", strip=True)
            # Xóa các con số thứ tự đếm ở đầu (Ví dụ: "1.", "2)")
            text = re.sub(r'^\d+[\.\)]\s*', '', text)
            if text and len(text) > 5:
                steps.append(text)
                
        # Dự phòng nếu không có id="step_..."
        if not steps:
            for p in soup.select("[itemprop='recipeInstructions'] p"):
                text = p.get_text(" ", strip=True)
                if len(text) > 5:
                    steps.append(text)

        instructions_str = " | ".join(steps) if steps else "N/A"

        # KIỂM TRA ĐIỀU KIỆN BẮT BUỘC
        if title == "N/A" or not ingredients or not steps:
            print(f"   -> Lọc dữ liệu: (Tên: {'OK' if title != 'N/A' else 'Lỗi'}, NL: {len(ingredients)} mục, Các bước: {len(steps)} mục)")
            return {}

        return {
            "ten": title,
            "thoi gian": time_val,
            "so nguoi": servings,
            "do kho": difficulty,
            "nguyen lieu": ingredients_str,
            "cach che bien": instructions_str
        }

    except Exception as exc:
        print(f"Lỗi bài viết {url}: {exc}")
        return {}


def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def write_rows(rows: List[Dict]) -> None:
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
    print(f"Bắt đầu thu thập dữ liệu Cookpad. File sẽ được lưu tại: {OUTPUT_FILE}")

    page = 1
    total_articles = 0
    empty_count = 0
    max_empty_pages = 2

    while True:
        page_url = build_list_url(page)
        print(f"\n--- Đang quét trang {page}: {page_url} ---")

        links = get_article_links(page_url)
        
        if not links:
            empty_count += 1
            if empty_count >= max_empty_pages:
                print("Đã hết bài viết hoặc bị chặn. Kết thúc quá trình cào dữ liệu!")
                break
            page += 1
            continue
        
        empty_count = 0
        page_rows: List[Dict] = []
        
        for link in links:
            print(f"Đang phân tích: {link}")
            recipe_data = parse_article(link)
            
            if not recipe_data:
                print(" -> Bỏ qua (Thiếu thông tin bắt buộc).")
                continue

            page_rows.append(recipe_data)
            total_articles += 1

            # Sleep tránh bị chặn IP
            time.sleep(random.uniform(0.5, 1.5))

        if page_rows:
            write_rows(page_rows)
            print(f"Đã lưu {len(page_rows)} công thức hợp lệ từ Trang {page}.")
        
        page += 1

    print(f"\n✅ HOÀN THÀNH! Tổng cộng đã cào được {total_articles} công thức từ Cookpad.")


if __name__ == "__main__":
    main()