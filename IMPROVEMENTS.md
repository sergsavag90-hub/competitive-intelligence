# Покращення Конкурентної Розвідки

Цей документ описує нові можливості, додані до системи конкурентної розвідки.

## 🎯 Огляд

Реалізовано розширені можливості аналізу та звітності відповідно до роадмапу покращень:

1. **Аналіз Цінової Політики** - відстеження динаміки цін та конкурентного ціноутворення
2. **Виявлення Змін** - автоматичне виявлення нових продуктів, акцій та цінових змін
3. **LLM Інтеграція** - глибокий аналіз за допомогою штучного інтелекту
4. **Етичний Скрейпінг** - дотримання правил robots.txt та етичних норм

---

## 📊 1. Аналіз Цінової Політики (PriceAnalyzer)

### Можливості

#### Аналіз трендів цін
```python
from src.utils.price_analyzer import PriceAnalyzer
from src.database.db_manager import DatabaseManager

db = DatabaseManager()
analyzer = PriceAnalyzer(db)

# Аналіз за останні 30 днів
trends = analyzer.analyze_price_trends(competitor_id=1, days=30)

print(trends['summary'])
# {
#   'increasing_count': 15,    # Товарів з підвищенням цін
#   'decreasing_count': 8,     # Товарів зі зниженням цін
#   'stable_count': 42,        # Стабільні ціни
#   'volatile_count': 5        # Високо волатильні
# }
```

#### Порівняння цін між конкурентами
```python
# Знайти цінові розриви
comparison = analyzer.compare_prices_with_competitors(category='electronics')

for gap in comparison['price_gaps'][:5]:
    print(f"{gap['product_name']}: розрив {gap['price_difference_percent']}%")
    print(f"  Найдешевший: {gap['cheapest_competitor']}")
    print(f"  Найдорожчий: {gap['most_expensive_competitor']}")
```

#### Визначення цінової стратегії
```python
strategy = analyzer.detect_pricing_strategy(competitor_id=1)

print(f"Стратегія: {strategy['strategy']}")
# Можливі значення:
# - aggressive_discounting (агресивні знижки)
# - moderate_discounting (помірні знижки)
# - low_price_leader (лідер низьких цін)
# - premium_pricing (преміум ціноутворення)
# - market_based_pricing (ринкове ціноутворення)

print(f"Впевненість: {strategy['confidence']}%")
print(f"Товарів зі знижками: {strategy['statistics']['discount_rate_percent']}%")
```

#### Рекомендації по оптимізації
```python
recommendations = analyzer.get_price_optimization_recommendations(competitor_id=1)

for rec in recommendations:
    print(f"[{rec['priority']}] {rec['title']}")
    print(f"   {rec['description']}")
```

### API Endpoints

```bash
# Аналіз трендів
GET /api/competitor/1/price-analysis?days=30

# Стратегія ціноутворення
GET /api/competitor/1/pricing-strategy

# Порівняння цін
GET /api/price-comparison?category=electronics

# Рекомендації
GET /api/competitor/1/price-recommendations
```

---

## 🔍 2. Виявлення Змін (ChangeDetector)

### Можливості

#### Виявлення нових продуктів
```python
from src.utils.change_detector import ChangeDetector

detector = ChangeDetector(db)

# Нові продукти за останні 24 години
new_products = detector.detect_new_products(competitor_id=1, hours=24)

for product in new_products:
    print(f"Новий товар: {product['name']}")
    print(f"  Ціна: {product['price']} {product['currency']}")
    print(f"  Категорія: {product['category']}")
    print(f"  Додано: {product['first_seen']}")
```

#### Виявлення нових акцій
```python
new_promotions = detector.detect_new_promotions(competitor_id=1, hours=24)

for promo in new_promotions:
    print(f"Нова акція: {promo['title']}")
    print(f"  Тип: {promo['promotion_type']}")
    print(f"  Знижка: {promo['discount_value']}% {promo['discount_type']}")
```

#### Відстеження змін цін
```python
# Мінімальна зміна 5% для виявлення
increases, decreases = detector.detect_price_changes(
    competitor_id=1, 
    hours=24,
    min_change_percent=5.0
)

print(f"Підвищень цін: {len(increases)}")
for change in increases[:5]:
    print(f"  {change['name']}: +{change['change_percent']}%")

print(f"Знижень цін: {len(decreases)}")
for change in decreases[:5]:
    print(f"  {change['name']}: {change['change_percent']}%")
```

#### Моніторинг наявності
```python
back_in_stock, out_of_stock = detector.detect_stock_changes(competitor_id=1, hours=24)

print(f"З'явилось в наявності: {len(back_in_stock)}")
print(f"Закінчилось: {len(out_of_stock)}")
```

#### Загальна інформація про зміни
```python
# По всіх конкурентах
summary = detector.get_changes_summary(hours=24)

# Або по конкретному
summary = detector.get_changes_summary(competitor_id=1, hours=24)

for comp_changes in summary['changes']:
    print(f"\n{comp_changes['competitor_name']}:")
    print(f"  Нових товарів: {comp_changes['summary']['total_new_products']}")
    print(f"  Нових акцій: {comp_changes['summary']['total_new_promotions']}")
    print(f"  Підвищень цін: {comp_changes['summary']['total_price_increases']}")
    print(f"  Знижень цін: {comp_changes['summary']['total_price_decreases']}")
```

### API Endpoints

```bash
# Зміни по конкуренту
GET /api/competitor/1/changes?hours=24

# Загальна інформація
GET /api/changes-summary?hours=24

# По всіх конкурентах
GET /api/changes-summary?competitor_id=1&hours=24
```

---

## 🤖 3. LLM Інтеграція (LLMAnalyzer)

### Налаштування Ollama

```bash
# Запустити Ollama (вже в docker-compose.yml)
docker-compose up -d ollama

# Завантажити модель
docker exec -it ollama-intelligence ollama pull llama2
# або інші моделі: mistral, codellama, etc.
```

### Можливості

#### SWOT-аналіз
```python
from src.utils.llm_analyzer import LLMAnalyzer

analyzer = LLMAnalyzer(db, ollama_host="http://localhost:11434")

# Генерація SWOT-аналізу
swot = analyzer.generate_competitor_swot(
    competitor_id=1,
    model="llama2"  # опціонально
)

print(swot['summary'])
print("\nСильні сторони:")
for strength in swot['strengths']:
    print(f"  • {strength}")

print("\nСлабкі сторони:")
for weakness in swot['weaknesses']:
    print(f"  • {weakness}")

print("\nМожливості:")
for opportunity in swot['opportunities']:
    print(f"  • {opportunity}")

print("\nЗагрози:")
for threat in swot['threats']:
    print(f"  • {threat}")

print("\nРекомендації:")
for rec in swot['recommendations']:
    print(f"  • {rec}")
```

#### Рекомендації щодо контенту
```python
recommendations = analyzer.generate_content_recommendations(
    competitor_id=1,
    target_audience="B2C",
    model="llama2"
)

print(recommendations['recommendations'])
```

#### Отримання останнього аналізу
```python
# Без повторної генерації
latest = analyzer.get_latest_analysis(competitor_id=1, analysis_type='swot')

if latest:
    print(f"Аналіз від {latest['created_at']}")
    print(f"Модель: {latest['model_used']}")
    print(f"Час обробки: {latest['processing_time']}с")
```

### API Endpoints

```bash
# Генерація SWOT (асинхронно)
POST /api/competitor/1/swot-analysis
{
  "model": "llama2"
}
# Відповідь: {"job_id": "uuid"}

# Перевірка статусу
GET /api/scan/{job_id}

# Отримати останній SWOT
GET /api/competitor/1/swot-analysis

# Рекомендації контенту
POST /api/competitor/1/content-recommendations
{
  "target_audience": "B2C",
  "model": "llama2"
}
```

---

## 🤝 4. Етичний Скрейпінг (RobotsParser & SmartCrawler)

### Можливості

#### Перевірка дозволу на сканування
```python
from src.utils.robots_parser import RobotsParser, SmartCrawler

parser = RobotsParser(user_agent="CompetitiveIntelligenceBot/1.0")

# Перевірити чи можна сканувати URL
url = "https://example.com/products"
if parser.can_fetch(url):
    print("✓ Дозволено сканувати")
else:
    print("✗ Заборонено robots.txt")
```

#### Отримання інформації з robots.txt
```python
info = parser.get_robots_info("https://example.com")

print(f"Crawl delay: {info['crawl_delay']}с")
print(f"Sitemaps: {info['sitemaps']}")
print(f"Заборонені шляхи: {info['disallowed_paths']}")
print(f"Дозволені шляхи: {info['allowed_paths']}")
```

#### Перевірка meta robots
```python
html_content = "<html>...</html>"
meta_rules = parser.respect_meta_robots(html_content)

if meta_rules['noindex']:
    print("⚠ Сторінка має noindex - не індексувати")
if meta_rules['nofollow']:
    print("⚠ Сторінка має nofollow - не переходити по посиланнях")
```

#### Розумний краулер
```python
crawler = SmartCrawler(user_agent="CompetitiveIntelligenceBot/1.0")

# Комплексна перевірка
if crawler.should_crawl(url, html_content):
    # Отримати рекомендовану затримку
    delay = crawler.get_crawl_delay(url)
    print(f"Використовувати затримку: {delay}с")
    
    # Виконати сканування
    # ...
```

---

## 📈 Використання в проєкті

### Інтеграція в існуючі скрейпери

```python
from src.base_scraper import BaseScraper
from src.utils.robots_parser import SmartCrawler
import time

class MyEnhancedScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.crawler = SmartCrawler()
    
    def scrape(self, url: str):
        # Перевірка дозволу
        if not self.crawler.should_crawl(url):
            self.logger.warning(f"Сканування заборонено: {url}")
            return []
        
        # Отримання затримки
        delay = self.crawler.get_crawl_delay(url)
        
        # Сканування з затримкою
        driver = self.get_driver()
        driver.get(url)
        
        # Перевірка meta robots
        html = driver.page_source
        if not self.crawler.should_crawl(url, html):
            self.logger.warning(f"Meta robots забороняє індексацію")
            return []
        
        # ... логіка скрейпінга ...
        
        time.sleep(delay)
        return results
```

### Автоматичний аналіз після сканування

```python
from src.utils.price_analyzer import PriceAnalyzer
from src.utils.change_detector import ChangeDetector

def post_scan_analysis(competitor_id: int, db):
    """Виконати аналіз після сканування"""
    
    # Виявити зміни
    detector = ChangeDetector(db)
    new_products = detector.detect_new_products(competitor_id, hours=24)
    price_increases, price_decreases = detector.detect_price_changes(competitor_id, hours=24)
    
    # Аналіз цін
    analyzer = PriceAnalyzer(db)
    strategy = analyzer.detect_pricing_strategy(competitor_id)
    recommendations = analyzer.get_price_optimization_recommendations(competitor_id)
    
    # Формування звіту
    report = {
        'new_products_count': len(new_products),
        'price_changes': {
            'increases': len(price_increases),
            'decreases': len(price_decreases)
        },
        'pricing_strategy': strategy['strategy'],
        'recommendations': recommendations
    }
    
    return report
```

---

## 🔧 Налаштування

### Конфігурація в config.yaml

```yaml
# Ollama для LLM аналізу
ollama:
  host: "http://ollama:11434"
  default_model: "llama2"

# Параметри скрейпінга
scraping:
  user_agent: "CompetitiveIntelligenceBot/1.0"
  respect_robots_txt: true
  default_crawl_delay: 1.0  # секунди
  
# Аналітика
analytics:
  price_analysis:
    min_change_percent: 5.0  # Мінімальна зміна для виявлення
    trend_days: 30  # Кількість днів для аналізу трендів
  
  change_detection:
    check_hours: 24  # Період для виявлення змін
```

---

## 📝 Приклади API запитів

### cURL

```bash
# Отримати зміни за 48 годин
curl "http://localhost:5000/api/competitor/1/changes?hours=48"

# Порівняння цін по категорії
curl "http://localhost:5000/api/price-comparison?category=electronics"

# Генерація SWOT
curl -X POST "http://localhost:5000/api/competitor/1/swot-analysis" \
  -H "Content-Type: application/json" \
  -d '{"model": "llama2"}'

# Рекомендації по цінах
curl "http://localhost:5000/api/competitor/1/price-recommendations"
```

### Python (requests)

```python
import requests

BASE_URL = "http://localhost:5000"

# Отримати аналіз цін
response = requests.get(f"{BASE_URL}/api/competitor/1/price-analysis?days=30")
trends = response.json()

# Виявити зміни
response = requests.get(f"{BASE_URL}/api/competitor/1/changes?hours=24")
changes = response.json()

# Згенерувати SWOT
response = requests.post(
    f"{BASE_URL}/api/competitor/1/swot-analysis",
    json={"model": "llama2"}
)
job_id = response.json()['job_id']

# Перевірити статус
response = requests.get(f"{BASE_URL}/api/scan/{job_id}")
status = response.json()
```

---

## 🎯 Наступні кроки

Рекомендовані покращення для майбутніх версій:

1. **Візуалізація даних**
   - Інтерактивні графіки трендів цін
   - Дашборд з ключовими метриками
   - Експорт звітів у PDF/Excel

2. **Розширення функціонального тестування**
   - Тестування пошуку на сайті
   - Симуляція додавання в кошик
   - Тестування відновлення паролю

3. **Додаткові модулі**
   - Traffic & Ranking (інтеграція з SimilarWeb API)
   - Social Media моніторинг
   - Technology Stack detection

4. **Продуктивність**
   - Асинхронний збір даних (asyncio + aiohttp)
   - Паралельне сканування з пулом воркерів
   - Кешування частих запитів

---

## 📚 Документація модулів

- [`PriceAnalyzer`](src/utils/price_analyzer.py) - Аналіз цінової політики
- [`ChangeDetector`](src/utils/change_detector.py) - Виявлення змін
- [`LLMAnalyzer`](src/utils/llm_analyzer.py) - LLM інтеграція
- [`RobotsParser`](src/utils/robots_parser.py) - Обробка robots.txt

---

## 🐛 Виправлені помилки

1. **IndentationError в run_intelligence.py**
   - Виправлено невірний відступ у рядку 254
   - Тепер скрипт запускається без помилок

2. **OpenTelemetry Connection Error**
   - Відключено експорт телеметрії в Selenium Hub
   - Додано змінні середовища для вимкнення OTEL

---

## 🤝 Внесок у проєкт

Якщо ви хочете покращити ці модулі:

1. Fork репозиторій
2. Створіть feature branch
3. Внесіть зміни
4. Створіть Pull Request

---

**Дата:** 2024-12-19  
**Версія:** 1.0.0  
**Автор:** Competitive Intelligence Team
