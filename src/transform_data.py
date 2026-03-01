from logging import Logger
from pathlib import Path

import pandas as pd

from src.utils import *
from src.config import transform_path


def transform_data(file_path: Path, log: Logger) -> None:
    log.info('Загрузка данных')
    df = pd.read_parquet(file_path)
    df_process = df.copy()
    
    # id
    log.info('Генерация id аварии')
    df_process['id'] = df.apply(create_hash_id, axis=1)

    # datetime
    log.info('Преобразование даты')
    df_process['time'] = df['time'].apply(parse_time)

    df_process['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y', dayfirst=True, errors='coerce')

    df_process['date'] = pd.to_datetime(
        df_process['date'].dt.strftime('%d.%m.%Y') + ' ' + df_process['time'].fillna('00:00:00'), 
        dayfirst=True,
        errors='coerce'
    )

    df_process['date'].isna().sum()

    df_process = df_process.rename(columns={'date': 'datetime'}).drop('time', axis=1)

    # lat & lng
    log.info('Преобразование координат')
    df_process['lat'] = df['lat'].apply(lambda x: clean_single_coord(x, 'lat'))
    df_process['lng'] = df['lng'].apply(lambda x: clean_single_coord(x, 'lng'))

    # dtp_type
    log.info('Выделение групп из типов аварии')
    # Выделим более крупные группы и преобразуем текущие в более лаконичные
    group_mapping = {
        # Столкновения (самый массовый тип)
        'Столкновение': 'Столкновения',
        
        # Наезды (все виды наездов)
        'Наезд на пешехода': 'Наезды',
        'Наезд на велосипедиста': 'Наезды',
        'Наезд на стоящее ТС': 'Наезды',
        'Наезд на препятствие': 'Наезды',
        'Наезд на животное': 'Наезды',
        'Наезд на гужевой транспорт': 'Наезды',
        'Наезд на лицо, использующее для передвижения СИМ': 'Наезды',
        'Наезд на лицо, не являющееся участником дорожного движения, осуществляющее производство работ': 'Наезды',
        'Наезд на лицо, не являющееся участником дорожного движения, осуществляющее несение службы': 'Наезды',
        'Наезд на лицо, не являющееся участником дорожного движения, осуществляющее какую-либо другую деятельность': 'Наезды',
        'Наезд на внезапно возникшее препятствие': 'Наезды',
        
        # Потеря управления
        'Съезд с дороги': 'Потеря управления',
        'Опрокидывание': 'Потеря управления',
        
        # Падения и происшествия
        'Падение пассажира': 'Падения и происшествия',
        'Падение груза': 'Падения и происшествия',
        'Отбрасывание предмета': 'Падения и происшествия',
        
        # Редкие и специфические
        'Иной вид ДТП': 'Прочие',
        'Возгорание вследствие технической неисправности движущегося или остановившегося ТС, участвующего в дорожном движении.': 'Прочие'
    }

    df_process['dtp_type_group'] = df['dtp_type'].map(group_mapping)


    type_mapping = {
        # Столкновения
        'Столкновение': 'Столкновения транспортных средств',
        
        # Наезды на уязвимых участников
        'Наезд на пешехода': 'Наезды на пешеходов',
        'Наезд на велосипедиста': 'Наезды на велосипедистов',
        'Наезд на лицо, использующее для передвижения СИМ': 'Наезды на СИМ',
        
        # Наезды на объекты
        'Наезд на стоящее ТС': 'Наезды на припаркованный транспорт',
        'Наезд на препятствие': 'Наезды на препятствия',
        'Наезд на внезапно возникшее препятствие': 'Наезды на препятствия',
        
        # Наезды на животных
        'Наезд на животное': 'Наезды на животных',
        'Наезд на гужевой транспорт': 'Наезды на гужевой транспорт',
        
        # Наезды на людей вне ДД
        'Наезд на лицо, не являющееся участником дорожного движения, осуществляющее производство работ': 'Наезды на дорожных рабочих',
        'Наезд на лицо, не являющееся участником дорожного движения, осуществляющее несение службы': 'Наезды на сотрудников служб',
        'Наезд на лицо, не являющееся участником дорожного движения, осуществляющее какую-либо другую деятельность': 'Прочие наезды',
        
        # Потеря управления
        'Съезд с дороги': 'Съезды с дороги',
        'Опрокидывание': 'Опрокидывания',
        
        # Происшествия
        'Падение пассажира': 'Падения пассажиров',
        'Падение груза': 'Падения грузов',
        'Отбрасывание предмета': 'Отбрасывание предметов',
        
        # Прочие
        'Иной вид ДТП': 'Иные виды ДТП',
        'Возгорание вследствие технической неисправности движущегося или остановившегося ТС, участвующего в дорожном движении.': 'Возгорания ТС'
    }

    df_process['dtp_type'] = df['dtp_type'].map(type_mapping)

    # road_code
    log.info('Извлечение кода дороги')
    df_process['road_code'] = df['road_title'].apply(extract_official_road_code)

    # weather
    log.info('Преобразование данных о погоде')
    # Перевод массива погоды в строку
    df_process['weather_float'] = df['weather'].apply(lambda x: ', '.join(x))

    # Извлечение базовой погоды
    df_process['weather_base'] = df_process['weather_float'].apply(get_base_weather)

    # Извлечение температуры
    df_process['extreme_temp'] = df_process['weather_float'].apply(get_extreme_temp)

    # road_cond
    log.info('Преобразования состояния дороги')
    condition_map = {
        'Сухое': 'Сухое',
        'Мокрое': 'Мокрое',
        'Залитое (покрытое) водой': 'Мокрое',
        'Заснеженное': 'Зимние условия',
        'Со снежным накатом': 'Зимние условия',
        'Гололедица': 'Зимние условия',
        'Обработанное противогололедными материалами': 'Обработанное',
        'Загрязненное': 'Специфическое',
        'Пыльное': 'Специфическое',
        'Свежеуложенная поверхностная обработка': 'Специфическое',
        'Не установлено': 'Не указано'
    }
    
    df_process['road_cond'] = df['road_cond'].map(condition_map).fillna('Другое')

    # violations
    log.info('Приобразование нарушений ПДД')
    df_process['driver_violations'] = df['driver_violations'].fillna("['Нет нарушений']")
    df_process['driver_violations_float'] = df_process['driver_violations'].apply(lambda x: ', '.join(x))

    df_process['driver_violation_category'] = df_process['driver_violations_float'].apply(categorize_violation)

    log.info('Выделение нужных столбцов и сохренение')
    selected_cols = ['id', 'datetime', 'lat', 'lng', 'dtp_type_group',
                  'dtp_type', 'weather_base', 'extreme_temp', 'road_code', 'car_mark', 'car_model', 'color', 'car_year',
                  'driver_gender', 'driver_exp', 'driver_alco', 'driver_violation_category', 'passenger_count', 'death_count', 'wounded_count', 'year', 'month']

    df_process = df_process[selected_cols]

    df_process.to_parquet(
        transform_path,
        partition_cols=['year', 'month'],
        engine='pyarrow',
        compression='snappy',
        index=False
    )