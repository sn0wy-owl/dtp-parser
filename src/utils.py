from pathlib import Path
import logging

from pyarrow import parquet as pq

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
    

def remove_partiton(data_path: Path, year: int, month: int, log: logging.Logger) -> None:
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


def should_rewrite(year: int, month: int) -> bool:
    if config.rewrite_all is None:
        while True:
            answer = input(
                f'Перезаписать данные за {month:02d}.{year}?\n'
                f'1 - перезаписать\n'
                f'2 - пропустить обработку\n'
                f'3 - перезаписать (для всех)\n'
                f'4 - пропустить обработку (для всех)\n'
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
    