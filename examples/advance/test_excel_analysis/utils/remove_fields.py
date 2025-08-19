import json
import os

json_path = "examples/advance/test_excel_analysis/test_excel.json"

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for item in data:
    for key in ["constraints", "format", "level", "status"]:
        item.pop(key, None)

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Fields removed successfully.")
