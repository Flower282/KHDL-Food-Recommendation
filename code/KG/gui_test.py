from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    current_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(current_dir.parent))

    from KG.config import DEFAULT_RECIPE_FILE, DEFAULT_STOCK_FILE  # type: ignore
    from KG.preprocess import load_json_array  # type: ignore
    from KG.recommender import load_and_recommend  # type: ignore
else:
    from .config import DEFAULT_RECIPE_FILE, DEFAULT_STOCK_FILE
    from .preprocess import load_json_array
    from .recommender import load_and_recommend


TYPE_OPTIONS = [
    ("Mặn", "mon man"),
    ("Canh", "canh"),
    ("Rau", "rau"),
    ("Chay", "chay"),
]


class RecipeKGApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Knowledge Graph - Gợi ý món ăn")
        self.root.geometry("1220x780")
        self.root.minsize(1100, 700)

        self.recipe_path = str(DEFAULT_RECIPE_FILE)
        self.stock_path = str(DEFAULT_STOCK_FILE)

        self.type_vars: dict[str, tk.BooleanVar] = {}
        self._build_style()
        self._build_ui()
        self._load_preview_counts()

    def _build_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background="#f6f2ea")
        style.configure("Header.TFrame", background="#1f2937")
        style.configure("Header.TLabel", background="#1f2937", foreground="#f8fafc", font=("Segoe UI", 15, "bold"))
        style.configure("SubHeader.TLabel", background="#1f2937", foreground="#cbd5e1", font=("Segoe UI", 9))
        style.configure("Section.TLabelframe", background="#f6f2ea", padding=10)
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("TButton", padding=6)
        style.configure("Result.Treeview", rowheight=26, font=("Segoe UI", 9))
        style.configure("Result.Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, style="App.TFrame")
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(container, style="Header.TFrame", padding=(18, 14))
        header.pack(fill=tk.X)
        ttk.Label(header, text="Gợi ý món ăn từ Knowledge Graph", style="Header.TLabel").pack(anchor=tk.W)
        ttk.Label(
            header,
            text="Chọn điều kiện, bấm Tìm gợi ý để xem top món phù hợp và tổ hợp nhiều món cùng lúc.",
            style="SubHeader.TLabel",
        ).pack(anchor=tk.W, pady=(4, 0))

        body = ttk.Frame(container, style="App.TFrame", padding=14)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        control_box = ttk.Labelframe(body, text="Điều kiện tìm kiếm", style="Section.TLabelframe")
        control_box.grid(row=0, column=0, sticky="nsw", padx=(0, 12), pady=0)

        result_box = ttk.Frame(body, style="App.TFrame")
        result_box.grid(row=0, column=1, sticky="nsew")
        result_box.columnconfigure(0, weight=1)
        result_box.rowconfigure(1, weight=1)
        result_box.rowconfigure(3, weight=1)

        self._build_controls(control_box)
        self._build_results(result_box)

    def _build_controls(self, parent: ttk.Labelframe) -> None:
        parent.columnconfigure(0, weight=1)

        ttk.Label(parent, text="Số món gợi ý cùng lúc:").grid(row=0, column=0, sticky=tk.W, pady=(0, 4))
        self.max_dishes_var = tk.StringVar(value="3")
        ttk.Entry(parent, textvariable=self.max_dishes_var, width=20).grid(row=1, column=0, sticky=tk.W, pady=(0, 10))

        ttk.Label(parent, text="Top kết quả hiển thị:").grid(row=2, column=0, sticky=tk.W, pady=(0, 4))
        self.top_k_var = tk.StringVar(value="10")
        ttk.Entry(parent, textvariable=self.top_k_var, width=20).grid(row=3, column=0, sticky=tk.W, pady=(0, 10))

        ttk.Label(parent, text="Thời gian tối đa (phút):").grid(row=4, column=0, sticky=tk.W, pady=(0, 4))
        self.max_minutes_var = tk.StringVar(value="")
        ttk.Entry(parent, textvariable=self.max_minutes_var, width=20).grid(row=5, column=0, sticky=tk.W, pady=(0, 12))

        type_frame = ttk.Labelframe(parent, text="Loại món", style="Section.TLabelframe")
        type_frame.grid(row=6, column=0, sticky=tk.EW, pady=(0, 10))
        type_frame.columnconfigure(0, weight=1)

        self.ignore_type_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            type_frame,
            text="Không lọc theo loại món",
            variable=self.ignore_type_var,
            command=self._toggle_type_checks,
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 6))

        for index, (label, value) in enumerate(TYPE_OPTIONS, start=1):
            var = tk.BooleanVar(value=False)
            self.type_vars[value] = var
            ttk.Checkbutton(type_frame, text=label, variable=var).grid(row=index, column=0, sticky=tk.W)

        ttk.Button(parent, text="Tìm gợi ý", command=self.on_search).grid(row=7, column=0, sticky=tk.EW, pady=(12, 6))
        ttk.Button(parent, text="Xóa kết quả", command=self.clear_results).grid(row=8, column=0, sticky=tk.EW)

        self.info_label = ttk.Label(parent, text="")
        self.info_label.grid(row=9, column=0, sticky=tk.W, pady=(12, 0))

    def _build_results(self, parent: ttk.Frame) -> None:
        top_title = ttk.Label(parent, text="Top món thỏa điều kiện", font=("Segoe UI", 11, "bold"))
        top_title.grid(row=0, column=0, sticky=tk.W, pady=(0, 6))

        top_frame = ttk.Frame(parent)
        top_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        top_frame.columnconfigure(0, weight=1)
        top_frame.rowconfigure(0, weight=1)

        self.top_tree = self._create_treeview(
            top_frame,
            ["Món ăn", "Điểm", "Loại", "Thiếu NL chính", "Type filter"],
            [260, 80, 120, 110, 130],
        )
        self.top_tree.grid(row=0, column=0, sticky="nsew")

        meal_title = ttk.Label(parent, text="Tổ hợp món được chọn", font=("Segoe UI", 11, "bold"))
        meal_title.grid(row=2, column=0, sticky=tk.W, pady=(0, 6))

        meal_frame = ttk.Frame(parent)
        meal_frame.grid(row=3, column=0, sticky="nsew")
        meal_frame.columnconfigure(0, weight=1)
        meal_frame.rowconfigure(0, weight=1)

        self.meal_tree = self._create_treeview(
            meal_frame,
            ["Món ăn", "Điểm", "Loại", "Thiếu NL chính", "Type filter"],
            [260, 80, 120, 110, 130],
        )
        self.meal_tree.grid(row=0, column=0, sticky="nsew")

    def _create_treeview(self, parent: ttk.Frame, columns: list[str], widths: list[int]) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=columns, show="headings", style="Result.Treeview")
        for column_name, width in zip(columns, widths):
            tree.heading(column_name, text=column_name)
            tree.column(column_name, width=width, anchor=tk.W, stretch=True)

        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        return tree

    def _toggle_type_checks(self) -> None:
        if self.ignore_type_var.get():
            for var in self.type_vars.values():
                var.set(False)

    def _load_preview_counts(self) -> None:
        try:
            recipes = load_json_array(self.recipe_path)
            stocks = load_json_array(self.stock_path)
            self.info_label.configure(text=f"Đã nạp {len(recipes)} món ăn và {len(stocks)} nguyên liệu kho.")
        except Exception as exc:
            self.info_label.configure(text=f"Không thể đọc dữ liệu: {exc}")

    def _parse_int(self, value: str, field_name: str, allow_empty: bool = False) -> int | None:
        text = value.strip()
        if not text:
            if allow_empty:
                return None
            raise ValueError(f"Vui lòng nhập {field_name}.")

        try:
            parsed = int(text)
        except ValueError as exc:
            raise ValueError(f"{field_name} phải là số nguyên.") from exc

        if parsed <= 0:
            raise ValueError(f"{field_name} phải lớn hơn 0.")

        return parsed

    def _selected_types(self) -> list[str]:
        if self.ignore_type_var.get():
            return []
        return [value for value, var in self.type_vars.items() if var.get()]

    def clear_results(self) -> None:
        for tree in (self.top_tree, self.meal_tree):
            for item in tree.get_children():
                tree.delete(item)

    def on_search(self) -> None:
        try:
            top_k = self._parse_int(self.top_k_var.get(), "top kết quả")
            max_dishes = self._parse_int(self.max_dishes_var.get(), "số món gợi ý")
            max_minutes = self._parse_int(self.max_minutes_var.get(), "thời gian tối đa", allow_empty=True)
            selected_types = self._selected_types()

            if selected_types and max_dishes is not None and len(selected_types) > max_dishes:
                messagebox.showwarning(
                    "Không hợp lệ",
                    "Số món gợi ý phải lớn hơn hoặc bằng số loại món đã chọn để đảm bảo mỗi loại có ít nhất 1 món.",
                )
                return

            result = load_and_recommend(
                recipe_path=self.recipe_path,
                stock_path=self.stock_path,
                top_k=top_k,
                max_dishes=max_dishes,
                required_types=selected_types,
                max_minutes=max_minutes,
            )

            self._render_top_dishes(result.get("top_dishes", []))
            self._render_meal_set(result.get("meal_set", []))

            if selected_types and not result.get("meal_set"):
                self.info_label.configure(text="Không tìm được tổ hợp thỏa mãn điều kiện loại món và thời gian.")
            else:
                self.info_label.configure(text=f"Đã hiển thị {len(result.get('top_dishes', []))} món top và {len(result.get('meal_set', []))} món trong tổ hợp.")
        except Exception as exc:
            messagebox.showerror("Lỗi", str(exc))

    def _render_top_dishes(self, rows: list[dict[str, Any]]) -> None:
        for item in self.top_tree.get_children():
            self.top_tree.delete(item)

        for row in rows:
            self.top_tree.insert(
                "",
                tk.END,
                values=(
                    row.get("dish_name", ""),
                    row.get("score", ""),
                    row.get("dish_type", "null"),
                    row.get("missing_required", ""),
                    row.get("dish_type_filter", ""),
                ),
            )

    def _render_meal_set(self, rows: list[dict[str, Any]]) -> None:
        for item in self.meal_tree.get_children():
            self.meal_tree.delete(item)

        for row in rows:
            self.meal_tree.insert(
                "",
                tk.END,
                values=(
                    row.get("dish_name", ""),
                    row.get("score", ""),
                    row.get("dish_type", "null"),
                    row.get("missing_required", ""),
                    row.get("dish_type_filter", ""),
                ),
            )


def main() -> None:
    root = tk.Tk()
    app = RecipeKGApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
