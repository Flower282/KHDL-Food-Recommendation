from playwright.sync_api import sync_playwright

KNORR_LIST = "https://www.knorr.com/vn/cong-thuc-nau-an.html"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    try:
        resp = page.goto(KNORR_LIST, timeout=30000)
        status = resp.status if resp else 'no-response'
        print('listing_status', status)
        # wait briefly for dynamic content
        try:
            page.wait_for_selector('a[href^="/vn/r/"]', timeout=5000)
        except Exception:
            pass
        anchors = page.query_selector_all('a[href^="/vn/r/"]')
        links = []
        for a in anchors:
            href = a.get_attribute('href')
            if href and href.startswith('/vn/r/'):
                full = 'https://www.knorr.com' + href
                if full not in links:
                    links.append(full)
        print('found_links_count', len(links))
        for ln in links[:10]:
            print(ln)
    except Exception as e:
        print('ERROR', e)
    finally:
        browser.close()
