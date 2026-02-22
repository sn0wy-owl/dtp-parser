import requests

from src.config import BASE_URL

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
