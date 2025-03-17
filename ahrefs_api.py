import http.client
import json
import logging
from datetime import datetime, timedelta
from config import AHREFS_API_KEY, AHREFS_API_URL

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ahrefs_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_organic_traffic(domain):
    """
    Получает органический трафик для указанного домена через API Ahrefs v3.
    
    Args:
        domain (str): Домен для проверки
        
    Returns:
        int: Значение органического трафика или 0 в случае ошибки
    """
    try:
        conn = http.client.HTTPSConnection("api.ahrefs.com")
        
        headers = {
            'Accept': "application/json",
            'Authorization': f"Bearer {AHREFS_API_KEY}"
        }
        
        # Получаем даты для запроса (последний месяц)
        date_to = datetime.now().strftime('%Y-%m-%d')
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        endpoint = f"/v3/site-explorer/metrics-history?target={domain}&mode=domain&date_from={date_from}&date_to={date_to}&volume_mode=monthly&history_grouping=monthly"
        
        logger.info(f"Отправка запроса к API для домена {domain}")
        logger.debug(f"URL: {endpoint}")
        logger.debug(f"Заголовки: {headers}")
        
        conn.request("GET", endpoint, headers=headers)
        response = conn.getresponse()
        data = response.read()
        
        logger.debug(f"Статус ответа: {response.status}")
        logger.debug(f"Заголовки ответа: {response.getheaders()}")
        logger.debug(f"Ответ API: {data.decode('utf-8')}")
        
        if response.status == 200:
            json_data = json.loads(data.decode("utf-8"))
            logger.debug(f"Распарсенный ответ: {json_data}")
            
            try:
                # Получаем последнее значение трафика из истории
                metrics = json_data.get("metrics", [])
                logger.debug(f"Метрики: {metrics}")
                
                if metrics:
                    traffic = metrics[-1].get("organic_traffic", 0)
                    logger.info(f"Получен трафик для домена {domain}: {traffic}")
                    return int(traffic)
                else:
                    logger.warning(f"Нет данных о трафике для домена {domain}")
                    return 0
            except (KeyError, TypeError, IndexError) as e:
                logger.warning(f"Не удалось получить данные о трафике для домена {domain}. Ошибка: {str(e)}. Ответ API: {json_data}")
                return 0
        else:
            logger.error(f"Ошибка API Ahrefs: {response.status} - {data.decode('utf-8')}")
            return 0
            
    except Exception as e:
        logger.error(f"Ошибка при получении данных о трафике для домена {domain}: {str(e)}")
        return 0
    finally:
        conn.close()

def check_api_availability():
    """
    Проверяет доступность API Ahrefs.
    
    Returns:
        bool: True, если API доступно, иначе False
    """
    try:
        conn = http.client.HTTPSConnection("api.ahrefs.com")
        
        headers = {
            'Accept': "application/json",
            'Authorization': f"Bearer {AHREFS_API_KEY}"
        }
        
        date_to = datetime.now().strftime('%Y-%m-%d')
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        endpoint = f"/v3/site-explorer/metrics-history?target=ahrefs.com&mode=domain&date_from={date_from}&date_to={date_to}&volume_mode=monthly&history_grouping=monthly"
        
        conn.request("GET", endpoint, headers=headers)
        response = conn.getresponse()
        
        if response.status == 200:
            logger.info("API Ahrefs доступно")
            return True
        else:
            logger.error(f"API Ahrefs недоступно. Код ответа: {response.status} - {response.read().decode('utf-8')}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при проверке доступности API Ahrefs: {str(e)}")
        return False
    finally:
        conn.close() 