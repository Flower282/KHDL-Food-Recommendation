import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# Test các URLs
urls = [
    "https://afamily.vn/an-ngon/toi-vao-bep.chn",
    "https://afamily.vn/an-ngon/toi-vao-bep.chn?page=1",
    "https://afamily.vn/an-ngon/toi-vao-bep.chn?page=2",
    "https://afamily.vn/an-ngon/toi-vao-bep.chn/page/2",
]

for url in urls:
    print(f"\n{'='*60}")
    print(f"Testing: {url}")
    print('='*60)
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        print(f"Status: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Tìm các item recipe
        items = soup.find_all('li', class_='afctru-li')
        print(f"Found {len(items)} recipe items")
        
        # In các titles
        for i, item in enumerate(items[:5]):
            title_span = item.find('span', class_='afctrull-title')
            if title_span:
                print(f"  {i+1}. {title_span.get_text(strip=True)[:60]}")
        
        # Kiểm tra xem có pagination info không
        pagination = soup.find('div', class_=lambda x: x and 'paging' in str(x).lower())
        if pagination:
            print(f"\nPagination found: {pagination.get_text(strip=True)[:100]}")
        
        # Kiểm tra xem có data-page hoặc attribute liên quan tới page không
        body = soup.find('body')
        if body:
            data_attrs = [attr for attr in body.attrs if 'page' in attr.lower() or 'data' in attr.lower()]
            if data_attrs:
                print(f"Body data attributes: {data_attrs}")
        
    except Exception as e:
        print(f"Error: {e}")
