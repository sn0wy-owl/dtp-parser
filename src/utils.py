from pathlib import Path
import logging
from typing import Union
import os
import re
import shutil
from hashlib import sha256

from pyarrow import parquet as pq
import pandas as pd
import numpy as np

import src.config as config


def partition_exists(data_path: Path, year: int, month: int, log: logging.Logger) -> bool:
    """
    Проверяет, существует ли партиция year=..., month=...
    """
    if not data_path:
        return False
    
    try:
        dataset = pq.ParquetDataset(data_path)
        fragments = dataset.fragments
        for fragment in fragments:
            p = str(fragment.path)
            if f'year={year}' in p and f'month={month}' in p:
                return True
            
        return False

    except Exception as e:
        log.error(f'Ошибка при проверка партиции {month:02d}.{year}')
        return False
    

def remove_partition(data_path: Path, year: int, month: int, log: logging.Logger) -> None:
    """
    Удаляет все файлы в партиции year=..., month=...
    """
    year_dir = data_path / f'year={year}'
    if not year_dir:
        return

    for month_dir in year_dir.glob(f'month={month}'):
        if month_dir.is_dir():
            for file in month_dir.iterdir():
                file.unlink()
            month_dir.rmdir()
            log.info(f'Удалена директория: {month_dir}')


def remove_partitioned_data(path: Path, log: logging.Logger) -> None:
    """
    Полностью удаляет директорию с партицированными данными
    """
    if os.path.exists(path):
        shutil.rmtree(path)
        log.warning('Удалены результаты прошлой обработки')
    else:
        log.warning('Данных прошлой обработки необнаружено')


def should_rewrite(year: int, month: int) -> bool:
    if config.rewrite_all is None:
        while True:
            answer = input(
                f'Перезаписать данные за {month:02d}.{year}?\n'
                f'1 - перезаписать\n'
                f'2 - пропустить загрузку\n'
                f'3 - перезаписать (для всех)\n'
                f'4 - пропустить загрузку (для всех)\n'
                'Ответ: '
            )

            if answer == '1':
                return True
            elif answer == '2':
                return False
            elif answer == '3':
                config.rewrite_all = True
                return True
            elif answer == '4':
                config.rewrite_all = False
                return False
            else:
                print('Введите 1, 2, 3 или 4')
    else:
        return config.rewrite_all


def get_health_status(trauma: str) -> str:
    if trauma == '':
        return 'Не указано'

    trauma_lower = trauma.lower()

    if 'скончался' in trauma_lower:
        return 'Скончался'
    elif 'раненый' in trauma_lower:
        return 'Раненый'
    else:
        return 'Не пострадал'
    

def safe_convert_coord(coord_str: str) -> Union[float, None]:
    """
    Безопасное преобразование координат в float
    """
    if pd.isna(coord_str) or coord_str is None:
        return None
    
    # Преобразуем в строку и чистим
    coord_str = str(coord_str).strip()
    
    # Проверка на пустую строку или '.'
    if coord_str == '' or coord_str == '.':
        return None
    
    # Удаляем лишние точки и пробелы
    coord_str = re.sub(r'[^\d.-]', '', coord_str)
    
    # Проверка на корректность
    if not coord_str or coord_str == '.' or coord_str == '-':
        return None
    
    try:
        return float(coord_str)
    except ValueError:
        return None


def create_hash_id(row: dict) -> str:
    '''
    Функция формирует уникальный id для каждой аварии на основе даты, времени и координат
    '''
    hash_components = []

    hash_components.append(str(row['date']) if pd.notna(row['date']) else '')
    hash_components.append(str(row['time']) if pd.notna(row['time']) else '')

    # Для одинаковой длины координат возьмем 4 знака после запятой
    lat = safe_convert_coord(row['lat'])
    lat_rounded = round(lat, 4) if lat else ''
    hash_components.append(str(lat_rounded))

    lng = safe_convert_coord(row['lng'])
    lng_rounded = round(lng, 4) if lng else ''
    hash_components.append(str(lng_rounded))

    hash_string = '|'.join(hash_components)

    # Возьмем только первые 16 символом для читаемости 
    return sha256(hash_string.encode('utf-8')).hexdigest()[:16]


def parse_time(time_str: str) -> Union[str, None]:
    if pd.isna(time_str):
        return None
    
    time_str = str(time_str).strip()
    
    # Проверка разных форматов
    try:
        # Формат ЧЧ:ММ
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) >= 2:
                hour = int(parts[0])
                minute = int(parts[1])
                return f"{hour:02d}:{minute:02d}:00"
    except:
        pass
    
    return None


def clean_single_coord(coord: str, coord_type: str ='lat') -> Union[float, None]:
    if pd.isna(coord):
        return np.nan
    
    # Преобразуем в строку и чистим
    coord_str = str(coord).strip()
    
    # Заменяем запятые на точки
    coord_str = coord_str.replace(',', '.')
    
    # Удаляем все кроме цифр, точки и минуса
    coord_str = re.sub(r'[^\d.-]', '', coord_str)
    
    # Проверка на пустые значения
    if not coord_str or coord_str in ['.', '-', '-.']:
        return np.nan
    
    try:
        coord_float = float(coord_str)
        
        # Валидация по диапазонам для России
        if coord_type == 'lat':
            # Широта России: ~41° до 82°
            if 41 <= coord_float <= 82:
                return coord_float
            else:
                return np.nan
        else:  # lng
            # Долгота России: ~19° до 190°
            if 19 <= coord_float <= 190:
                return coord_float
            else:
                return np.nan
                
    except ValueError:
        return np.nan
    

def extract_official_road_code(road_title: str) -> Union[None, str]:
    """
    Извлекает только официальные коды дорог в формате буква-цифры
    """
    if pd.isna(road_title):
        return None
    
    road_str = str(road_title).strip()
    
    # ============= ПАТТЕРНЫ ТОЛЬКО ДЛЯ ОФИЦИАЛЬНЫХ КОДОВ =============
    
    # 1. Федеральные трассы: М-4, М-7, Р-22, А-136
    pattern1 = r'\b([ММPРAА])\s*[-–—]?\s*(\d+[А-ЯA-Z]?)\b'
    match = re.search(pattern1, road_str, re.IGNORECASE)
    if match:
        letter, number = match.groups()
        # Приводим к формату "М-4"
        return f"{letter.upper()}-{number}"
    
    # 2. Европейские маршруты: E-95, E-30
    pattern2 = r'\b(E)\s*[-–—]?\s*(\d+)\b'
    match = re.search(pattern2, road_str, re.IGNORECASE)
    if match:
        letter, number = match.groups()
        return f"{letter.upper()}-{number}"
    
    # 3. Азиатские маршруты: AH-6, AH-8
    pattern3 = r'\b(AH)\s*[-–—]?\s*(\d+)\b'
    match = re.search(pattern3, road_str, re.IGNORECASE)
    if match:
        letter, number = match.groups()
        return f"{letter.upper()}-{number}"
    
    # 4. Региональные с индексами: 50К-1, 60Н-2
    pattern4 = r'\b(\d{1,2}[КН])\s*[-–—]?\s*(\d+)\b'
    match = re.search(pattern4, road_str)
    if match:
        index, number = match.groups()
        return f"{index}-{number}"
    
    # Если ничего не нашли - возвращаем None
    return None


def get_base_weather(weather_str: str) -> str:
    """
    Определяет базовый тип погоды из строки
    """
    if pd.isna(weather_str):
        return 'Не указано'
    
    weather_lower = str(weather_str).lower()
    
    # Проверяем по приоритету (что важнее для вождения)
    if 'дождь' in weather_lower:
        return 'Дождь'
    elif 'снег' in weather_lower or 'метель' in weather_lower:
        return 'Снег'
    elif 'туман' in weather_lower:
        return 'Туман'
    elif 'пасмурно' in weather_lower:
        return 'Пасмурно'
    elif 'ясно' in weather_lower:
        return 'Ясно'
    else:
        return 'Другое'
    

def get_extreme_temp(weather_str: str) -> Union[str, None]:
    """
    Определяет экстремальную температуру из строки
    """
    if pd.isna(weather_str):
        return 'Не указано'
    
    weather_lower = str(weather_str).lower()
    
    # Проверяем по приоритету (что важнее для вождения)
    if 'ниже' in weather_lower:
        return '-30'
    elif 'выше' in weather_lower:
        return '+30'
    else:
        return np.nan


def categorize_violation(violation: str) -> str:
    """
    Определяет категорию нарушения
    """
    if pd.isna(violation) or violation == 'Нет нарушений':
        return 'Нет нарушений'
    
    v = str(violation).lower()
    
    # Словарь категорий с ключевыми словами
    categories = {
        'Превышение скорости': ['скорост', 'превышен'],
        'Нарушение дистанции': ['дистанц', 'интервал'],
        'Выезд на встречную полосу': ['встречн', 'обгон', 'выезд на'],
        'Несоблюдение очередности проезда': ['очередност', 'перекрест'],
        'Пешеходы': ['пешеход', 'переход'],
        'Нарушение расположения ТС': ['расположен', 'ряд', 'полос'],
        'Несоблюдение сигналов светофора/разметки': ['светофор', 'сигнал', 'знак', 'разметк'],
        'Опасные маневры': ['перестроен', 'разворот', 'задним', 'поворот'],
        'Неисправное техническое состояние': ['техническ', 'неисправн', 'эксплуатац'],
        'Нарушение правил перевозки': ['перевозк', 'груз', 'пассажир'],
        'Сопротивление': ['неповиновен', 'сопротивлен', 'полиц'],
        'Другое': ['другие', 'иные']
    }
    
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in v:
                return category
    
    return 'Прочее'