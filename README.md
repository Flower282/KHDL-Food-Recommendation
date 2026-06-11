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

## � Chuẩn Bị Dữ Liệu

### Bước 1: Xử Lý Dữ Liệu Thô (Data Processing)

Trước tiên, bạn cần xử lý các file CSV thô bằng script `process_recipes_csv.py`:

```bash
# Xử lý một file CSV
python scripts/process_recipes_csv.py <input_file.csv>

# Hoặc xử lý file cụ thể
python scripts/process_recipes_csv.py rawCSV/raw_data.csv
```

Script này sẽ:
- 🧹 Làm sạch và chuẩn hóa dữ liệu
- ✅ Xoá các hàng không hợp lệ
- 📊 Tạo output file đã xử lý

### Bước 2: Di Chuyển File vào Folder rawCSV

Sau khi xử lý dữ liệu, **di chuyển các file CSV đã xử lý** vào thư mục `rawCSV/`:

```bash
# Tạo thư mục nếu chưa tồn tại
mkdir -p rawCSV

# Di chuyển file đã xử lý (ví dụ)
mv path/to/processed_file.csv rawCSV/

# Hoặc di chuyển nhiều file
mv path/to/processed/*.csv rawCSV/
```

**Lưu ý:**
- ⚠️ **Chỉ đưa các file CSV đã được xử lý bởi `process_recipes_csv.py` vào folder `rawCSV/`**
- 📁 Folder `rawCSV/` sẽ chứa các file nguồn cho pipeline normalize
- 🔄 File đầu vào phải có cấu trúc cột hợp lệ (xem examples)

### Bước 3: Normalize Recipes (CSV → JSON)

Khi đã có file trong `rawCSV/`, chạy script normalize để xử lý batch:

```bash
# Chế độ batch (xử lý tất cả CSV files)
python scripts/normalize.py --batch

# Hoặc chế độ interactive (chọn file)
python scripts/normalize.py

# Chỉ định file riêng
python scripts/normalize.py -i rawCSV/recipes.csv -o normalized/recipes.json
```

Output sẽ được lưu vào thư mục `normalized/` với tên: `<input_name>.json`

---

## �🚀 Khởi Động Nhanh

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

#### a) Normalize Recipes (CSV → JSON)

Sau khi di chuyển file CSV đã xử lý vào folder `rawCSV/`, bạn có thể normalize batch:

```bash
# Batch mode - xử lý tất cả CSV files từ rawCSV/
python scripts/normalize.py --batch

# Interactive mode - chọn file cụ thể
python scripts/normalize.py

# Chỉ định file input riêng
python scripts/normalize.py -i rawCSV/recipes.csv
```

Output: `normalized/` folder chứa các file `.json` tương ứng

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

## 📁 Cấu Trúc Thư Mục & Dòng Chảy Dữ Liệu

```
📦 KHDL-Food-Recommendation/
├── 📂 rawCSV/                    ← Di chuyển CSV đã xử lý vào đây
│   ├── raw_data_CP.csv
│   ├── raw_data_DMX.csv
│   └── ...
├── 📂 normalized/                ← Output của normalize.py
│   ├── raw_data_CP.json
│   ├── raw_data_DMX.json
│   └── ...
├── 📂 result/                    ← Output của build_kg & recommend
│   ├── recipes_processed.json
│   ├── kg_payload.json
│   ├── load_kg.cypher
│   └── recommendation_kg.json
├── 📂 data/
│   └── Kho.json                  ← Stock data
├── scripts/
│   ├── normalize.py              ← Chạy này sau khi có rawCSV
│   ├── build_kg.py
│   ├── recommend.py
│   └── ...
└── src/
    ├── config.py
    ├── pipeline.py
    └── ...
```

**Dòng chảy dữ liệu:**
```
Raw Data
   ↓
[process_recipes_csv.py] ← Xử lý thô
   ↓
📁 rawCSV/ (CSV files)
   ↓
[scripts/normalize.py] ← Batch normalize
   ↓
📁 normalized/ (JSON files)
   ↓
[scripts/build_kg.py] ← Build Knowledge Graph
   ↓
📁 result/ (KG payload + Cypher)
   ↓
[scripts/recommend.py] ← Generate recommendations
   ↓
📁 result/recommendation_kg.json ✅
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

## � Format Dữ Liệu Đầu Vào

### Format CSV cần có:

Các file CSV trong `rawCSV/` **phải có** các cột sau (tiếng Việt):

| Cột | Bắt buộc | Ví dụ |
|-----|---------|------|
| `tên` | ✅ | Cơm rang dưa bò |
| `thời gian` | ✅ | 30 phút |
| `số người` | ✅ | 4 người |
| `độ khó` | ✅ | dễ / trung bình / khó |
| `nguyên liệu` | ✅ | Cơm 500g \| Thịt bò 300g \| ... |
| `cách chế biến` | ❌ | (Optional) |
| `link` | ❌ | (Optional) |

### Yêu cầu chi tiết:

- **`tên`**: Tên món ăn (không được rỗng)
- **`nguyên liệu`**: Danh sách nguyên liệu cách nhau bằng ` | ` (pipe)
  - Ví dụ: `Gạo 500g | Thịt bò 300g | Cà rốt 100g`
  - Mỗi nguyên liệu nên có tên + khối lượng (nếu có)
- **`thời gian`**: Có thể có số phút hoặc text (ví dụ: `30 phút`, `1h30`)
- **`độ khó`**: `dễ`, `trung bình`, `khó`

### Xử lý file trước khi đưa vào:

```bash
# 1. Xử lý file CSV thô
python scripts/process_recipes_csv.py raw_input.csv

# 2. Di chuyển file đã xử lý
mv raw_input.csv rawCSV/

# 3. Chạy normalize
python scripts/normalize.py --batch
```

---

### Q: File CSV không được nhận diện trong rawCSV/
**A:** Đảm bảo file:
- ✅ Đã được xử lý bằng `process_recipes_csv.py`
- ✅ Có cấu trúc cột hợp lệ: `tên`, `thời gian`, `số người`, `độ khó`, `nguyên liệu`
- ✅ Có đuôi `.csv`

### Q: Lỗi "nguyên liệu" không hợp lệ
**A:** File CSV cần có:
- Tên cột tiếng Việt chính xác
- Hoặc chạy `process_recipes_csv.py` để chuẩn hóa trước

### Q: Lỗi "recipes_processed.json not found"
**A:** Bạn cần normalize trước:
```bash
# 1. Đưa file CSV vào rawCSV/
mv file.csv rawCSV/

# 2. Chạy normalize
python scripts/normalize.py --batch
```

### Q: Lỗi kết nối Neo4j
**A:** Kiểm tra cấu hình trong `src/config.py` và đảm bảo Neo4j đang chạy

### Q: Muốn xem chi tiết kiến trúc?
**A:** Mở file [ARCHITECTURE.html](ARCHITECTURE.html) trong browser

### Q: Folder rawCSV/ chưa tồn tại?
**A:** Tạo folder:
```bash
mkdir -p rawCSV
```

---

## 📝 Các Lệnh Thường Dùng

```bash
# === CHUẨN BỊ DỮ LIỆU ===
# Xử lý file CSV thô (bằng process_recipes_csv.py)
python scripts/process_recipes_csv.py input.csv

# Di chuyển file đã xử lý vào rawCSV
mv processed_file.csv rawCSV/

# === NORMALIZE (CSV → JSON) ===
# Batch mode - tất cả files
python scripts/normalize.py --batch

# Interactive mode - chọn file
python scripts/normalize.py

# Chỉ định file input
python scripts/normalize.py -i rawCSV/recipes.csv

# === KIẾN THỨC ĐỒ THỊ ===
# Kiểm tra trạng thái pipeline
python -m src status

# Build Knowledge Graph
python scripts/build_kg.py

# === GỢI Ý ===
# Tạo gợi ý (mặc định 3 bộ, top-10)
python scripts/recommend.py

# Tạo gợi ý tùy chỉnh
python scripts/recommend.py --top-k 20 --max-dishes 5

# === FULL PIPELINE ===
# Normalize → Build KG → Recommend
python scripts/pipeline.py --normalize --build-kg --recommend

# Load vào Neo4j
python scripts/pipeline.py --normalize --build-kg --load-neo4j --recommend \
    --neo4j-password YOUR_PASSWORD
```

---

<<<<<<< HEAD
=======
## HTTP API: Gợi ý món ăn từ JSON nguyên liệu

Chạy API không cần cài thêm framework web:

```bash
py -m src.api --host 127.0.0.1 --port 8000
```

Gọi endpoint:

```bash
curl -X POST http://127.0.0.1:8000/recommend ^
  -H "Content-Type: application/json" ^
  -d "{\"ingredients\":[{\"name\":\"Thịt bò\",\"quantity\":\"300 g\"},{\"name\":\"Cà chua\",\"quantity\":\"3 quả\"},{\"name\":\"Trứng gà\",\"quantity\":\"2 quả\"}],\"top_k\":5,\"max_dishes\":2}"
```

Body có thể dùng key tiếng Anh (`name`, `quantity`) hoặc tiếng Việt (`tên`, `khối lượng`). API trả về `top_dishes` và `meal_set`.

---

>>>>>>> ba34e0891da923704e0e35fe0b8243790d96d12e
**Last Updated:** June 3, 2026  
**Version:** 1.1.0 - Enhanced data pipeline with rawCSV folder support  
**Status:** Production Ready

### Thay Đổi Gần Đây (v1.1.0):
- ✨ Thêm hỗ trợ batch processing từ folder `rawCSV/`
- 📁 Normalize script tự động scan và convert CSV → JSON
- 🔄 Hỗ trợ xử lý multiple files cùng lúc
- 📝 Cập nhật documentation đầy đủ về data pipeline
