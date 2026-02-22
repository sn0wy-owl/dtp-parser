from pathlib import Path

years = range(2016, 2026)
months = range(1, 13)
BASE_URL = 'http://стат.гибдд.рф/opendataapi/v1/kartdtp/rows?'
output_path = Path('data/all_accidents.parquet')