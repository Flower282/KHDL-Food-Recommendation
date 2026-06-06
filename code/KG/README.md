# Knowledge Graph cho Goi Y Mon An

Thu muc nay trien khai day du pipeline theo 4 buoc:

1. Thiet ke ontology (Dish, Ingredient, StockItem, Difficulty).
2. Tien xu ly JSON thanh payload va Cypher.
3. Nap du lieu vao Neo4j.
4. Goi y mon an theo do phu nguyen lieu va chon nhieu mon cung luc.

## Cau truc file

- `config.py`: duong dan mac dinh va config Neo4j.
- `ontology.py`: dinh nghia ontology va schema Cypher.
- `preprocess.py`: chuan hoa ten nguyen lieu, tach khoi luong, do tuong dong.
- `neo4j_pipeline.py`: build payload, tao Cypher, nap du lieu Neo4j.
- `recommender.py`: tinh diem mon an va chon meal set nhieu mon.
- `run_pipeline.py`: CLI de chay toan bo quy trinh.

## Cai dat

```bash
pip install neo4j
```

## Cap nhat KG va nap Neo4j

### Phuong an 1: Khoi tao KG lan dau (hoac xay lai tu dau)

Dung cho lan dau chay hoac khi muon dong bo lai toan bo tu file JSON nguon:

1) Xuat payload va Cypher tu file JSON cong thuc:
```bash
python code/KG/run_pipeline.py --recipe-file result/data_monan_day_du_CP.json export
```

2) Nap vao Neo4j (co the dung `--clear` de xoa sach du lieu cu tren graph truoc khi nap):
```bash
# Neo4j local
python code/KG/run_pipeline.py load-neo4j --password YOUR_PASSWORD --clear

# Neo4j Aura (online)
python code/KG/run_pipeline.py load-neo4j --uri neo4j+s://YOUR_INSTANCE.databases.neo4j.io --user YOUR_USER --password YOUR_PASSWORD --database neo4j --clear
```

### Phuong an 2: Cap nhat/Them moi gia tang (Incremental Merge)

Dung khi co file recipe JSON moi can nap vao ma khong muon hop nhat file JSON thu cong hay re-build lai toan bo KG. Tu dong so khop do tuong dong ten mon an de gop/them moi:

1) Run merge de tao payload con va hop nhat vao payload chinh (`kg_payload.json`):
```bash
# He thong se hoi duong dan file JSON moi neu khong truyen tham so
python code/KG/run_pipeline.py merge

# Hoac truyen truc tiep qua CLI:
python code/KG/run_pipeline.py merge --new-recipe-file result/your_new_recipes.json
```

2) Dong bo du lieu moi len Neo4j (KHONG dung `--clear` de giu lai cac mon cu):
```bash
python code/KG/run_pipeline.py load-neo4j --password YOUR_PASSWORD
```

Chay goi y (1 mon va nhieu mon):

```bash
python code/KG/run_pipeline.py recommend --top-k 10 --max-dishes 3
```

Mo giao dien test nhanh:

```bash
python code/KG/gui_test.py
```

Trong giao dien co the chon so mon, thoi gian toi da, va nhom loai mon. Neu bo chon "Khong loc theo loai mon" thi co the tick nhieu loai va he thong se co gang goi y it nhat 1 mon cho moi loai da chon.

Ket qua mac dinh duoc ghi vao `result/recommendation_kg.json`.
