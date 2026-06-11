"""Verify fixes before reloading Neo4j."""
import sys, os
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from code.KG.neo4j_pipeline import _parse_minutes, build_kg_payload

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("=== Kiểm tra _parse_minutes ===")
samples = ['15 phut', '30 phut', '40 phut', None, '1 gio', '', '25']
for s in samples:
    print(f"  parse_minutes({s!r}) = {_parse_minutes(s)}")

print("\n=== Kiểm tra build_kg_payload ===")
payload = build_kg_payload(
    os.path.join(PROJECT_ROOT, 'result', 'data_monan_day_du_CP.json'),
    os.path.join(PROJECT_ROOT, 'data', 'Kho.json'),
)

dishes_with_time = [d for d in payload['dish_rows'] if d['time_minutes'] is not None]
dishes_without_time = [d for d in payload['dish_rows'] if d['time_minutes'] is None]
print(f"Dishes with time_minutes   : {len(dishes_with_time)}")
print(f"Dishes without time_minutes: {len(dishes_without_time)}")
if dishes_without_time:
    print("  (Mẫu không có time):", [d['name'] for d in dishes_without_time[:3]])

print("\n=== Stock mapping (tất cả, sắp xếp theo score) ===")
mappings = sorted(payload['stock_mapping_rows'], key=lambda x: x['name_score'], reverse=True)
ok, bad = 0, 0
for m in mappings:
    status = "✓" if m['name_score'] >= 0.5 else "✗"
    if m['name_score'] >= 0.5:
        ok += 1
    else:
        bad += 1
    print(f"  {status} {m['stock_name']:<28} -> {m['ingredient_canonical']:<28} score={m['name_score']:.3f}")

print(f"\nKết quả: {ok} mapping tốt (>=0.5), {bad} mapping yếu (<0.5)")
