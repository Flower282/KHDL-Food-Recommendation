import requests
from bs4 import BeautifulSoup
url='https://www.maggi.com.vn/thuc-don-tao-mon-quen/?page=1&content_type=srh_recipe&range=12&searchpage=false'
r=requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=15)
print('status', r.status_code)
print('len', len(r.text))
print('snippet', r.text[0:200])
