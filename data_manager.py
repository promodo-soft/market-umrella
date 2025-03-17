import os
import pandas as pd
import logging
from datetime import datetime
from config import DOMAINS_FILE, DATA_FILE, TRAFFIC_DECREASE_THRESHOLD
import json
from sheets_manager import SheetsManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация менеджера Google Sheets
sheets_manager = SheetsManager()

def load_domains():
    """
    Загружает список доменов из файла.
    
    Returns:
        list: Список доменов
    """
    try:
        if not os.path.exists(DOMAINS_FILE):
            logger.error(f"Файл с доменами {DOMAINS_FILE} не найден")
            return []
            
        with open(DOMAINS_FILE, 'r') as file:
            domains = [line.strip() for line in file if line.strip()]
            
        logger.info(f"Загружено {len(domains)} доменов из файла {DOMAINS_FILE}")
        return domains
    except Exception as e:
        logger.error(f"Ошибка при загрузке доменов из файла {DOMAINS_FILE}: {str(e)}")
        return []

def load_data():
    """
    Загружает данные о трафике из Excel файла.
    
    Returns:
        pandas.DataFrame: DataFrame с данными о трафике или пустой DataFrame, если файл не существует
    """
    try:
        if not os.path.exists(DATA_FILE):
            logger.info(f"Файл с данными {DATA_FILE} не найден, будет создан новый")
            return pd.DataFrame(columns=['domain'])
            
        df = pd.read_excel(DATA_FILE, index_col=0)
        logger.info(f"Загружены данные о трафике из файла {DATA_FILE}")
        return df
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных из файла {DATA_FILE}: {str(e)}")
        return pd.DataFrame(columns=['domain'])

def save_data(df):
    """
    Сохраняет данные о трафике в Excel файл.
    
    Args:
        df (pandas.DataFrame): DataFrame с данными о трафике
    
    Returns:
        bool: True, если данные сохранены успешно, иначе False
    """
    try:
        df.to_excel(DATA_FILE)
        logger.info(f"Данные о трафике сохранены в файл {DATA_FILE}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных в файл {DATA_FILE}: {str(e)}")
        return False

def update_traffic_data(domains_traffic):
    """
    Обновляет данные о трафике в Excel файле.
    
    Args:
        domains_traffic (dict): Словарь с данными о трафике для каждого домена
    
    Returns:
        tuple: (DataFrame с обновленными данными, список доменов с падением трафика)
    """
    try:
        # Загрузка существующих данных
        df = load_data()
        
        # Текущая дата для нового столбца
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Если DataFrame пустой, создаем его с доменами
        if df.empty or 'domain' not in df.columns:
            df = pd.DataFrame({'domain': list(domains_traffic.keys())})
            df.set_index('domain', inplace=True)
        
        # Добавляем новый столбец с текущей датой
        df[current_date] = pd.Series(domains_traffic)
        
        # Сохраняем обновленные данные
        save_data(df)
        
        # Проверяем падение трафика
        traffic_decrease = []
        if len(df.columns) >= 2:
            last_date = df.columns[-1]
            prev_date = df.columns[-2]
            
            for domain in df.index:
                if domain in domains_traffic:
                    current_traffic = df.loc[domain, last_date]
                    previous_traffic = df.loc[domain, prev_date]
                    
                    if pd.notna(current_traffic) and pd.notna(previous_traffic) and previous_traffic > 0:
                        decrease_percent = ((previous_traffic - current_traffic) / previous_traffic) * 100
                        
                        if decrease_percent >= TRAFFIC_DECREASE_THRESHOLD:
                            traffic_decrease.append({
                                'domain': domain,
                                'previous_traffic': previous_traffic,
                                'current_traffic': current_traffic,
                                'decrease_percent': decrease_percent
                            })
        
        return df, traffic_decrease
    except Exception as e:
        logger.error(f"Ошибка при обновлении данных о трафике: {str(e)}")
        return pd.DataFrame(), []

def load_traffic_data():
    """
    Загружает данные о трафике из Google Sheets.
    
    Returns:
        dict: Словарь с данными о трафике по доменам
    """
    return sheets_manager.load_traffic_data()

def save_traffic_data(domains_data):
    """
    Сохраняет данные о трафике в Google Sheets.
    
    Args:
        domains_data (dict): Словарь с данными о трафике по доменам
    """
    return sheets_manager.save_traffic_data(domains_data) 