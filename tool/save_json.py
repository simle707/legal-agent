import json
from parse_law import articles
from pathlib import Path

BASE_PATH = Path(__file__).parent

with open(f'{BASE_PATH}/docs/labor_contract_law.json', 'w', encoding='utf-8') as f:
    json.dump(articles, f, ensure_ascii=False, indent=2)

print('已保存', len(articles), '条')