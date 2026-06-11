"""
===================================================================
TEST TOÀN DIỆN NEO4J + HỆ THỐNG GỢI Ý MÓN ĂN
===================================================================
Chạy từ thư mục gốc project:
    python test_neo4j_full.py

Yêu cầu: pip install neo4j
===================================================================
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Đảm bảo project root trong sys.path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env
_env = PROJECT_ROOT / ".env"
if _env.exists():
    with open(_env, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _v = _line.split("=", 1)
            _k, _v = _k.strip(), _v.strip().strip("'\"")
            if _k and _k not in os.environ:
                os.environ[_k] = _v

NEO4J_URI      = os.getenv("NEO4J_URI",      "neo4j+s://4ed018bf.databases.neo4j.io")
NEO4J_USER     = os.getenv("NEO4J_USER",     "4ed018bf")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "7he_IgP45assE3vsuO3GpWaxcNVmMxa-3npnUJAm1XM")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "4ed018bf")

STOCK_FILE  = PROJECT_ROOT / "data" / "Kho.json"
RECIPE_FILE = PROJECT_ROOT / "result" / "data_monan_day_du_CP.json"

# ANSI colors
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

PASS = f"{GREEN}✓ PASS{RESET}"
FAIL = f"{RED}✗ FAIL{RESET}"
INFO = f"{CYAN}ℹ{RESET}"
WARN = f"{YELLOW}⚠{RESET}"


# ===========================================================================
# SECTION 1 – NEO4J CONNECTION & DATA STATS
# ===========================================================================

def section_header(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'='*65}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*65}{RESET}")


def test_neo4j_connection(driver) -> bool:
    """Test 1: Kết nối cơ bản."""
    print(f"\n{BOLD}[TEST 1] Kết nối Neo4j Aura{RESET}")
    try:
        driver.verify_connectivity()
        print(f"  {PASS} verify_connectivity() thành công")
        print(f"  {INFO} URI: {NEO4J_URI}")
        print(f"  {INFO} User: {NEO4J_USER} | Database: {NEO4J_DATABASE}")
        return True
    except Exception as exc:
        print(f"  {FAIL} {exc}")
        return False


def query_node_counts(driver) -> dict:
    """Test 2: Đếm node theo từng label."""
    print(f"\n{BOLD}[TEST 2] Số lượng node trong KG{RESET}")
    counts = {}
    labels = ["Dish", "Ingredient", "DishType", "Difficulty", "StockItem"]
    with driver.session(database=NEO4J_DATABASE) as session:
        for label in labels:
            result = session.run(f"MATCH (n:{label}) RETURN count(n) AS cnt")
            cnt = result.single()["cnt"]
            counts[label] = cnt
            icon = PASS if cnt > 0 else WARN
            print(f"  {icon} {label:<14}: {cnt:>6} nodes")
    return counts


def query_relationship_counts(driver) -> None:
    """Test 3: Đếm relationship."""
    print(f"\n{BOLD}[TEST 3] Số lượng quan hệ (relationships){RESET}")
    rels = ["HAS_INGREDIENT", "HAS_TYPE", "HAS_DIFFICULTY", "REFERS_TO"]
    with driver.session(database=NEO4J_DATABASE) as session:
        for rel in rels:
            result = session.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS cnt")
            cnt = result.single()["cnt"]
            icon = PASS if cnt > 0 else WARN
            print(f"  {icon} {rel:<20}: {cnt:>6} relationships")


def query_sample_dishes(driver) -> None:
    """Test 4: Xem 5 món ăn mẫu."""
    print(f"\n{BOLD}[TEST 4] Mẫu 5 món ăn đầu tiên trong KG{RESET}")
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            "MATCH (d:Dish) "
            "OPTIONAL MATCH (d)-[:HAS_DIFFICULTY]->(f:Difficulty) "
            "RETURN d.name AS name, d.time_minutes AS mins, f.name AS diff "
            "ORDER BY d.name LIMIT 5"
        )
        for i, record in enumerate(result, 1):
            name = record["name"]
            mins = record["mins"] if record["mins"] else "?"
            diff = record["diff"] if record["diff"] else "?"
            print(f"  {i}. {name[:55]:<55} | {mins:>4} phút | {diff}")


def query_sample_ingredients(driver) -> None:
    """Test 5: Xem top 5 nguyên liệu xuất hiện nhiều nhất."""
    print(f"\n{BOLD}[TEST 5] Top 5 nguyên liệu phổ biến nhất{RESET}")
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            "MATCH (d:Dish)-[:HAS_INGREDIENT]->(i:Ingredient) "
            "RETURN i.display_name AS name, count(d) AS usage "
            "ORDER BY usage DESC LIMIT 5"
        )
        for i, record in enumerate(result, 1):
            print(f"  {i}. {record['name']:<35} → {record['usage']:>4} món")


def query_stock_items(driver) -> None:
    """Test 6: Kiểm tra StockItem & REFERS_TO."""
    print(f"\n{BOLD}[TEST 6] Kho nguyên liệu và ánh xạ tới Ingredient{RESET}")
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            "MATCH (s:StockItem)-[r:REFERS_TO]->(i:Ingredient) "
            "RETURN s.name AS stock, s.available_raw AS qty, i.display_name AS ing, r.name_score AS score "
            "ORDER BY r.name_score DESC LIMIT 10"
        )
        rows = list(result)
        if not rows:
            print(f"  {WARN} Không tìm thấy StockItem nào có REFERS_TO!")
        else:
            print(f"  {'Kho':<22} {'Qty':<12} {'Nguyên liệu KG':<30} {'Score'}")
            print(f"  {'-'*80}")
            for rec in rows:
                score_color = GREEN if (rec["score"] or 0) >= 0.75 else YELLOW
                print(
                    f"  {str(rec['stock']):<22} "
                    f"{str(rec['qty'] or '?'):<12} "
                    f"{str(rec['ing']):<30} "
                    f"{score_color}{rec['score']:.3f}{RESET}"
                )


def query_dish_by_ingredient(driver, ingredient_name: str = "thịt gà") -> None:
    """Test 7: Tìm món chứa nguyên liệu nhất định."""
    print(f"\n{BOLD}[TEST 7] Món ăn chứa '{ingredient_name}'{RESET}")
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            "MATCH (d:Dish)-[r:HAS_INGREDIENT]->(i:Ingredient) "
            "WHERE toLower(i.display_name) CONTAINS toLower($name) "
            "   OR toLower(i.canonical_name) CONTAINS toLower($name) "
            "RETURN DISTINCT d.name AS dish, d.time_minutes AS mins "
            "ORDER BY d.time_minutes LIMIT 8",
            {"name": ingredient_name},
        )
        rows = list(result)
        if not rows:
            print(f"  {WARN} Không tìm thấy món nào chứa '{ingredient_name}'")
        else:
            for rec in rows:
                mins_str = f"{rec['mins']} phút" if rec["mins"] else "?"
                print(f"  → {rec['dish'][:55]:<55} | {mins_str}")


def query_dish_types_distribution(driver) -> None:
    """Test 8: Phân bố loại món ăn."""
    print(f"\n{BOLD}[TEST 8] Phân bố loại món ăn (DishType){RESET}")
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            "MATCH (d:Dish)-[:HAS_TYPE]->(t:DishType) "
            "RETURN t.display_name AS type, count(d) AS cnt "
            "ORDER BY cnt DESC LIMIT 10"
        )
        rows = list(result)
        if not rows:
            print(f"  {WARN} Không tìm thấy DishType nào!")
        else:
            for rec in rows:
                bar = "█" * min(int(rec["cnt"] / 2), 40)
                print(f"  {str(rec['type']):<20} {rec['cnt']:>5}  {bar}")


# ===========================================================================
# SECTION 2 – RECOMMENDATION ENGINE TEST
# ===========================================================================

def test_recommendation_engine() -> None:
    """Test 9 & 10: Chạy engine gợi ý từ file JSON."""
    section_header("SECTION 2 – RECOMMENDATION ENGINE (từ file JSON)")

    # Kiểm tra file tồn tại
    print(f"\n{BOLD}[TEST 9] Kiểm tra file dữ liệu{RESET}")
    for label, path in [("Kho (Stock)", STOCK_FILE), ("Recipe", RECIPE_FILE)]:
        if path.exists():
            size_kb = path.stat().st_size // 1024
            print(f"  {PASS} {label}: {path.name} ({size_kb} KB)")
        else:
            print(f"  {FAIL} Không tìm thấy: {path}")
            print(f"  {WARN} Test gợi ý sẽ bị bỏ qua.")
            return

    print(f"\n{BOLD}[TEST 10] Chạy recommendation engine{RESET}")
    try:
        from code.KG.recommender import load_and_recommend

        t0 = time.time()
        result = load_and_recommend(
            recipe_path=RECIPE_FILE,
            stock_path=STOCK_FILE,
            top_k=10,
            max_dishes=3,
        )
        elapsed = time.time() - t0

        print(f"  {PASS} Engine chạy xong trong {elapsed:.2f}s")

        top_dishes = result.get("top_dishes", [])
        meal_set   = result.get("meal_set", [])

        print(f"\n  {BOLD}TOP {len(top_dishes)} MÓN PHÙ HỢP NHẤT:{RESET}")
        if top_dishes:
            print(f"  {'#':<4} {'Tên món':<45} {'Score':>6} {'Thiếu NL'}")
            print(f"  {'-'*70}")
            for idx, dish in enumerate(top_dishes, 1):
                score_color = GREEN if dish['score'] >= 0.6 else (YELLOW if dish['score'] >= 0.4 else RED)
                print(
                    f"  {idx:<4} {dish['dish_name'][:44]:<45} "
                    f"{score_color}{dish['score']:>6.4f}{RESET} "
                    f"{dish['missing_required']:>4}"
                )
        else:
            print(f"  {WARN} Không có món nào thỏa điều kiện.")

        print(f"\n  {BOLD}TỔ HỢP {len(meal_set)} MÓN ĐƯỢC GỢI Ý:{RESET}")
        if meal_set:
            for idx, dish in enumerate(meal_set, 1):
                print(
                    f"  {idx}. {dish['dish_name'][:55]:<55} "
                    f"| score={dish['score']:.4f} "
                    f"| type={dish.get('dish_type', '?')}"
                )
        else:
            print(f"  {WARN} Không tạo được tổ hợp món.")

    except ImportError as exc:
        print(f"  {FAIL} Import lỗi: {exc}")
    except Exception as exc:
        import traceback
        print(f"  {FAIL} Exception: {exc}")
        traceback.print_exc()


def test_recommendation_with_filter() -> None:
    """Test 11: Gợi ý với bộ lọc thời gian."""
    print(f"\n{BOLD}[TEST 11] Gợi ý món ăn ≤ 30 phút{RESET}")
    if not RECIPE_FILE.exists() or not STOCK_FILE.exists():
        print(f"  {WARN} Bỏ qua (thiếu file dữ liệu)")
        return
    try:
        from code.KG.recommender import load_and_recommend
        result = load_and_recommend(
            recipe_path=RECIPE_FILE,
            stock_path=STOCK_FILE,
            top_k=5,
            max_dishes=2,
            max_minutes=30,
        )
        dishes = result.get("top_dishes", [])
        if dishes:
            print(f"  {PASS} Tìm được {len(dishes)} món ≤ 30 phút:")
            for d in dishes:
                print(f"    → {d['dish_name'][:55]}")
        else:
            print(f"  {WARN} Không có món nào ≤ 30 phút trong kho hiện tại.")
    except Exception as exc:
        print(f"  {FAIL} {exc}")


def test_neo4j_recommend_query(driver) -> None:
    """Test 12: Gợi ý trực tiếp từ Neo4j bằng Cypher."""
    section_header("SECTION 3 – GỢI Ý TRỰC TIẾP TỪ NEO4J (Cypher)")

    print(f"\n{BOLD}[TEST 12] Query Cypher: Món có nguyên liệu khớp với kho{RESET}")

    # Lấy danh sách tên nguyên liệu trong kho
    with open(STOCK_FILE, encoding="utf-8") as f:
        stock_data = json.load(f)
    stock_names = [item["tên"].lower() for item in stock_data if item.get("tên")]
    print(f"  {INFO} Kho có {len(stock_names)} nguyên liệu: {', '.join(stock_names[:6])}...")

    with driver.session(database=NEO4J_DATABASE) as session:
        # Tìm món mà nguyên liệu chính khớp với tên kho (fuzzy: CONTAINS)
        cypher = """
        MATCH (s:StockItem)-[:REFERS_TO]->(i:Ingredient)<-[r:HAS_INGREDIENT]-(d:Dish)
        WHERE r.group = 'main_ingredients'
        WITH d, count(DISTINCT i) AS matched_count
        ORDER BY matched_count DESC
        LIMIT 10
        MATCH (d)-[:HAS_DIFFICULTY]->(f:Difficulty)
        RETURN d.name AS dish, d.time_minutes AS mins, f.name AS diff, matched_count
        ORDER BY matched_count DESC, d.time_minutes ASC
        """
        try:
            result = session.run(cypher)
            rows = list(result)
            if not rows:
                print(f"  {WARN} Không tìm được kết quả. Thử query đơn giản hơn...")
                # Fallback: chỉ dùng REFERS_TO
                fallback = """
                MATCH (s:StockItem)-[:REFERS_TO]->(i:Ingredient)<-[:HAS_INGREDIENT]-(d:Dish)
                WITH d, count(DISTINCT s) AS stock_match
                ORDER BY stock_match DESC LIMIT 5
                RETURN d.name AS dish, stock_match
                """
                result2 = session.run(fallback)
                rows2 = list(result2)
                if rows2:
                    print(f"  {PASS} Fallback query tìm được {len(rows2)} món:")
                    for rec in rows2:
                        print(f"    → {rec['dish'][:55]:<55} (khớp {rec['stock_match']} stock)")
                else:
                    print(f"  {WARN} Fallback cũng không có kết quả.")
            else:
                print(f"  {PASS} Tìm được {len(rows)} món phù hợp với kho:")
                print(f"  {'Tên món':<50} {'Phút':>6} {'Khó':>12} {'Khớp NL':>8}")
                print(f"  {'-'*80}")
                for rec in rows:
                    print(
                        f"  {str(rec['dish'])[:49]:<50} "
                        f"{str(rec['mins'] or '?'):>6} "
                        f"{str(rec['diff'] or '?'):>12} "
                        f"{rec['matched_count']:>8}"
                    )
        except Exception as exc:
            print(f"  {FAIL} Cypher error: {exc}")


def test_full_graph_stats(driver) -> None:
    """Test 13: Tổng quan toàn bộ graph."""
    print(f"\n{BOLD}[TEST 13] Tổng quan graph{RESET}")
    with driver.session(database=NEO4J_DATABASE) as session:
        total_nodes = session.run("MATCH (n) RETURN count(n) AS cnt").single()["cnt"]
        total_rels  = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()["cnt"]
        print(f"  {INFO} Tổng nodes       : {total_nodes}")
        print(f"  {INFO} Tổng relationships: {total_rels}")

        # Avg ingredients per dish
        avg_ing = session.run(
            "MATCH (d:Dish)-[:HAS_INGREDIENT]->(i) "
            "WITH d, count(i) AS cnt "
            "RETURN round(avg(cnt), 1) AS avg"
        ).single()["avg"]
        print(f"  {INFO} TB nguyên liệu/món: {avg_ing}")


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    # Windows encoding fix
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print(f"\n{BOLD}{CYAN}{'='*65}")
    print("  KIỂM TRA HỆ THỐNG GỢI Ý MÓN ĂN – NEO4J KNOWLEDGE GRAPH")
    print(f"{'='*65}{RESET}")

    # -----------------------------------------------------------------------
    # Kết nối Neo4j
    # -----------------------------------------------------------------------
    section_header("SECTION 1 – NEO4J DATA VERIFICATION")

    try:
        # pyrefly: ignore [missing-import]
        from neo4j import GraphDatabase
    except ImportError:
        print(f"\n{FAIL} Chưa cài neo4j. Chạy: pip install neo4j")
        sys.exit(1)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    connected = test_neo4j_connection(driver)
    if not connected:
        print(f"\n{RED}Không thể kết nối Neo4j. Dừng test.{RESET}")
        driver.close()
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Neo4j data tests
    # -----------------------------------------------------------------------
    counts = query_node_counts(driver)
    query_relationship_counts(driver)
    query_sample_dishes(driver)
    query_sample_ingredients(driver)
    query_stock_items(driver)
    query_dish_by_ingredient(driver, "thịt gà")
    query_dish_by_ingredient(driver, "tôm")
    query_dish_types_distribution(driver)
    test_full_graph_stats(driver)

    # -----------------------------------------------------------------------
    # Recommendation engine tests
    # -----------------------------------------------------------------------
    test_recommendation_engine()
    test_recommendation_with_filter()
    test_neo4j_recommend_query(driver)

    driver.close()

    # -----------------------------------------------------------------------
    # Tổng kết
    # -----------------------------------------------------------------------
    print(f"\n{BOLD}{CYAN}{'='*65}{RESET}")
    print(f"{BOLD}  KẾT QUẢ TỔNG KẾT{RESET}")
    print(f"{BOLD}{CYAN}{'='*65}{RESET}")
    dish_cnt = counts.get("Dish", 0)
    ing_cnt  = counts.get("Ingredient", 0)
    stock_cnt = counts.get("StockItem", 0)
    status = GREEN + "SẵN SÀNG" + RESET if dish_cnt > 0 and ing_cnt > 0 else RED + "CHƯA ĐỦ DATA" + RESET
    print(f"  Trạng thái KG : {status}")
    print(f"  Món ăn        : {dish_cnt}")
    print(f"  Nguyên liệu   : {ing_cnt}")
    print(f"  Kho (Stock)   : {stock_cnt}")
    print()


if __name__ == "__main__":
    main()
