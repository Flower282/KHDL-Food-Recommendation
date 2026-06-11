from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from code.KG.preprocess import load_json_array
from code.KG.recommender import recommend_from_rows
from src.config import Config


DEFAULT_FALLBACK_RECIPE_FILE = Config.result_dir / "data_monan_day_du_CP.json"


def _resolve_recipe_file(recipe_file: str | None = None) -> Path:
    candidates = []
    if recipe_file:
        candidates.append(Path(recipe_file))
    candidates.extend([Path(Config.recipe_file), DEFAULT_FALLBACK_RECIPE_FILE])

    for candidate in candidates:
        if candidate.exists():
            return candidate

    searched = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Khong tim thay file cong thuc. Da thu: {searched}")


def _get_first(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return value
    return None


def _normalize_stock_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict):
        raw_items = (
            payload.get("ingredients")
            or payload.get("nguyen_lieu")
            or payload.get("items")
            or payload.get("stock")
        )
    else:
        raw_items = None

    if not isinstance(raw_items, list):
        raise ValueError("JSON can co field 'ingredients' la mot mang, hoac body la mot mang nguyen lieu.")

    stock_rows: list[dict[str, Any]] = []
    for item in raw_items:
        if isinstance(item, str):
            name = item.strip()
            quantity = None
        elif isinstance(item, dict):
            name = _get_first(item, ["name", "ingredient", "ten", "tên"])
            quantity = _get_first(item, ["quantity", "weight", "amount", "khoi_luong", "khối lượng"])
        else:
            continue

        if name:
            stock_rows.append({"tên": str(name).strip(), "khối lượng": quantity})

    if not stock_rows:
        raise ValueError("Danh sach nguyen lieu rong hoac thieu ten nguyen lieu.")

    return stock_rows


def _int_option(body: dict[str, Any], query: dict[str, list[str]], key: str, default: int) -> int:
    value = body.get(key)
    if value is None and key in query:
        value = query[key][0]
    if value is None:
        return default

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{key}' phai la so nguyen.")

    if parsed <= 0:
        raise ValueError(f"'{key}' phai lon hon 0.")
    return parsed


def _optional_int_option(body: dict[str, Any], query: dict[str, list[str]], key: str) -> int | None:
    value = body.get(key)
    if value is None and key in query:
        value = query[key][0]
    if value in {None, ""}:
        return None

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{key}' phai la so nguyen.")

    if parsed <= 0:
        raise ValueError(f"'{key}' phai lon hon 0.")
    return parsed


def _string_option(body: dict[str, Any], query: dict[str, list[str]], key: str) -> str | None:
    value = body.get(key)
    if value is None and key in query:
        value = query[key][0]
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


def _list_option(body: dict[str, Any], query: dict[str, list[str]], key: str) -> list[str] | None:
    value = body.get(key)
    if value is None and key in query:
        value = query[key]

    if value is None:
        return None
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    raise ValueError(f"'{key}' phai la chuoi hoac mang chuoi.")


def recommend_from_payload(payload: Any, recipe_file: str | Path | None = None) -> dict[str, Any]:
    body = payload if isinstance(payload, dict) else {}
    recipe_path = _resolve_recipe_file(str(recipe_file or body.get("recipe_file") or ""))
    recipe_rows = load_json_array(recipe_path)
    stock_rows = _normalize_stock_rows(payload)

    result = recommend_from_rows(
        recipe_rows=recipe_rows,
        stock_rows=stock_rows,
        top_k=_int_option(body, {}, "top_k", 10),
        max_dishes=_int_option(body, {}, "max_dishes", 3),
        dish_type_filter=_string_option(body, {}, "dish_type_filter"),
        required_types=_list_option(body, {}, "required_types"),
        max_minutes=_optional_int_option(body, {}, "max_minutes"),
    )

    return {
        "ok": True,
        "recipe_file": str(recipe_path),
        "input_count": len(stock_rows),
        **result,
    }


class RecommendationHandler(BaseHTTPRequestHandler):
    recipe_file: Path | None = None

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:
        self._send_json(HTTPStatus.NO_CONTENT, {})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        print(f"Nhan request GET {parsed.path}", flush=True)
        if parsed.path != "/health":
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Endpoint khong ton tai."})
            return

        self._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "service": "food-recommendation-api",
                "recipe_file": str(self.recipe_file),
            },
        )

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        print(f"Nhan request POST {parsed.path}", flush=True)
        if parsed.path != "/recommend":
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Endpoint khong ton tai."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            print(f"Body /recommend: {raw_body[:500]}", flush=True)
            payload = json.loads(raw_body) if raw_body.strip() else {}
            query = parse_qs(parsed.query)

            body = payload if isinstance(payload, dict) else {}
            result = recommend_from_payload_with_query(payload, query, self.recipe_file)
            self._send_json(HTTPStatus.OK, result)
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Body khong phai JSON hop le."})
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
        except FileNotFoundError as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")


def recommend_from_payload_with_query(
    payload: Any,
    query: dict[str, list[str]],
    recipe_file: str | Path | None = None,
) -> dict[str, Any]:
    body = payload if isinstance(payload, dict) else {}
    recipe_path = _resolve_recipe_file(str(recipe_file or body.get("recipe_file") or ""))
    recipe_rows = load_json_array(recipe_path)
    stock_rows = _normalize_stock_rows(payload)

    result = recommend_from_rows(
        recipe_rows=recipe_rows,
        stock_rows=stock_rows,
        top_k=_int_option(body, query, "top_k", 10),
        max_dishes=_int_option(body, query, "max_dishes", 3),
        dish_type_filter=_string_option(body, query, "dish_type_filter"),
        required_types=_list_option(body, query, "required_types"),
        max_minutes=_optional_int_option(body, query, "max_minutes"),
    )

    return {
        "ok": True,
        "recipe_file": str(recipe_path),
        "input_count": len(stock_rows),
        **result,
    }


def run_server(host: str, port: int, recipe_file: str | None = None) -> None:
    RecommendationHandler.recipe_file = _resolve_recipe_file(recipe_file)
    server = ThreadingHTTPServer((host, port), RecommendationHandler)
    print(f"Food recommendation API dang chay tai http://{host}:{port}")
    print("POST /recommend de goi y mon an, GET /health de kiem tra trang thai.")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Food recommendation HTTP API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--recipe-file", default=None)
    args = parser.parse_args()

    run_server(args.host, args.port, args.recipe_file)


if __name__ == "__main__":
    main()
