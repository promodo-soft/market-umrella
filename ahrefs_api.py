import http.client
import json
import logging
from datetime import datetime, timedelta
from config import AHREFS_API_KEY, AHREFS_API_URL

# Глобальный флаг для отслеживания лимитов API
_api_limit_reached = False

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

def is_api_limit_reached():
    """Проверяет, достигнут ли лимит API"""
    return _api_limit_reached

def reset_api_limit_flag():
    """Сбрасывает флаг лимита API (для тестирования или нового цикла)"""
    global _api_limit_reached
    _api_limit_reached = False
    logger.info("Флаг лимита API скинуто")

def get_api_limit_message():
    """Возвращает сообщение о достижении лимитов API для уведомлений"""
    if _api_limit_reached:
        return "🚫 *Увага!*\n\nДосягнуто ліміт API Ahrefs!\n\n" \
               "📊 Збір даних трафіку призупинено до відновлення лімітів.\n" \
               "⏰ Ліміти зазвичай оновлюються щодня о 00:00 UTC.\n\n" \
               "🔄 Наступна спроба буде виконана автоматично за розкладом."
    return None

def _set_api_limit_reached(status_code, response_text=""):
    """Устанавливает флаг лимита API при получении ошибки 403"""
    global _api_limit_reached
    if status_code == 403:
        _api_limit_reached = True
        logger.error(f"🚫 ЛІМІТ API ДОСЯГНУТО! Статус: {status_code}. Подальші запити будуть пропущені.")
        logger.error(f"Відповідь API: {response_text}")
        
        # Проверяем, содержит ли ответ информацию о лимитах
        if "API units limit reached" in response_text:
            logger.error("💥 API UNITS LIMIT EXCEEDED - потрібно зачекати до відновлення лімітів")
        elif "Rate limit" in response_text:
            logger.error("⏰ RATE LIMIT EXCEEDED - забагато запитів за короткий час")
        
        return True
    return False

def get_current_organic_traffic(domain):
    """
    ОПТИМИЗИРОВАННАЯ ВЕРСИЯ: Получает только ТЕКУЩИЙ органический трафик для домена.
    Вместо запроса месячной истории получает актуальные данные за сегодня.
    
    Args:
        domain (str): Домен для проверки
        
    Returns:
        int: Значение органического трафика или 0 в случае ошибки
    """
    # Проверяем, не достигнут ли лимит API
    if _api_limit_reached:
        logger.warning(f"[{domain}] ⚠️ Пропускаємо запит - ліміт API вже досягнуто")
        return None  # Возвращаем None вместо 0 для индикации недоступности API
    
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
        
        # Проверяем на лимит API (403)
        if _set_api_limit_reached(response.status, response_text):
            return None  # Возвращаем None при достижении лимитов
        
        if response.status == 200:
            try:
                json_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"[{domain}] Помилка парсингу JSON: {e}")
                logger.error(f"[{domain}] Перші 500 символів відповіді: {response_text[:500]}")
                return 0
            
            # Логируем полную структуру для отладки (GitHub Actions замаскирует чувствительные данные)
            logger.info(f"[{domain}] Успішна відповідь: {response_text}")
            
            # Проверяем структуру ответа детально
            logger.info(f"[{domain}] Тип відповіді: {type(json_data)}")
            logger.info(f"[{domain}] Ключі верхнього рівня: {list(json_data.keys()) if isinstance(json_data, dict) else 'Не словник'}")
            
            # Пробуем получить данные напрямую из корня (для совместимости со старым API)
            traffic = json_data.get("org_traffic", 0) if isinstance(json_data, dict) else 0
            
            # Если не нашли в корне, ищем в metrics
            if traffic == 0 and isinstance(json_data, dict) and "metrics" in json_data:
                metrics = json_data.get("metrics", {})
                logger.info(f"[{domain}] Знайдено об'єкт metrics, ключі: {list(metrics.keys()) if isinstance(metrics, dict) else 'Не словник'}")
                traffic = metrics.get("org_traffic", 0) if isinstance(metrics, dict) else 0
            
            # Дополнительная проверка - может данные во вложенном объекте metrics.metrics
            if traffic == 0 and isinstance(json_data, dict):
                # Рекурсивный поиск org_traffic
                def find_org_traffic(obj, path=""):
                    if isinstance(obj, dict):
                        if "org_traffic" in obj:
                            logger.info(f"[{domain}] Знайдено org_traffic по шляху {path}: {obj['org_traffic']}")
                            return obj["org_traffic"]
                        for key, value in obj.items():
                            result = find_org_traffic(value, f"{path}.{key}")
                            if result is not None:
                                return result
                    return None
                
                found_traffic = find_org_traffic(json_data)
                if found_traffic is not None:
                    traffic = found_traffic
            
            logger.info(f"[{domain}] Фінальний трафік: {traffic}")
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
    
    # Проверяем, не достигнут ли лимит API
    if _api_limit_reached:
        logger.warning(f"⚠️ Пропускаємо BATCH запит для {len(domains_batch)} доменів - ліміт API вже досягнуто")
        # Возвращаем нулевые значения для всех доменов
        for domain in domains_batch:
            results[domain] = 0
        return results
    
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
        }
        
        json_body = json.dumps(request_body)
        logger.info(f"BATCH endpoint: {endpoint}")
        logger.info(f"BATCH body: {json_body}")
        
        conn.request("POST", endpoint, body=json_body, headers=headers)
        response = conn.getresponse()
        data = response.read()
        response_text = data.decode("utf-8")
        
        logger.info(f"BATCH статус відповіді: {response.status}")
        
        # Проверяем на лимит API (403) для batch запроса
        if _set_api_limit_reached(response.status, response_text):
            # Возвращаем нулевые значения для всех доменов в batch
            for domain in current_batch:
                results[domain] = 0
            return results
        
        if response.status == 200:
            json_data = json.loads(response_text)
            logger.info(f"BATCH успішна відповідь отримана")
            
            # Обрабатываем batch ответ - ожидаем массив объектов
            if isinstance(json_data, list):
                for idx, domain_data in enumerate(json_data):
                    target = domain_data.get("target", "")
                    
                    # Рекурсивный поиск org_traffic в объекте
                    def find_org_traffic(obj, path=""):
                        if isinstance(obj, dict):
                            if "org_traffic" in obj:
                                return obj["org_traffic"]
                            for key, value in obj.items():
                                result = find_org_traffic(value, f"{path}.{key}")
                                if result is not None:
                                    return result
                        return None
                    
                    traffic = find_org_traffic(domain_data)
                    if traffic is None:
                        traffic = 0
                        logger.warning(f"[BATCH] Не знайдено org_traffic для {target} в об'єкті {idx}")
                    
                    if target:
                        results[target] = int(traffic)
                        logger.info(f"[BATCH] {target}: {traffic}")
            else:
                # Если ответ в другом формате
                logger.warning(f"Неочікуваний формат відповіді BATCH: {json_data}")
                
        else:
            logger.error(f"BATCH помилка API Ahrefs ({response.status})")
            logger.error(f"BATCH відповідь: {response_text}")
            
            # Fallback: пробуем индивидуальные запросы только если лимит не достигнут
            if not _api_limit_reached:
                logger.info("Fallback до індивідуальних запитів")
                for domain in current_batch:
                    results[domain] = get_current_organic_traffic(domain)
                    # Если в процессе индивидуальных запросов достигли лимита, прекращаем
                    if _api_limit_reached:
                        logger.warning("Ліміт API досягнуто під час fallback запитів. Припиняємо обробку.")
                        break
            else:
                # Если лимит уже достигнут, возвращаем нули
                for domain in current_batch:
                    results[domain] = 0
                
    except Exception as e:
        logger.error(f"BATCH неочікувана помилка: {str(e)}")
        import traceback
        logger.error(f"BATCH traceback: {traceback.format_exc()}")
        # Fallback: пробуем индивидуальные запросы только если лимит не достигнут
        if not _api_limit_reached:
            logger.info("Fallback до індивідуальних запитів через помилку")
            for domain in current_batch:
                results[domain] = get_current_organic_traffic(domain)
                # Если в процессе индивидуальных запросов достигли лимита, прекращаем
                if _api_limit_reached:
                    logger.warning("Ліміт API досягнуто під час fallback запитів через помилку. Припиняємо обробку.")
                    break
        else:
            # Если лимит уже достигнут, возвращаем нули
            for domain in current_batch:
                results[domain] = 0
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
        response_text = response.read().decode('utf-8')
        
        # Проверяем на лимит API (403)
        if _set_api_limit_reached(response.status, response_text):
            return False
        
        if response.status == 200:
            logger.info("API Ahrefs доступний")
            return True
        else:
            logger.error(f"API Ahrefs недоступний. Код відповіді: {response.status} - {response_text}")
            return False
            
    except Exception as e:
        logger.error(f"Помилка при перевірці доступності API Ahrefs: {str(e)}")
        return False
    finally:
        conn.close() 