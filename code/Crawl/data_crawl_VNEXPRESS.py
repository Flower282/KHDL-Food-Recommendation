import csv
import os
import random
import time
from typing import Dict, List, Tuple

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

BASE_LIST_URL = "https://vnexpress.net/doi-song/cooking/mon-an"

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "rawCSV")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "mon_an_vnexpress.csv")


def build_list_url(page: int) -> str:
    if page <= 1:
        return BASE_LIST_URL
    return f"{BASE_LIST_URL}-p{page}"


def get_article_links(page_url: str) -> List[str]:
    """Lấy link của các cụm chủ đề món ăn từ trang danh sách chính"""
    links: List[str] = []
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"Lỗi trang danh sách {page_url}: HTTP {response.status_code}")
            return links

        soup = BeautifulSoup(response.content, "html.parser")
        
        # Đi theo cấu trúc thẻ thực tế trong HTML trang danh sách bạn gửi
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


def parse_single_article_block(block: BeautifulSoup) -> Tuple[str, str, str, str, str, str]:
    """Bóc tách dữ liệu từ một block bài viết cụ thể bên trong trang cụm"""
    
    # 1. Lấy tên món ăn
    title_tag = block.select_one("h2.title-detail") or block.select_one(".head-print div:first-child")
    title = title_tag.get_text(strip=True) if title_tag else "N/A"
    
    # 2. Lấy thông tin thời gian, số người, độ khó
    time_val, servings, difficulty = "N/A", "N/A", "N/A"
    status_block = block.select_one(".author-flex .status")
    if status_block:
        # Tìm tất cả các cụm <p class="itemt"> bên trong status
        items = status_block.select("p.itemt")
        for item in items:
            text = item.get_text(strip=True)
            # Dựa vào icon dùng thẻ use để nhận biết hoặc phân biệt qua text văn bản
            use_tag = item.select_one("use")
            href_attr = use_tag.get("xlink:href") if use_tag else ""
            
            if "#clock" in href_attr or "phút" in text or "giờ" in text:
                time_val = text
            elif "#mon" in href_attr or "người" in text:
                servings = text
            elif "#kcal" in href_attr:
                # Nếu muốn lấy thêm calo, bạn có thể gán vào biến riêng, ở đây ta ưu tiên tìm Độ khó
                pass
                
    # Lưu ý: Thường VnExpress Cooking không hiển thị text "Dễ/Khó" bằng thẻ riêng ở giao diện mới 
    # Nếu không tìm thấy độ khó ở cấu trúc thẻ, ta gán mặc định "N/A" hoặc quét trong mô tả.
    
    # 3. Lấy nguyên liệu (từ class chuẩn .choose-ingredients hoặc .list-material)
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
        # Lấy text sạch bên trong, loại bỏ khoảng trắng thừa
        text = item.get_text(strip=True)
        if text:
            steps.append(text)
            
    # Dự phòng nếu họ viết dạng các thẻ p thường trong fck_detail chứ không dùng danh sách nhóm ol > li
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
        
        # Tìm toàn bộ các block công thức món ăn có cấu trúc id chứa "article-"
        article_blocks = soup.find_all("div", id=lambda x: x and x.startswith("article-"))
        
        if not article_blocks:
            # Nếu trang cấu trúc cũ/đơn lẻ, thử parse trực tiếp toàn bộ trang như 1 block lớn
            title, time_val, servings, difficulty, ing, ins = parse_single_article_block(soup)
            if title != "N/A":
                cluster_rows.append({
                    "ten": title, "thoi gian": time_val, "so nguoi": servings,
                    "do kho": difficulty, "nguyen lieu": ing, "cach che bien": ins
                })
        else:
            for block in article_blocks:
                title, time_val, servings, difficulty, ing, ins = parse_single_article_block(block)
                if title != "N/A":
                    cluster_rows.append({
                        "ten": title, "thoi gian": time_val, "so nguoi": servings,
                        "do kho": difficulty, "nguyen lieu": ing, "cach che bien": ins
                    })
    except Exception as exc:
        print(f"Lỗi khi xử lý trang chi tiết cụm {url}: {exc}")
        
    return cluster_rows


def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def write_rows(rows: List[Dict]) -> None:
    if not rows:
        print("Không có dữ liệu mới.")
        return

    file_exists = os.path.isfile(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ten",
                "thoi gian",
                "so nguoi",
                "do kho",
                "nguyen lieu",
                "cach che bien",
            ],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(f"Đã lưu {len(rows)} dòng vào file {OUTPUT_FILE}")


def main() -> None:
    ensure_output_dir()

    try:
        start_page = int(input("Nhập trang bắt đầu: ").strip())
        end_page = int(input("Nhập trang kết thúc: ").strip())
    except ValueError:
        print("Giá trị không hợp lệ. Vui lòng nhập số nguyên.")
        return

    if start_page < 1 or end_page < start_page:
        print("Khoảng trang không hợp lệ.")
        return

    all_rows: List[Dict] = []

    for page in range(start_page, end_page + 1):
        page_url = build_list_url(page)
        print(f"\n--- Đang lấy danh sách cụm món từ: {page_url} ---")

        cluster_links = get_article_links(page_url)
        if not cluster_links:
            print(f"Không tìm thấy cụm bài viết nào ở trang {page}.")
            continue

        for cluster_link in cluster_links:
            print(f"Đang bóc tách cụm chủ đề: {cluster_link}")
            
            # Tiến hành quét sâu toàn bộ món ăn trong cụm chủ đề này
            rows_from_cluster = process_cluster_page(cluster_link)
            all_rows.extend(rows_from_cluster)

            # Nghỉ ngơi ngẫu nhiên để đảm bảo an toàn cho IP
            time.sleep(random.uniform(1.5, 3.0))

    write_rows(all_rows)


if __name__ == "__main__":
    main()