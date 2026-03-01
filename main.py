import os
import sys
import logging
from typing import List

from tqdm import tqdm
import pandas as pd
import requests

from src.load_regions import load_regions
from src.fetcher import fetch_data
from src.parser import parse_data
from src.utils import partition_exists, remove_partition, should_rewrite, remove_partitioned_data
from src.transform_data import transform_data

from src.config import years, months, output_path, transform_path
import src.config as config


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)


def main():
    log.info('Запуск парсера')
    # Создаём папки
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Загрузка справочника регионов
    try:
        regions = load_regions()
        log.info(f"Справочник регионов загружен: {len(regions)} регион(ов) ✅")
    except Exception as e:
        log.error(f"Ошибка загрузки справочника регионов: {e} ❌")
        raise

    total_requests = len(years) * len(months) * len(regions)
    log.info(f"Начинаем загрузку: {total_requests} запросов")

    try:
        for year in years:
            for month in months:
                if partition_exists(output_path, year, month, log):
                    log.info(f'Найдены данные за {month:02d}.{year}')
                
                    if should_rewrite(year, month):
                        log.warning(f'Удаляем старые данные за {month:02d}.{year}')
                        remove_partition(output_path, year, month, log)
                    else:
                        log.info(f'Пропускаем {month:02d}.{year}')
                        continue

                month_dfs: List[pd.DataFrame] = []

                parsed_region = 0
                error_parse = 0
                error_regions = []

                placeholder = f'Загрзука регионов за {month:02d}.{year}'

                for region_code in tqdm(regions['code'].tolist(), desc=placeholder, leave=False):
                    try:
                        # Получение ответа от сервера ГИБДД
                        load_data = fetch_data(year, month, region_code)
                        # Обработка ответа
                        parsed_data = parse_data(load_data)
                        if parsed_data is not None and not parsed_data.empty:
                            parsed_data['year'] = year
                            parsed_data['month'] = month
                            month_dfs.append(parsed_data)
                            parsed_region += 1
                        
                    except (requests.RequestException, TimeoutError) as e:
                        error_parse += 1
                        error_regions.append(region_code)
                        log.debug(f'Ошибка запроса: {month:02d}.{year}, регион {region_code}: {e}')
                    except (KeyError, TypeError, IndexError) as e:
                        error_parse += 1
                        error_regions.append(region_code)
                        log.debug(f'Ошибка парсинга: {month:02d}.{year}, регион {region_code}: {e}')
                    except Exception as e:
                        error_parse += 1
                        error_regions.append(region_code)
                        log.debug(f'Неизвестная ошибка: {month:02d}.{year}, регион {region_code}: {e}')


                log.info(f'Успешно: {parsed_region}, ошибок: {error_parse} ({", ".join(error_regions)})')
                log.info(f'Сохранение данных за {month:02d}.{year}')

                if month_dfs:
                    combined_month = pd.concat(month_dfs, ignore_index=True)
                    combined_month.to_parquet(
                        output_path,
                        partition_cols=['year', 'month'],
                        engine='pyarrow',
                        compression='snappy',
                        index=False
                    )
                    log.info(f'Сохранено: {len(combined_month)} записей')
                
        log.info('✅ Загрузка завершена')
    

    except KeyboardInterrupt:
        log.warning('🛑 Остановлено пользователем (Ctrl+C)')
        sys.exit(0)
    except Exception as e:
        log.critical(f'Критическая ошибка: {e}')
        sys.exit(1)

    # Обработка данных
    log.info('Начало обработки данных')
    remove_partitioned_data(transform_path, log)
    transform_data(output_path, log)

    log.info('Обработка данных завершена')

if __name__ == '__main__':
    main()
