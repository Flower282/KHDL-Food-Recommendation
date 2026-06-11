"""
=============================================================
SCRIPT TEST API - FOOD RECOMMENDATION
=============================================================
Chạy server trước:
  py -3 -m src.api --host 127.0.0.1 --port 8000 --recipe-file "result/data_monan_day_du_CP.json"

Rồi chạy script này:
  py -3 scripts/test_api.py
=============================================================
"""
import sys, json
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import urllib.request
    import urllib.error
except ImportError:
    print("Cần urllib (built-in)")
    sys.exit(1)

BASE_URL = "http://127.0.0.1:8000"

GREEN = "\033[92m"
RED   = "\033[91m"
CYAN  = "\033[96m"
BOLD  = "\033[1m"
RESET = "\033[0m"


def call(method: str, path: str, body: dict | None = None) -> dict:
    url = BASE_URL + path
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json; charset=utf-8"} if data else {}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8"))


def section(title: str):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")


# ─────────────────────────────────────────────
# TEST 1: Health Check
# ─────────────────────────────────────────────
section("TEST 1 — GET /health")
resp = call("GET", "/health")
if resp.get("ok"):
    print(f"  {GREEN}✓ PASS{RESET} service = {resp['service']}")
    print(f"       recipe_file = {resp['recipe_file']}")
else:
    print(f"  {RED}✗ FAIL{RESET} {resp}")
    print(f"\n{RED}Server chưa chạy! Hãy start server trước.{RESET}")
    sys.exit(1)


# ─────────────────────────────────────────────
# TEST 2: Recommend với kho cơ bản
# ─────────────────────────────────────────────
section("TEST 2 — POST /recommend (kho cơ bản)")
payload = {
    "ingredients": [
        {"name": "Thịt bò",    "quantity": "300 g"},
        {"name": "Tôm",        "quantity": "300 g"},
        {"name": "Trứng gà",   "quantity": "2 quả"},
        {"name": "Cà chua",    "quantity": "3 quả"},
        {"name": "Bắp cải",    "quantity": "200 g"},
        {"name": "Khoai tây",  "quantity": "2 củ"},
        {"name": "Nấm hương",  "quantity": "50 g"},
        {"name": "Thịt ức gà", "quantity": "300 g"},
    ],
    "top_k": 5,
    "max_dishes": 2
}
resp = call("POST", "/recommend", payload)
if resp.get("ok"):
    print(f"  {GREEN}✓ PASS{RESET}  input_count = {resp['input_count']}")
    print(f"\n  TOP DISHES:")
    for i, d in enumerate(resp.get("top_dishes", []), 1):
        print(f"  {i}. {d['dish_name'][:50]:<50} score={d['score']:.4f}  thiếu={d['missing_required']}")
    print(f"\n  MEAL SET:")
    for d in resp.get("meal_set", []):
        print(f"  → {d['dish_name'][:50]:<50} type={d.get('dish_type','?')}")
else:
    print(f"  {RED}✗ FAIL{RESET} {resp.get('error','?')}")


# ─────────────────────────────────────────────
# TEST 3: Recommend lọc theo thời gian ≤ 20 phút
# ─────────────────────────────────────────────
section("TEST 3 — POST /recommend?max_minutes=20")
payload["max_minutes"] = 20
payload["top_k"] = 3
resp = call("POST", "/recommend", payload)
if resp.get("ok"):
    dishes = resp.get("top_dishes", [])
    print(f"  {GREEN}✓ PASS{RESET}  Tìm được {len(dishes)} món ≤ 20 phút:")
    for d in dishes:
        print(f"    → {d['dish_name']}")
else:
    print(f"  {RED}✗ FAIL{RESET} {resp.get('error','?')}")


# ─────────────────────────────────────────────
# TEST 4: Recommend theo dạng mảng tên đơn giản
# ─────────────────────────────────────────────
section("TEST 4 — POST /recommend (dạng list string)")
payload_simple = ["thịt bò", "tôm", "cà chua", "trứng gà"]
resp = call("POST", "/recommend", payload_simple)
if resp.get("ok"):
    print(f"  {GREEN}✓ PASS{RESET}  input_count = {resp['input_count']}")
    for d in resp.get("top_dishes", [])[:3]:
        print(f"    → {d['dish_name']}")
else:
    print(f"  {RED}✗ FAIL{RESET} {resp.get('error','?')}")


# ─────────────────────────────────────────────
# TEST 5: Endpoint không tồn tại (404)
# ─────────────────────────────────────────────
section("TEST 5 — GET /invalid (expect 404)")
resp = call("GET", "/invalid")
if not resp.get("ok") and "khong ton tai" in str(resp.get("error","")).lower():
    print(f"  {GREEN}✓ PASS{RESET}  404 trả về đúng: {resp['error']}")
else:
    print(f"  {RED}✗ FAIL{RESET}  {resp}")


# ─────────────────────────────────────────────
# TEST 6: Body rỗng (expect lỗi validation)
# ─────────────────────────────────────────────
section("TEST 6 — POST /recommend (body rỗng)")
resp = call("POST", "/recommend", {})
if not resp.get("ok"):
    print(f"  {GREEN}✓ PASS{RESET}  Lỗi validation đúng: {resp.get('error','')}")
else:
    print(f"  {RED}✗ FAIL{RESET}  Nên trả lỗi nhưng lại ok")


print(f"\n{BOLD}{'='*60}")
print("  HOÀN TẤT TEST API")
print(f"{'='*60}{RESET}\n")
