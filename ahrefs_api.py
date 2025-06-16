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

def get_current_organic_traffic(domain):
    """
    ОПТИМИЗИРОВАННАЯ ВЕРСИЯ: Получает только ТЕКУЩИЙ органический трафик для домена.
    Вместо запроса месячной истории получает актуальные данные за сегодня.
    
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
        
        logger.info(f"[{domain}] ОПТИМІЗОВАНИЙ запит - отримуємо тільки поточний трафік")

        conn = http.client.HTTPSConnection("api.ahrefs.com")
        
        headers = {
            'Accept': "application/json",
            'Authorization': f"Bearer {AHREFS_API_KEY}"
        }
        
        # ОПТИМИЗАЦИЯ: используем metrics endpoint с volume_mode=average для консистентности
        current_date = datetime.now().strftime('%Y-%m-%d')
        endpoint = f"/v3/site-explorer/metrics?target={domain}&mode=domain&volume_mode=average&date={current_date}"
        
        logger.info(f"[{domain}] Оптимізований endpoint: {endpoint}")
        
        conn.request("GET", endpoint, headers=headers)
        response = conn.getresponse()
        data = response.read()
        response_text = data.decode("utf-8")
        
        logger.info(f"[{domain}] Статус відповіді: {response.status}")
        
        if response.status == 200:
            json_data = json.loads(response_text)
            logger.info(f"[{domain}] Успішна відповідь: {response_text}")
            
            # Получаем текущий трафик из overview
            traffic = json_data.get("org_traffic", 0)
            logger.info(f"[{domain}] Поточний трафік: {traffic}")
            return int(traffic)
            
        elif response.status == 401:
            logger.error(f"[{domain}] Помилка авторизації API Ahrefs")
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

def get_batch_organic_traffic(domains_batch):
    """
    ОПТИМИЗИРОВАННЫЙ BATCH ЗАПРОС: Использует правильный /batch-analysis endpoint.
    Получает трафик для нескольких доменов за один API вызов с volume_mode=average.
    
    Args:
        domains_batch (list): Список доменов (максимум 50 доменов за раз)
        
    Returns:
        dict: Словарь {domain: traffic_value}
    """
    results = {}
    
    if not AHREFS_API_KEY:
        logger.error("AHREFS_API_KEY не знайдений в змінних середовища")
        return results
    
    if not domains_batch:
        return results
        
    # Ограничиваем размер batch до 50 доменов
    batch_size = min(len(domains_batch), 50)
    current_batch = domains_batch[:batch_size]
    
    logger.info(f"BATCH ANALYSIS запит для {len(current_batch)} доменів: {current_batch}")
    
    try:
        conn = http.client.HTTPSConnection("api.ahrefs.com")
        
        headers = {
            'Accept': "application/json",
            'Authorization': f"Bearer {AHREFS_API_KEY}",
            'Content-Type': "application/json"
        }
        
        # Правильный batch endpoint с POST запросом
        endpoint = "/v3/site-explorer/batch-analysis"
        
        # Формируем JSON body для batch запроса
        request_body = {
            "targets": current_batch,
            "mode": "domain",
            "volume_mode": "average",  # Используем режим average как указано
            "date": datetime.now().strftime('%Y-%m-%d')  # Текущая дата
            # country не указываем, так как не обязательный
        }
        
        json_body = json.dumps(request_body)
        logger.info(f"BATCH endpoint: {endpoint}")
        logger.info(f"BATCH body: {json_body}")
        
        conn.request("POST", endpoint, body=json_body, headers=headers)
        response = conn.getresponse()
        data = response.read()
        response_text = data.decode("utf-8")
        
        logger.info(f"BATCH статус відповіді: {response.status}")
        
        if response.status == 200:
            json_data = json.loads(response_text)
            logger.info(f"BATCH успішна відповідь отримана")
            
            # Обрабатываем batch ответ - ожидаем массив объектов
            if isinstance(json_data, list):
                for domain_data in json_data:
                    target = domain_data.get("target", "")
                    traffic = domain_data.get("org_traffic", 0)
                    if target:
                        results[target] = int(traffic)
                        logger.info(f"[BATCH] {target}: {traffic}")
            else:
                # Если ответ в другом формате
                logger.warning(f"Неочікуваний формат відповіді BATCH: {json_data}")
                
        else:
            logger.error(f"BATCH помилка API Ahrefs ({response.status})")
            logger.error(f"BATCH відповідь: {response_text}")
            
            # Fallback: пробуем индивидуальные запросы
            logger.info("Fallback до індивідуальних запитів")
            for domain in current_batch:
                results[domain] = get_current_organic_traffic(domain)
                
    except Exception as e:
        logger.error(f"BATCH неочікувана помилка: {str(e)}")
        import traceback
        logger.error(f"BATCH traceback: {traceback.format_exc()}")
        # Fallback: пробуем индивидуальные запросы
        logger.info("Fallback до індивідуальних запитів через помилку")
        for domain in current_batch:
            results[domain] = get_current_organic_traffic(domain)
    finally:
        conn.close()
        
    return results

# Оставляем старую функцию для совместимости, но делаем ее оптимизированной
def get_organic_traffic(domain):
    """
    УСТАРЕВШАЯ функция для совместимости.
    Теперь использует оптимизированный endpoint.
    """
    return get_current_organic_traffic(domain)

def check_api_availability():
    """
    Проверяет доступность API Ahrefs используя оптимизированный endpoint.
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
        
        # ОПТИМИЗАЦИЯ: используем metrics endpoint для проверки API
        current_date = datetime.now().strftime('%Y-%m-%d')
        endpoint = f"/v3/site-explorer/metrics?target=ahrefs.com&mode=domain&volume_mode=average&date={current_date}"
        
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