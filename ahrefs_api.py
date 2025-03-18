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
        if not AHREFS_API_KEY:
            logger.error("AHREFS_API_KEY не найден в переменных окружения")
            return 0

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
        logger.debug(f"Даты запроса: с {date_from} по {date_to}")
        
        conn.request("GET", endpoint, headers=headers)
        response = conn.getresponse()
        data = response.read()
        
        logger.info(f"Получен ответ от API для домена {domain}. Статус: {response.status}")
        
        if response.status == 200:
            json_data = json.loads(data.decode("utf-8"))
            
            # Получаем последнее значение трафика из истории
            metrics = json_data.get("metrics", [])
            
            if not metrics:
                logger.warning(f"Нет данных о трафике для домена {domain}")
                return 0
                
            traffic = metrics[-1].get("organic_traffic", 0)
            logger.info(f"Успешно получен трафик для домена {domain}: {traffic}")
            return int(traffic)
            
        elif response.status == 401:
            logger.error(f"Ошибка авторизации API Ahrefs. Проверьте ключ API. Ответ: {data.decode('utf-8')}")
            return 0
        elif response.status == 429:
            logger.error(f"Превышен лимит запросов к API Ahrefs. Ответ: {data.decode('utf-8')}")
            return 0
        else:
            logger.error(f"Ошибка API Ahrefs ({response.status}): {data.decode('utf-8')}")
            return 0
            
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка при разборе JSON ответа для домена {domain}: {str(e)}")
        return 0
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении данных о трафике для домена {domain}: {str(e)}")
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