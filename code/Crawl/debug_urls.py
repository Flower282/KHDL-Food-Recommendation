import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# Test các URLs khác nhau
urls = [
    ("Tôi vào bếp", "https://afamily.vn/an-ngon/toi-vao-bep.chn"),
    ("Khéo tay", "https://afamily.vn/an-ngon/kheo-tay.chn"),
    ("Mẹo vặt", "https://afamily.vn/an-ngon/meo-vat.chn"),
    ("Ăn ngon (chính)", "https://afamily.vn/an-ngon.chn"),
]

print("Kiểm tra số lượng công thức trên các trang:")
print("=" * 60)

for name, url in urls:
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Tìm các recipe items
        items = soup.find_all('li', class_='afctru-li')
        
        print(f"\n{name}")
        print(f"URL: {url}")
        print(f"Số công thức tìm được: {len(items)}")
        
        if items:
            print("Các công thức:")
            for i, item in enumerate(items[:5]):
                title_span = item.find('span', class_='afctrull-title')
                if title_span:
                    print(f"  {i+1}. {title_span.get_text(strip=True)[:60]}")
        
    except Exception as e:
        print(f"Error: {e}")

# Kiểm tra xem có API endpoint nào
print("\n" + "=" * 60)
print("Kiểm tra API endpoints:")
print("=" * 60)

test_api_urls = [
    "https://s3.afamily.vn/api/news/list",
    "https://s3.afamily.vn/api/category/23654",
    "https://s3.afamily.vn/api/zone/23654",
    "https://afamily.vn/api/news/list",
]

for url in test_api_urls:
    try:
        print(f"\nTesting: {url}")
        response = requests.get(url, headers=HEADERS, timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Content preview: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {type(e).__name__}")
