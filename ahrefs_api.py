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
    response_text = None
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
        
        logger.info(f"[{domain}] Отправка запроса к API")
        logger.info(f"[{domain}] Endpoint: {endpoint}")
        logger.info(f"[{domain}] Даты запроса: с {date_from} по {date_to}")
        logger.info(f"[{domain}] API Key (первые 4 символа): {AHREFS_API_KEY[:4]}...")
        
        conn.request("GET", endpoint, headers=headers)
        response = conn.getresponse()
        data = response.read()
        response_text = data.decode("utf-8")
        
        logger.info(f"[{domain}] Статус ответа: {response.status}")
        logger.info(f"[{domain}] Полный ответ API: {response_text}")
        
        if response.status == 200:
            json_data = json.loads(response_text)
            
            # Получаем последнее значение трафика из истории
            metrics = json_data.get("metrics", [])
            logger.info(f"[{domain}] Полученные метрики: {metrics}")
            
            if not metrics:
                logger.warning(f"[{domain}] Нет данных о трафике")
                return 0
                
            traffic = metrics[-1].get("organic_traffic", 0)
            logger.info(f"[{domain}] Успешно получен трафик: {traffic}")
            return int(traffic)
            
        elif response.status == 401:
            logger.error(f"[{domain}] Ошибка авторизации API Ahrefs. Проверьте ключ API")
            logger.error(f"[{domain}] Ответ: {response_text}")
            return 0
        elif response.status == 429:
            logger.error(f"[{domain}] Превышен лимит запросов к API Ahrefs")
            logger.error(f"[{domain}] Ответ: {response_text}")
            return 0
        else:
            logger.error(f"[{domain}] Ошибка API Ahrefs ({response.status})")
            logger.error(f"[{domain}] Ответ: {response_text}")
            return 0
            
    except json.JSONDecodeError as e:
        logger.error(f"[{domain}] Ошибка при разборе JSON ответа: {str(e)}")
        if response_text:
            logger.error(f"[{domain}] Полученный текст: {response_text}")
        return 0
    except Exception as e:
        logger.error(f"[{domain}] Неожиданная ошибка: {str(e)}")
        import traceback
        logger.error(f"[{domain}] Traceback: {traceback.format_exc()}")
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