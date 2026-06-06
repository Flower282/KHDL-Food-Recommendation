import csv
import json
import os
import random
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Referer": "https://www.knorr.com/",
    "Upgrade-Insecure-Requests": "1",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAWCSV_DIR = PROJECT_ROOT / "rawCSV"
DEFAULT_OUTPUT_FILE = RAWCSV_DIR / "maggi_knorr_raw.csv"
MAGGI_BASE = "https://www.maggi.com.vn/thuc-don-tao-mon-quen/"
KNORR_BASE = "https://www.knorr.com/vn/cong-thuc-nau-an.html"


def ensure_output_folder() -> None:
    RAWCSV_DIR.mkdir(parents=True, exist_ok=True)


def build_maggi_list_url(page: int) -> str:
    query = "content_type=srh_recipe&range=12&searchpage=false"
    if page <= 1:
        return f"{MAGGI_BASE}?{query}"
    return f"{MAGGI_BASE}?page={page - 1}&{query}"


def is_maggi_listing(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc.endswith("maggi.com.vn") and parsed.path.strip("/") == "thuc-don-tao-mon-quen"


def is_knorr_listing(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc.endswith("knorr.com") and parsed.path.strip("/") == "vn/cong-thuc-nau-an.html"


def is_maggi_recipe(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc.endswith("maggi.com.vn") and parsed.path.startswith("/cong-thuc/")


def is_knorr_recipe(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc.endswith("knorr.com") and parsed.path.startswith("/vn/r/")


def fetch_html(url: str, timeout: int = 15) -> Optional[str]:
    try:
        response = SESSION.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except Exception as exc:
        print(f"⚠️  Failed to fetch {url}: {exc}")
        return None


def parse_jsonld_recipe(html: str) -> Optional[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    jsonld_scripts = soup.find_all("script", type="application/ld+json")

    for script in jsonld_scripts:
        if not script.string:
            continue

        try:
            payload = json.loads(script.string)
        except json.JSONDecodeError:
            continue

        if isinstance(payload, dict) and payload.get("@type") == "Recipe":
            return payload

        if isinstance(payload, dict) and "@graph" in payload:
            for item in payload["@graph"]:
                if isinstance(item, dict) and item.get("@type") == "Recipe":
                    return item

        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and item.get("@type") == "Recipe":
                    return item

    return None


def iso_duration_to_text(duration: str) -> str:
    if not duration or not duration.startswith("PT"):
        return duration or "N/A"

    hours = 0
    minutes = 0
    value = duration[2:]
    num = ""

    for char in value:
        if char.isdigit():
            num += char
            continue
        if char == "H" and num:
            hours = int(num)
            num = ""
            continue
        if char == "M" and num:
            minutes = int(num)
            num = ""
            continue

    parts = []
    if hours:
        parts.append(f"{hours} giờ")
    if minutes:
        parts.append(f"{minutes} phút")
    if not parts:
        parts.append("0 phút")
    return " ".join(parts)


def normalize_recipe_time(recipe: Dict) -> str:
    for key in ["totalTime", "cookTime", "prepTime"]:
        value = recipe.get(key)
        if value:
            return iso_duration_to_text(value)
    return "N/A"


def flatten_recipe_instructions(instructions) -> List[str]:
    if instructions is None:
        return []

    if isinstance(instructions, str):
        return [instructions.strip()]

    if isinstance(instructions, dict):
        if instructions.get("text"):
            return [instructions["text"].strip()]
        if instructions.get("itemListElement"):
            return flatten_recipe_instructions(instructions["itemListElement"])
        return []

    if isinstance(instructions, list):
        steps: List[str] = []
        for item in instructions:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    steps.append(text)
                continue

            if isinstance(item, dict):
                if item.get("@type", "").lower().endswith("section"):
                    header = item.get("name")
                    if header:
                        steps.append(header.strip())
                    nested = item.get("itemListElement")
                    steps.extend(flatten_recipe_instructions(nested))
                elif item.get("@type", "").lower().endswith("step"):
                    text = item.get("text") or item.get("name")
                    if text:
                        steps.append(text.strip())
                elif item.get("itemListElement"):
                    steps.extend(flatten_recipe_instructions(item.get("itemListElement")))
        return steps

    return []


def extract_maggi_links_from_list_page(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    for anchor in soup.select("ul.seo-render--searchItem li a[href]"):
        href = anchor["href"].strip()
        if not href:
            continue
        full_url = urljoin(MAGGI_BASE, href)
        if full_url not in links:
            links.append(full_url)
    return links


def extract_knorr_links_from_list_page(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    for anchor in soup.select("a.cmp-recipe-listing-title[href]"):
        href = anchor["href"].strip()
        if href and href.startswith("/vn/r/"):
            full_url = urljoin("https://www.knorr.com", href)
            if full_url not in links:
                links.append(full_url)

    if not links:
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            if href.startswith("/vn/r/"):
                full_url = urljoin("https://www.knorr.com", href)
                if full_url not in links:
                    links.append(full_url)
    return links


def parse_maggi_recipe_page(url: str) -> Optional[Dict[str, str]]:
    html = fetch_html(url)
    if html is None:
        return None

    recipe = parse_jsonld_recipe(html)
    if recipe is None:
        print(f"⚠️  No recipe data found for Maggi URL: {url}")
        return None

    ingredients = recipe.get("recipeIngredient") or []
    instructions = flatten_recipe_instructions(recipe.get("recipeInstructions"))

    return {
        "tên": recipe.get("name", "N/A"),
        "thời gian": normalize_recipe_time(recipe),
        "số người": recipe.get("recipeYield", "N/A"),
        "độ khó": recipe.get("difficulty", "N/A"),
        "nguyên liệu": " | ".join(str(item).strip() for item in ingredients if item),
        "cách chế biến": " | ".join(instructions) if instructions else "N/A",
        "link": url,
    }


def parse_knorr_recipe_page(url: str) -> Optional[Dict[str, str]]:
    html = fetch_html(url)
    if html is None:
        return None

    recipe = parse_jsonld_recipe(html)
    if recipe is None:
        print(f"⚠️  No recipe data found for Knorr URL: {url}")
        return None

    ingredients = recipe.get("recipeIngredient") or []
    instructions = flatten_recipe_instructions(recipe.get("recipeInstructions"))

    return {
        "tên": recipe.get("name", "N/A"),
        "thời gian": normalize_recipe_time(recipe),
        "số người": recipe.get("recipeYield", "N/A"),
        "độ khó": recipe.get("difficulty", "N/A"),
        "nguyên liệu": " | ".join(str(item).strip() for item in ingredients if item),
        "cách chế biến": " | ".join(instructions) if instructions else "N/A",
        "link": url,
    }


def crawl_maggi_listing(start_page: int = 1, end_page: int = 1) -> List[Dict[str, str]]:
    results = []
    for page in range(start_page, end_page + 1):
        page_url = build_maggi_list_url(page)
        print(f"🔎 Crawling Maggi list page: {page_url}")
        html = fetch_html(page_url)
        if html is None:
            continue

        links = extract_maggi_links_from_list_page(html)
        print(f"   ➜ Found {len(links)} recipe links")
        for recipe_url in links:
            print(f"   🥘 Parsing Maggi recipe: {recipe_url}")
            recipe = parse_maggi_recipe_page(recipe_url)
            if recipe:
                results.append(recipe)
            time.sleep(random.uniform(1.0, 2.5))

        time.sleep(random.uniform(1.0, 2.5))
    return results


def crawl_knorr_listing(url: str) -> List[Dict[str, str]]:
    print(f"🔎 Crawling Knorr list page: {url}")
    html = fetch_html(url)
    if html is None:
        return []

    links = extract_knorr_links_from_list_page(html)
    print(f"   ➜ Found {len(links)} recipe links")
    results = []
    for recipe_url in links:
        print(f"   🥘 Parsing Knorr recipe: {recipe_url}")
        recipe = parse_knorr_recipe_page(recipe_url)
        if recipe:
            results.append(recipe)
        time.sleep(random.uniform(1.0, 2.5))
    return results


def save_to_csv(rows: List[Dict[str, str]], filename: str) -> None:
    if not rows:
        print("⚠️  No recipes to save.")
        return

    ensure_output_folder()
    file_exists = os.path.exists(filename)
    fieldnames = ["tên", "thời gian", "số người", "độ khó", "nguyên liệu", "cách chế biến", "link"]

    with open(filename, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Saved {len(rows)} recipes to {filename}")


def crawl_urls(urls: List[str], output_file: Optional[str] = None, save: bool = True) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for url in urls:
        if is_maggi_listing(url):
            rows.extend(crawl_maggi_listing(start_page=1, end_page=1))
        elif is_knorr_listing(url):
            rows.extend(crawl_knorr_listing(url))
        elif is_maggi_recipe(url):
            print(f"🔎 Parsing Maggi recipe: {url}")
            recipe = parse_maggi_recipe_page(url)
            if recipe:
                rows.append(recipe)
        elif is_knorr_recipe(url):
            print(f"🔎 Parsing Knorr recipe: {url}")
            recipe = parse_knorr_recipe_page(url)
            if recipe:
                rows.append(recipe)
        else:
            print(f"⚠️  Unsupported URL structure. Trying to parse as a recipe page: {url}")
            parsed = urlparse(url)
            if parsed.netloc.endswith("maggi.com.vn"):
                recipe = parse_maggi_recipe_page(url)
            elif parsed.netloc.endswith("knorr.com"):
                recipe = parse_knorr_recipe_page(url)
            else:
                recipe = None
            if recipe:
                rows.append(recipe)

    if save:
        if output_file is None:
            output_file = str(DEFAULT_OUTPUT_FILE)
        save_to_csv(rows, output_file)

    return rows


def crawl_default(output_file: Optional[str] = None) -> List[Dict[str, str]]:
    print("🚀 Crawling default Maggi and Knorr sources")
    urls = [MAGGI_BASE, KNORR_BASE]
    return crawl_urls(urls, output_file=output_file, save=True)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Crawl Maggi and Knorr recipe URLs and save them as a raw CSV file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url",
        action="append",
        help="One or more URLs to crawl. Can be Maggi listing pages, Knorr listing pages, or direct recipe pages.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT_FILE),
        help="Output CSV file path. Defaults to rawCSV/maggi_knorr_raw.csv",
    )
    parser.add_argument(
        "--maggi-pages",
        nargs=2,
        type=int,
        metavar=("START", "END"),
        help="Crawl Maggi recipe list pages from START to END (inclusive).",
    )
    args = parser.parse_args()

    urls: List[str] = args.url or []
    if not urls and not args.maggi_pages:
        urls = [MAGGI_BASE, KNORR_BASE]

    rows: List[Dict[str, str]] = []
    if args.maggi_pages:
        start, end = args.maggi_pages
        rows.extend(crawl_maggi_listing(start_page=start, end_page=end))

    if urls:
        rows.extend(crawl_urls(urls, output_file=args.output, save=False))
    elif not args.maggi_pages:
        rows.extend(crawl_default(output_file=args.output))

    if rows:
        if args.output:
            save_to_csv(rows, args.output)
        print(f"\n✅ Total recipes parsed: {len(rows)}")
    else:
        print("\n⚠️  No recipes were parsed.")


if __name__ == "__main__":
    main()
