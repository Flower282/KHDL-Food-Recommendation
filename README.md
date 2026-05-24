# 🍜 Food Recommendation System - Hệ Thống Gợi Ý Món Ăn

**Vietnamese Recipe Recommendation Engine with Knowledge Graph**

Hệ thống gợi ý các bộ món ăn dựa trên kho tài nguyên (stock) hiện có, sử dụng Knowledge Graph để xây dựng mối quan hệ giữa các món ăn, nguyên liệu và loại món.

### 📖 Kiến Trúc & Chi Tiết

**👉 Để hiểu về kiến trúc project, ontology, các module chính:** 
[**Xem file ARCHITECTURE.html**](ARCHITECTURE.html) (mở trong trình duyệt)

File này chứa:
- 📐 Kiến trúc tổng thể (5 phases)
- 📁 Cấu trúc thư mục chi tiết
- 🔹 Knowledge Graph Ontology (5 node types, 4 relationships)
- 🛠️ Mô tả các module chính
- 📋 Tổng hợp lệnh (new + legacy)

---

## 📋 Yêu Cầu

- **Python 3.10+**
- **Thư viện phụ thuộc**: Xem [requirements.txt](requirements.txt)

### Cài Đặt Dependencies

```bash
pip install -r requirements.txt
```

---

## 🚀 Khởi Động Nhanh

### 1. Cấu Hình (Optional)

Project sử dụng cấu hình mặc định cho Neo4j (local). Nếu cần thay đổi:

```bash
# Copy file cấu hình mẫu (nếu cần)
# cp .env.example .env
```

Các thông số cấu hình nằm trong [src/config.py](src/config.py):
- `NEO4J_URI`: Connection URI (default: `bolt://localhost:7687`)
- `NEO4J_USER`: Username (default: `neo4j`)
- `NEO4J_PASSWORD`: Password (default: `password`)

### 2. Kiểm Tra Trạng Thái Pipeline

```bash
# Xem các file đã xử lý và trạng thái
python -m src status

# Hoặc dùng standalone script
python scripts/status.py
```

Kết quả sẽ hiển thị:
- ✅/❌ Raw CSV đã tải
- ✅/❌ Recipes đã normalize
- ✅/❌ KG payload đã build
- ✅/❌ Recommendations đã tạo

### 3. Chạy Pipeline

#### a) Chỉ Normalize Recipes (CSV → JSON)

```bash
python scripts/normalize.py
```

Xử lý: `result/raw_data_CP.csv` → `result/recipes_processed.json`

#### b) Build Knowledge Graph

```bash
python scripts/build_kg.py
```

Tạo:
- `result/kg_payload.json` - KG structure
- `result/load_kg.cypher` - Cypher commands

#### c) Tạo Gợi Ý Món Ăn

```bash
python scripts/recommend.py --top-k 10 --max-dishes 3
```

Tùy chọn:
- `--top-k N` - Số món ăn xem xét (default: 10)
- `--max-dishes N` - Số món trong bộ gợi ý (default: 3)

#### d) Full Pipeline

```bash
python scripts/pipeline.py --normalize --build-kg --recommend
```

Hoặc chạy tất cả các bước:

```bash
python scripts/pipeline.py
```

### 4. Load vào Neo4j (Optional)

Nếu có Neo4j instance chạy:

```bash
python scripts/pipeline.py --load-neo4j --neo4j-password YOUR_PASSWORD --clear
```

## 💡 Ví Dụ Sử Dụng

### Ví dụ 1: Kiểm tra xem đã normalize chưa

```bash
python -m src status
```

### Ví dụ 2: Normalize + Recommendation

```bash
python scripts/pipeline.py --normalize --recommend --max-dishes 5
```

### Ví dụ 3: Chỉ build KG

```bash
python scripts/build_kg.py
```

### Ví dụ 4: Recommendation với thông số tùy chỉnh

```bash
python scripts/recommend.py --top-k 20 --max-dishes 4
```

---

## 🧪 Kiểm Tra Kết Quả

### Xem Recommendations

```bash
cat result/recommendation_kg.json | python -m json.tool
```

### Xem KG Stats

```bash
python scripts/build_kg.py  # Hiển thị số lượng dishes, ingredients
```

---

## 🐛 Troubleshooting

### Q: Lỗi "recipes_processed.json not found"
**A:** Chạy normalize trước:
```bash
python scripts/normalize.py
```

### Q: Lỗi kết nối Neo4j
**A:** Kiểm tra cấu hình trong `src/config.py` và đảm bảo Neo4j đang chạy

### Q: Muốn xem chi tiết kiến trúc?
**A:** Mở file [ARCHITECTURE.html](ARCHITECTURE.html) trong browser

---

## 📝 Các Lệnh Thường Dùng

```bash
# Kiểm tra trạng thái
python -m src status

# Normalize recipes
python scripts/normalize.py

# Build KG
python scripts/build_kg.py

# Tạo gợi ý (mặc định 3 bộ, top-10)
python scripts/recommend.py

# Tạo gợi ý (5 bộ, top-20)
python scripts/recommend.py --top-k 20 --max-dishes 5

# Full pipeline: normalize → build → recommend
python scripts/pipeline.py --normalize --build-kg --recommend

# Full pipeline with Neo4j
python scripts/pipeline.py --normalize --build-kg --load-neo4j --recommend \
    --neo4j-password YOUR_PASSWORD
```

---

**Last Updated:** May 24, 2026  
**Version:** 1.0.0  
**Status:** Production Ready
