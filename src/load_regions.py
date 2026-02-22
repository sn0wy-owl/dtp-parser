import requests
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    reraise=True
)
def load_regions() -> pd.DataFrame:
    '''
    Получает справочник регионов с сайта ГИБДД
    '''
    regions_url = 'http://стат.гибдд.рф/opendataapi/v1/dictionary/rows?code=1'

    response = requests.get(regions_url)
    response.raise_for_status()

    responce_json = response.json()
    regions = pd.DataFrame(responce_json['results'][0]['dict_rows'])[['rows_code', 'rows_name']]
    regions.rename(columns={'rows_code': 'code', 'rows_name': 'region_name'}, inplace=True)
    
    return regions


if __name__ == '__main__':
    load_regions()
    