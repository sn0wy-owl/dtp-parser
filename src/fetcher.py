import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import BASE_URL

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    reraise=True
)
def fetch_data(year: int, month: int, code: int) -> dict:
    '''
    Загрузка данных с сайта ГИБДД и чтение json ответа
    '''
    params = {
        'dat': f'{month}.{year}',
        'reg': code,
        'pok': '1'
    }
    
    response = requests.get(BASE_URL, params, timeout=30)
    response.raise_for_status()        
    response_json = response.json()

    return response_json
