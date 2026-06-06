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

BASE_LIST_URL = "https://vnexpress.net/doi-song/cooking/mon-an"

PROJECT_ROOT = os.getcwd()
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "rawCSV")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "mon_an_vnexpress.csv")


def build_list_url(page: int) -> str:
    """Tạo URL cho các trang danh sách (Pagination)"""
    if page <= 1:
        return BASE_LIST_URL
    return f"{BASE_LIST_URL}-p{page}"


def get_article_links(page_url: str) -> List[str]:
    """Lấy link của các cụm chủ đề món ăn từ trang danh sách chính"""
    links: List[str] = []
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=10)
        # VnExpress khi quá số trang thường trả về 404 hoặc trang không có article
        if response.status_code != 200:
            return links

        soup = BeautifulSoup(response.content, "html.parser")
        
        for a_tag in soup.select("div.list-dish article.art_item h3.title_news a"):
            href = a_tag.get("href")
            if href:
                if not href.startswith("http"):
                    href = "https://vnexpress.net" + href
                if href not in links and "cooking/mon-an" in href:
                    links.append(href)
    except Exception as exc:
        print(f"Lỗi trang danh sách {page_url}: {exc}")
    return links


def clean_title(raw_title: str) -> str:
    """Loại bỏ các từ khóa thừa ở đầu tên món ăn và chuẩn hóa viết hoa"""
    if not raw_title or raw_title == "N/A":
        return "N/A"
        
    # Danh sách các cụm từ cần loại bỏ ở ĐẦU câu
    prefixes = r"^(hướng dẫn cách làm|hướng dẫn cách nấu|hướng dẫn làm|hướng dẫn nấu|hướng dẫn|cách làm|cách nấu|cách)\s+"
    
    # Thực hiện thay thế/loại bỏ
    cleaned = re.sub(prefixes, "", raw_title, flags=re.IGNORECASE).strip()
    
    # Viết hoa chữ cái đầu tiên
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
        
    return cleaned if cleaned else "N/A"


def parse_single_article_block(block: BeautifulSoup) -> Tuple[str, str, str, str, str, str]:
    """Bóc tách dữ liệu từ một block bài viết cụ thể bên trong trang cụm"""
    
    # 1. Lấy tên món ăn và làm sạch
    title_tag = block.select_one("h2.title-detail") or block.select_one(".head-print div:first-child")
    raw_title = title_tag.get_text(strip=True) if title_tag else "N/A"
    title = clean_title(raw_title)
    
    # 2. Thiết lập giá trị mặc định cho thời gian, số người, độ khó
    time_val = "60 phút"
    servings = "4 người"
    difficulty = "Dễ"
    
    status_block = block.select_one(".author-flex .status")
    if status_block:
        items = status_block.select("p.itemt")
        for item in items:
            text = item.get_text(strip=True)
            use_tag = item.select_one("use")
            href_attr = use_tag.get("xlink:href") if use_tag else ""
            
            # Cập nhật nếu tìm thấy dữ liệu thực tế
            if "#clock" in href_attr or "phút" in text or "giờ" in text:
                time_val = text
            elif "#mon" in href_attr or "người" in text:
                servings = text
            
    # 3. Lấy nguyên liệu
    ingredients = []
    material_items = block.select(".choose-ingredients label.check-list .name, .list-material li")
    for item in material_items:
        text = item.get_text(strip=True)
        if text:
            ingredients.append(text)
    ingredients_str = " | ".join(ingredients) if ingredients else "N/A"
    
    # 4. Lấy cách chế biến
    steps = []
    instruction_items = block.select(".content-detail .steep ol li, .fck_detail ol li")
    for item in instruction_items:
        text = item.get_text(strip=True)
        if text:
            steps.append(text)
            
    # Dự phòng nếu cấu trúc thẻ P thường
    if not steps:
        content_div = block.select_one(".content-detail, .fck_detail")
        if content_div:
            for p in content_div.find_all("p", class_="Normal"):
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    steps.append(text)
                    
    instructions_str = " | ".join(steps) if steps else "N/A"
    
    return title, time_val, servings, difficulty, ingredients_str, instructions_str


def process_cluster_page(url: str) -> List[Dict]:
    """Truy cập trang cụm (Ví dụ: Bún cá) và quét mọi bài viết/món ăn có trong đó"""
    cluster_rows = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return cluster_rows

        soup = BeautifulSoup(response.content, "html.parser")
        
        # VnExpress Cooking gom nhiều công thức trong 1 cụm bài viết, ID dạng article-xxxx
        article_blocks = soup.find_all("div", id=lambda x: x and x.startswith("article-"))
        
        blocks_to_parse = article_blocks if article_blocks else [soup]
        
        for block in blocks_to_parse:
            title, time_val, servings, difficulty, ing, ins = parse_single_article_block(block)
            
            # ĐIỀU KIỆN BẮT BUỘC: Thiếu Tên, Nguyên Liệu hoặc Cách làm thì loại bỏ
            if title != "N/A" and ing != "N/A" and ins != "N/A":
                cluster_rows.append({
                    "ten": title,
                    "thoi gian": time_val,
                    "so nguoi": servings,
                    "do kho": difficulty,
                    "nguyen lieu": ing,
                    "cach che bien": ins
                })
            else:
                print(f" -> Bỏ qua món ăn vì thiếu thông tin bắt buộc (Tên: {title}).")
                
    except Exception as exc:
        print(f"Lỗi khi xử lý trang chi tiết cụm {url}: {exc}")
        
    return cluster_rows


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
    print(f"Bắt đầu thu thập dữ liệu. File sẽ được lưu tại: {OUTPUT_FILE}")

    page = 1
    total_articles = 0

    while True:
        page_url = build_list_url(page)
        print(f"\n--- Đang lấy danh sách cụm món từ Trang {page}: {page_url} ---")

        cluster_links = get_article_links(page_url)
        
        # Nếu không còn link bài viết nào, dừng vòng lặp cào
        if not cluster_links:
            print(f"Đã duyệt hết các trang hoặc trang {page} không tồn tại. Kết thúc quá trình cào dữ liệu!")
            break

        page_rows: List[Dict] = []

        for cluster_link in cluster_links:
            print(f"Đang bóc tách cụm chủ đề: {cluster_link}")
            
            rows_from_cluster = process_cluster_page(cluster_link)
            page_rows.extend(rows_from_cluster)

            # Nghỉ ngơi ngẫu nhiên để đảm bảo an toàn cho IP
            time.sleep(random.uniform(1.5, 3.0))

        # Lưu dữ liệu sau mỗi trang
        if page_rows:
            write_rows(page_rows)
            total_articles += len(page_rows)
            print(f"Đã lưu {len(page_rows)} công thức hợp lệ từ Trang {page}.")

        # Chuyển sang trang tiếp theo
        page += 1

    print(f"\n✅ HOÀN THÀNH! Tổng cộng đã cào được {total_articles} công thức nấu ăn hợp lệ từ VnExpress Cooking.")


if __name__ == "__main__":
    main()