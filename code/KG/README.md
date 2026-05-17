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

1) Xuat payload + cypher (cap nhat KG tu JSON):

```bash
python code/KG/run_pipeline.py export
```

2) Nap vao Neo4j local:

```bash
python code/KG/run_pipeline.py load-neo4j --uri neo4j://127.0.0.1:7687 --user neo4j --password YOUR_PASSWORD --database neo4j
```

3) Nap vao Neo4j Aura (online):

```bash
python code/KG/run_pipeline.py load-neo4j --uri neo4j+s://YOUR_INSTANCE.databases.neo4j.io --user YOUR_USER --password YOUR_PASSWORD --database neo4j
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
