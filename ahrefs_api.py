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
            logger.error("AHREFS_API_KEY не знайдений в змінних середовища")
            return 0
        
        logger.info(f"[{domain}] Використовуємо ключ AHREFS_API_KEY (перші 4 символи: {AHREFS_API_KEY[:4]}, довжина: {len(AHREFS_API_KEY)})")

        conn = http.client.HTTPSConnection("api.ahrefs.com")
        
        headers = {
            'Accept': "application/json",
            'Authorization': f"Bearer {AHREFS_API_KEY}"
        }
        
        # Получаем даты для запроса (последний месяц)
        date_to = datetime.now().strftime('%Y-%m-%d')
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        endpoint = f"/v3/site-explorer/metrics-history?target={domain}&mode=domain&date_from={date_from}&date_to={date_to}&volume_mode=monthly&history_grouping=monthly"
        
        logger.info(f"[{domain}] Відправка запиту до API")
        logger.info(f"[{domain}] Endpoint: {endpoint}")
        logger.info(f"[{domain}] Дати запиту: з {date_from} по {date_to}")
        logger.info(f"[{domain}] API Key (перші 4 символи): {AHREFS_API_KEY[:4]}...")
        
        conn.request("GET", endpoint, headers=headers)
        response = conn.getresponse()
        data = response.read()
        response_text = data.decode("utf-8")
        
        logger.info(f"[{domain}] Статус відповіді: {response.status}")
        logger.info(f"[{domain}] Повна відповідь API: {response_text}")
        
        if response.status == 200:
            json_data = json.loads(response_text)
            
            # Получаем последнее значение трафика из истории
            metrics = json_data.get("metrics", [])
            logger.info(f"[{domain}] Отримані метрики: {metrics}")
            
            if not metrics:
                logger.warning(f"[{domain}] Немає даних про трафік")
                return 0
                
            traffic = metrics[-1].get("org_traffic", 0)
            logger.info(f"[{domain}] Трафік успішно отримано: {traffic}")
            return int(traffic)
            
        elif response.status == 401:
            logger.error(f"[{domain}] Помилка авторизації API Ahrefs. Перевірте ключ API")
            logger.error(f"[{domain}] Відповідь: {response_text}")
            return 0
        elif response.status == 429:
            logger.error(f"[{domain}] Перевищено ліміт запитів до API Ahrefs")
            logger.error(f"[{domain}] Відповідь: {response_text}")
            return 0
        else:
            logger.error(f"[{domain}] Помилка API Ahrefs ({response.status})")
            logger.error(f"[{domain}] Відповідь: {response_text}")
            return 0
            
    except json.JSONDecodeError as e:
        logger.error(f"[{domain}] Помилка при розборі JSON відповіді: {str(e)}")
        if response_text:
            logger.error(f"[{domain}] Отриманий текст: {response_text}")
        return 0
    except Exception as e:
        logger.error(f"[{domain}] Неочікувана помилка: {str(e)}")
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
        logger.info("Початок перевірки доступності API Ahrefs")
        if not AHREFS_API_KEY:
            logger.error("AHREFS_API_KEY не знайдений в змінних середовища (в функції check_api_availability)")
            return False
            
        logger.info(f"Використовуємо ключ AHREFS_API_KEY (перші 4 символи: {AHREFS_API_KEY[:4]}, довжина: {len(AHREFS_API_KEY)})")
        
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
            logger.info("API Ahrefs доступний")
            return True
        else:
            logger.error(f"API Ahrefs недоступний. Код відповіді: {response.status} - {response.read().decode('utf-8')}")
            return False
            
    except Exception as e:
        logger.error(f"Помилка при перевірці доступності API Ahrefs: {str(e)}")
        return False
    finally:
        conn.close() 