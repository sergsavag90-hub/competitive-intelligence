# 🤖 ПРОМПТ ДЛЯ GITHUB CODEX

## Автоматична інтеграція Competitive Intelligence Tool в проєкт selenium-grid-proxmox-v3

---

## 📋 ЗАВДАННЯ

Інтегрувати повнофункціональний інструмент конкурентної розвідки **competitive-intelligence** в існуючий проєкт **selenium-grid-proxmox-v3**.

---

## 🎯 ЩО ПОТРІБНО ЗРОБИТИ

### 1. **Створити структуру папок та файлів**

Створіть в корені проєкту `selenium-grid-proxmox-v3` нову папку `competitive-intelligence/` з такою структурою:

```
competitive-intelligence/
├── src/
│   ├── __init__.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── selenium_helper.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── db_manager.py
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── seo_scraper.py
│   │   ├── company_scraper.py
│   │   ├── product_scraper.py
│   │   └── promotion_scraper.py
│   ├── analyzers/
│   │   ├── __init__.py
│   │   └── ollama_analyzer.py
│   └── web/
│       ├── __init__.py
│       ├── app.py
│       └── templates/
│           ├── index.html
│           ├── competitors.html
│           ├── seo.html
│           ├── products.html
│           └── promotions.html
├── data/
├── exports/
├── logs/
├── README.md
├── requirements.txt
├── config.yaml
├── docker-compose.intelligence.yml
├── Dockerfile
└── run_intelligence.py
```

### 2. **Скопіювати всі файли з наданих прикладів**

Я вже створив наступні файли, які потрібно помістити у відповідні місця:

#### Кореневі файли:
- `README.md` - Повна документація проєкту
- `requirements.txt` - Python залежності
- `config.yaml` - Конфігураційний файл
- `run_intelligence.py` - Головний запускаючий скрипт
- `Dockerfile` - Docker образ
- `docker-compose.intelligence.yml` - Docker Compose конфігурація

#### Модулі:
- `src/__init__.py`
- `src/utils/__init__.py`
- `src/utils/config.py` - Управління конфігурацією
- `src/utils/selenium_helper.py` - Допоміжні функції Selenium
- `src/database/__init__.py`
- `src/database/models.py` - SQLAlchemy моделі
- `src/database/db_manager.py` - Менеджер бази даних
- `src/scrapers/__init__.py`
- `src/scrapers/seo_scraper.py` - SEO збір
- `src/scrapers/company_scraper.py` - Контактні дані
- `src/scrapers/product_scraper.py` - Товари/послуги
- `src/scrapers/promotion_scraper.py` - Акції та промо

### 3. **Створити відсутні компоненти**

Створіть наступні файли, яких я ще не створив:

#### `src/analyzers/ollama_analyzer.py`:
```python
"""
Ollama LLM Analyzer - аналіз даних через локальну LLM
"""

import logging
import json
from typing import Dict, Any, List
import requests

from ..utils.config import config

logger = logging.getLogger(__name__)


class OllamaAnalyzer:
    """Клас для аналізу через Ollama LLM"""
    
    def __init__(self):
        self.host = config.ollama_host
        self.model = config.ollama_model
        self.enabled = config.ollama_enabled
    
    def analyze_competitor(self, competitor_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Проаналізувати конкурента"""
        if not self.enabled:
            logger.warning("Ollama вимкнено в конфігурації")
            return {}
        
        try:
            prompt = self._build_analysis_prompt(competitor_name, data)
            response = self._call_ollama(prompt)
            
            return self._parse_analysis(response)
        
        except Exception as e:
            logger.error(f"Помилка аналізу Ollama: {e}")
            return {}
    
    def _build_analysis_prompt(self, name: str, data: Dict) -> str:
        """Побудувати промпт для аналізу"""
        prompt = f"""
Проаналізуй інформацію про конкурента "{name}".

Дані:
{json.dumps(data, ensure_ascii=False, indent=2)}

Надай детальний аналіз у форматі:

1. СИЛЬНІ СТОРОНИ (3-5 пунктів)
2. СЛАБКІ СТОРОНИ (3-5 пунктів)
3. МОЖЛИВОСТІ (3-5 пунктів)
4. ЗАГРОЗИ (3-5 пунктів)
5. РЕКОМЕНДАЦІЇ (5-7 конкретних кроків)

Будь конкретним та практичним.
"""
        return prompt
    
    def _call_ollama(self, prompt: str) -> str:
        """Викликати Ollama API"""
        url = f"{self.host}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        
        return response.json().get('response', '')
    
    def _parse_analysis(self, response: str) -> Dict[str, Any]:
        """Парсити відповідь LLM"""
        # Простий парсинг на основі секцій
        analysis = {
            'strengths': [],
            'weaknesses': [],
            'opportunities': [],
            'threats': [],
            'recommendations': [],
            'full_analysis': response
        }
        
        # Тут можна додати більш складний парсинг
        
        return analysis
```

#### `src/web/__init__.py`:
```python
"""Web interface package"""
```

#### `src/web/app.py`:
```python
"""
Flask веб-додаток для перегляду даних конкурентної розвідки
"""

import logging
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sys
from pathlib import Path

# Додаємо src до шляху
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.config import config
from src.database.db_manager import DatabaseManager

# Ініціалізація Flask
app = Flask(__name__)
CORS(app)

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database
db = DatabaseManager()


@app.route('/')
def index():
    """Головна сторінка"""
    return render_template('index.html')


@app.route('/api/competitors')
def get_competitors():
    """API: Список конкурентів"""
    competitors = db.get_all_competitors()
    
    data = []
    for comp in competitors:
        stats = db.get_competitor_stats(comp.id)
        data.append({
            'id': comp.id,
            'name': comp.name,
            'url': comp.url,
            'enabled': comp.enabled,
            'priority': comp.priority,
            'stats': stats
        })
    
    return jsonify(data)


@app.route('/api/competitor/<int:competitor_id>/seo')
def get_seo_data(competitor_id):
    """API: SEO дані"""
    seo_data = db.get_latest_seo_data(competitor_id)
    
    if not seo_data:
        return jsonify({'error': 'No data'}), 404
    
    return jsonify({
        'title': seo_data.title,
        'meta_description': seo_data.meta_description,
        'h1_tags': seo_data.h1_tags,
        'h2_tags': seo_data.h2_tags,
        'internal_links_count': seo_data.internal_links_count,
        'external_links_count': seo_data.external_links_count,
        'page_load_time': seo_data.page_load_time,
        'collected_at': seo_data.collected_at.isoformat()
    })


@app.route('/api/competitor/<int:competitor_id>/company')
def get_company_data(competitor_id):
    """API: Контактні дані"""
    company_data = db.get_latest_company_data(competitor_id)
    
    if not company_data:
        return jsonify({'error': 'No data'}), 404
    
    return jsonify({
        'emails': company_data.emails,
        'phones': company_data.phones,
        'addresses': company_data.addresses,
        'facebook_url': company_data.facebook_url,
        'instagram_url': company_data.instagram_url,
        'linkedin_url': company_data.linkedin_url,
        'twitter_url': company_data.twitter_url,
        'collected_at': company_data.collected_at.isoformat()
    })


@app.route('/api/competitor/<int:competitor_id>/products')
def get_products(competitor_id):
    """API: Товари"""
    products = db.get_products(competitor_id)
    
    data = [{
        'id': p.id,
        'name': p.name,
        'price': p.price,
        'currency': p.currency,
        'url': p.url,
        'in_stock': p.in_stock,
        'category': p.category,
        'main_image': p.main_image,
    } for p in products]
    
    return jsonify(data)


@app.route('/api/competitor/<int:competitor_id>/promotions')
def get_promotions(competitor_id):
    """API: Акції"""
    promotions = db.get_active_promotions(competitor_id)
    
    data = [{
        'id': p.id,
        'title': p.title,
        'description': p.description,
        'promotion_type': p.promotion_type,
        'discount_value': p.discount_value,
        'discount_type': p.discount_type,
        'start_date': p.start_date.isoformat() if p.start_date else None,
        'end_date': p.end_date.isoformat() if p.end_date else None,
    } for p in promotions]
    
    return jsonify(data)


if __name__ == '__main__':
    app.run(
        host=config.web_host,
        port=config.web_port,
        debug=config.get('web.debug', False)
    )
```

#### `src/web/templates/index.html`:
```html
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Competitive Intelligence Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        
        h1 {
            color: #333;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-align: center;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .stat-card h3 {
            font-size: 1em;
            margin-bottom: 10px;
            opacity: 0.9;
        }
        
        .stat-card .value {
            font-size: 2.5em;
            font-weight: bold;
        }
        
        .competitors-list {
            margin-top: 30px;
        }
        
        .competitor-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 15px;
            border-left: 5px solid #667eea;
            transition: transform 0.2s;
        }
        
        .competitor-card:hover {
            transform: translateX(5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .competitor-name {
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }
        
        .competitor-url {
            color: #667eea;
            text-decoration: none;
            font-size: 0.9em;
        }
        
        .competitor-stats {
            display: flex;
            gap: 20px;
            margin-top: 15px;
        }
        
        .stat-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .badge {
            background: #667eea;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.9em;
        }
        
        .loading {
            text-align: center;
            padding: 50px;
            font-size: 1.2em;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🕵️ Competitive Intelligence Dashboard</h1>
        
        <div class="stats-grid" id="statsGrid">
            <div class="stat-card">
                <h3>Всього конкурентів</h3>
                <div class="value" id="totalCompetitors">-</div>
            </div>
            <div class="stat-card">
                <h3>Товарів відстежується</h3>
                <div class="value" id="totalProducts">-</div>
            </div>
            <div class="stat-card">
                <h3>Активних акцій</h3>
                <div class="value" id="totalPromotions">-</div>
            </div>
            <div class="stat-card">
                <h3>Останнє оновлення</h3>
                <div class="value" id="lastUpdate" style="font-size: 1.2em;">-</div>
            </div>
        </div>
        
        <div class="competitors-list">
            <h2>Конкуренти</h2>
            <div id="competitorsList" class="loading">Завантаження...</div>
        </div>
    </div>
    
    <script>
        async function loadData() {
            try {
                const response = await fetch('/api/competitors');
                const competitors = await response.json();
                
                let totalProducts = 0;
                let totalPromotions = 0;
                
                competitors.forEach(comp => {
                    totalProducts += comp.stats.total_products || 0;
                    totalPromotions += comp.stats.total_promotions || 0;
                });
                
                document.getElementById('totalCompetitors').textContent = competitors.length;
                document.getElementById('totalProducts').textContent = totalProducts;
                document.getElementById('totalPromotions').textContent = totalPromotions;
                document.getElementById('lastUpdate').textContent = new Date().toLocaleDateString('uk-UA');
                
                const listHtml = competitors.map(comp => `
                    <div class="competitor-card">
                        <div class="competitor-name">${comp.name}</div>
                        <a href="${comp.url}" target="_blank" class="competitor-url">${comp.url}</a>
                        <div class="competitor-stats">
                            <div class="stat-item">
                                <span class="badge">🛒 ${comp.stats.total_products || 0} товарів</span>
                            </div>
                            <div class="stat-item">
                                <span class="badge">🎁 ${comp.stats.total_promotions || 0} акцій</span>
                            </div>
                            <div class="stat-item">
                                <span class="badge">${comp.stats.has_seo_data ? '✓ SEO' : '✗ SEO'}</span>
                            </div>
                        </div>
                    </div>
                `).join('');
                
                document.getElementById('competitorsList').innerHTML = listHtml;
                
            } catch (error) {
                console.error('Error:', error);
                document.getElementById('competitorsList').innerHTML = 
                    '<div class="loading">Помилка завантаження даних</div>';
            }
        }
        
        loadData();
    </script>
</body>
</html>
```

### 4. **Оновити головний README.md проєкту**

Додайте в існуючий `README.md` проєкту `selenium-grid-proxmox-v3` новий розділ:

```markdown
## 🕵️ Competitive Intelligence Tool

Проєкт тепер включає потужний інструмент для конкурентної розвідки!

### Можливості:
- 📊 SEO аналіз конкурентів
- 🏢 Збір контактних даних
- 🛒 Моніторинг товарів та цін
- 🎁 Відстеження акцій
- 🧠 AI-аналіз через Ollama
- 📈 Веб-дашборд

### Швидкий старт:

```bash
# Запуск з Docker
docker compose -f docker-compose.yml -f competitive-intelligence/docker-compose.intelligence.yml up -d

# Доступ до веб-інтерфейсу
open http://localhost:5000

# Запуск аналізу вручну
cd competitive-intelligence
python run_intelligence.py --full
```

Детальна документація: [competitive-intelligence/README.md](competitive-intelligence/README.md)
```

### 5. **Налаштувати інтеграцію**

Переконайтеся що:
- Всі папки `data/`, `exports/`, `logs/` створені
- Файл `config.yaml` містить правильний `selenium_hub_url`
- Docker network `selenium-grid` існує або буде створена

### 6. **Створити Makefile команди** (опціонально)

Додайте в існуючий `Makefile` проєкту:

```makefile
# Competitive Intelligence
ci-start:
	docker compose -f competitive-intelligence/docker-compose.intelligence.yml up -d

ci-stop:
	docker compose -f competitive-intelligence/docker-compose.intelligence.yml down

ci-logs:
	docker compose -f competitive-intelligence/docker-compose.intelligence.yml logs -f

ci-scan:
	cd competitive-intelligence && python run_intelligence.py --full
```

---

## ✅ ПЕРЕВІРКА РОБОТИ

Після виконання всіх кроків, перевірте:

1. **Структура файлів**:
   ```bash
   ls -la competitive-intelligence/
   ls -la competitive-intelligence/src/
   ```

2. **Запуск вручну**:
   ```bash
   cd competitive-intelligence
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python run_intelligence.py --help
   ```

3. **Запуск Docker**:
   ```bash
   docker compose -f competitive-intelligence/docker-compose.intelligence.yml up -d
   docker compose -f competitive-intelligence/docker-compose.intelligence.yml logs
   ```

4. **Веб-інтерфейс**:
   Відкрийте http://localhost:5000 в браузері

---

## 📝 ВАЖЛИВІ ПРИМІТКИ

1. **Всі файли вже створені** - просто скопіюйте їх у відповідні місця
2. **Перевірте config.yaml** - встановіть правильний URL Selenium Grid
3. **База даних** створюється автоматично при першому запуску
4. **Ollama** опціонально - можна відключити в `config.yaml`

---

## 🎯 РЕЗУЛЬТАТ

Після виконання цих інструкцій ви отримаєте:

✅ Повністю робочий інструмент конкурентної розвідки  
✅ Інтеграцію з Selenium Grid  
✅ Веб-інтерфейс для перегляду даних  
✅ Автоматичне сканування через cron  
✅ API для доступу до даних  
✅ LLM аналіз через Ollama  

---

**Версія**: 1.0.0  
**Автор**: Bot-IpMan  
**Дата**: 2025-01-12
