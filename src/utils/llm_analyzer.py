"""
Модуль для інтеграції з LLM (Ollama) для глибокого аналізу конкурентів
"""

import json
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class LLMAnalyzer:
    """Аналізатор даних за допомогою LLM"""
    
    def __init__(self, db_manager, ollama_host: str = "http://localhost:11434"):
        """
        Ініціалізація LLM аналізатора
        
        Args:
            db_manager: DatabaseManager instance
            ollama_host: URL Ollama сервера
        """
        self.db = db_manager
        self.ollama_host = ollama_host.rstrip('/')
        self.default_model = "llama2"  # Можна змінити на інші моделі
    
    def _call_ollama(
        self, 
        prompt: str, 
        model: str = None,
        system_prompt: str = None
    ) -> Optional[str]:
        """
        Виконати запит до Ollama
        
        Args:
            prompt: Текст запиту
            model: Назва моделі (якщо None - використовується default_model)
            system_prompt: Системний промт
            
        Returns:
            Відповідь від LLM або None при помилці
        """
        if model is None:
            model = self.default_model
        
        try:
            url = f"{self.ollama_host}/api/generate"
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '')
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка виклику Ollama: {e}")
            return None
        except Exception as e:
            logger.error(f"Неочікувана помилка: {e}")
            return None
    
    def generate_competitor_swot(
        self, 
        competitor_id: int,
        model: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Згенерувати SWOT-аналіз конкурента
        
        Args:
            competitor_id: ID конкурента
            model: Назва LLM моделі
            
        Returns:
            Словник з SWOT-аналізом
        """
        from src.database.models import Competitor, LLMAnalysis
        
        session = self.db.Session()
        try:
            # Отримуємо дані конкурента
            competitor = session.query(Competitor).get(competitor_id)
            if not competitor:
                logger.error(f"Конкурент з ID {competitor_id} не знайдений")
                return None
            
            # Збираємо всі дані для аналізу
            seo_data = self.db.get_latest_seo_data(competitor_id)
            company_data = self.db.get_latest_company_data(competitor_id)
            products = self.db.get_products(competitor_id)
            promotions = self.db.get_active_promotions(competitor_id)
            
            # Формуємо промт
            data_summary = self._prepare_competitor_summary(
                competitor, seo_data, company_data, products, promotions
            )
            
            system_prompt = """Ти експерт з конкурентного аналізу та бізнес-стратегії. 
Твоє завдання - провести детальний SWOT-аналіз компанії на основі наданих даних.
Відповідай структуровано у форматі JSON з такими ключами:
{
  "summary": "Короткий загальний висновок",
  "strengths": ["сильна сторона 1", "сильна сторона 2", ...],
  "weaknesses": ["слабка сторона 1", "слабка сторона 2", ...],
  "opportunities": ["можливість 1", "можливість 2", ...],
  "threats": ["загроза 1", "загроза 2", ...],
  "recommendations": ["рекомендація 1", "рекомендація 2", ...]
}"""
            
            prompt = f"""Проведи SWOT-аналіз для наступного конкурента:

{data_summary}

Проаналізуй всі аспекти бізнесу та надай детальний SWOT-аналіз у форматі JSON."""
            
            start_time = datetime.utcnow()
            
            response = self._call_ollama(prompt, model, system_prompt)
            
            if not response:
                return None
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Парсимо JSON з відповіді
            try:
                # Витягуємо JSON з відповіді (може бути обгорнутий у текст)
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    swot_data = json.loads(json_str)
                else:
                    # Якщо JSON не знайдено, створюємо структуру з текстової відповіді
                    swot_data = {
                        "summary": response[:500],
                        "strengths": [],
                        "weaknesses": [],
                        "opportunities": [],
                        "threats": [],
                        "recommendations": []
                    }
            except json.JSONDecodeError:
                logger.warning("Не вдалось розпарсити JSON, зберігаємо як текст")
                swot_data = {
                    "summary": response[:500],
                    "strengths": [],
                    "weaknesses": [],
                    "opportunities": [],
                    "threats": [],
                    "recommendations": []
                }
            
            # Зберігаємо результат в БД
            analysis = LLMAnalysis(
                competitor_id=competitor_id,
                analysis_type='swot',
                summary=swot_data.get('summary', ''),
                strengths=swot_data.get('strengths', []),
                weaknesses=swot_data.get('weaknesses', []),
                opportunities=swot_data.get('opportunities', []),
                threats=swot_data.get('threats', []),
                recommendations=swot_data.get('recommendations', []),
                full_analysis=response,
                model_used=model or self.default_model,
                processing_time=processing_time
            )
            
            session.add(analysis)
            session.commit()
            
            logger.info(
                f"SWOT-аналіз для '{competitor.name}' успішно створено "
                f"(час: {processing_time:.2f}с)"
            )
            
            return {
                'analysis_id': analysis.id,
                'competitor_name': competitor.name,
                'summary': swot_data.get('summary'),
                'strengths': swot_data.get('strengths', []),
                'weaknesses': swot_data.get('weaknesses', []),
                'opportunities': swot_data.get('opportunities', []),
                'threats': swot_data.get('threats', []),
                'recommendations': swot_data.get('recommendations', []),
                'model_used': model or self.default_model,
                'processing_time': processing_time,
                'created_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Помилка створення SWOT-аналізу: {e}", exc_info=True)
            session.rollback()
            return None
        finally:
            session.close()
    
    def _prepare_competitor_summary(
        self,
        competitor,
        seo_data,
        company_data,
        products,
        promotions
    ) -> str:
        """Підготувати резюме даних конкурента для LLM"""
        
        summary_parts = [
            f"Назва компанії: {competitor.name}",
            f"Сайт: {competitor.url}",
            ""
        ]
        
        # SEO дані
        if seo_data:
            summary_parts.append("SEO інформація:")
            summary_parts.append(f"  - Title: {seo_data.title or 'N/A'}")
            summary_parts.append(f"  - Meta Description: {seo_data.meta_description or 'N/A'}")
            summary_parts.append(f"  - Внутрішніх посилань: {seo_data.internal_links_count or 0}")
            summary_parts.append(f"  - Зовнішніх посилань: {seo_data.external_links_count or 0}")
            summary_parts.append(f"  - Час завантаження: {seo_data.page_load_time or 'N/A'}с")
            summary_parts.append("")
        
        # Контактні дані
        if company_data:
            summary_parts.append("Контактна інформація:")
            if company_data.emails:
                summary_parts.append(f"  - Email(и): {', '.join(company_data.emails)}")
            if company_data.phones:
                summary_parts.append(f"  - Телефон(и): {', '.join(company_data.phones)}")
            
            socials = []
            if company_data.facebook_url:
                socials.append("Facebook")
            if company_data.instagram_url:
                socials.append("Instagram")
            if company_data.linkedin_url:
                socials.append("LinkedIn")
            
            if socials:
                summary_parts.append(f"  - Соціальні мережі: {', '.join(socials)}")
            summary_parts.append("")
        
        # Товари/послуги
        if products:
            summary_parts.append(f"Товари/послуги: {len(products)} позицій")
            
            # Категорії
            categories = set(p.category for p in products if p.category)
            if categories:
                summary_parts.append(f"  - Категорії: {', '.join(list(categories)[:5])}")
            
            # Цінові діапазони
            prices = [p.price for p in products if p.price]
            if prices:
                summary_parts.append(f"  - Ціновий діапазон: {min(prices):.2f} - {max(prices):.2f}")
                avg_price = sum(prices) / len(prices)
                summary_parts.append(f"  - Середня ціна: {avg_price:.2f}")
            
            # Наявність
            in_stock = sum(1 for p in products if p.in_stock)
            summary_parts.append(f"  - В наявності: {in_stock}/{len(products)}")
            summary_parts.append("")
        
        # Акції
        if promotions:
            summary_parts.append(f"Активні акції: {len(promotions)}")
            for promo in promotions[:3]:  # Показуємо перші 3
                summary_parts.append(f"  - {promo.title} ({promo.promotion_type})")
            summary_parts.append("")
        
        return "\n".join(summary_parts)
    
    def generate_content_recommendations(
        self,
        competitor_id: int,
        target_audience: str = "B2C",
        model: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Згенерувати рекомендації щодо контенту
        
        Args:
            competitor_id: ID конкурента
            target_audience: Цільова аудиторія (B2C, B2B, etc.)
            model: Назва LLM моделі
            
        Returns:
            Словник з рекомендаціями
        """
        from src.database.models import Competitor
        
        session = self.db.Session()
        try:
            competitor = session.query(Competitor).get(competitor_id)
            if not competitor:
                return None
            
            # Отримуємо SEO дані для семантичного ядра
            seo_data = self.db.get_latest_seo_data(competitor_id)
            
            if not seo_data or not seo_data.semantic_core:
                logger.warning("Немає семантичного ядра для аналізу")
                return None
            
            semantic_core = seo_data.semantic_core
            
            system_prompt = """Ти експерт з контент-маркетингу та SEO. 
Проаналізуй семантичне ядро конкурента та запропонуй стратегію контенту."""
            
            prompt = f"""На основі семантичного ядра конкурента "{competitor.name}":

{json.dumps(semantic_core, indent=2, ensure_ascii=False)}

Цільова аудиторія: {target_audience}

Запропонуй:
1. Топ-10 контентних тем для блогу
2. Ключові слова для фокусу
3. Gaps в контенті конкурента (що можна покращити)
4. Рекомендації щодо структури контенту

Відповідай у форматі JSON."""
            
            response = self._call_ollama(prompt, model, system_prompt)
            
            if not response:
                return None
            
            return {
                'competitor_name': competitor.name,
                'recommendations': response,
                'target_audience': target_audience,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        finally:
            session.close()
    
    def get_latest_analysis(
        self,
        competitor_id: int,
        analysis_type: str = 'swot'
    ) -> Optional[Dict[str, Any]]:
        """
        Отримати останній аналіз
        
        Args:
            competitor_id: ID конкурента
            analysis_type: Тип аналізу
            
        Returns:
            Словник з аналізом
        """
        from src.database.models import LLMAnalysis, Competitor
        
        session = self.db.Session()
        try:
            analysis = session.query(LLMAnalysis).filter(
                LLMAnalysis.competitor_id == competitor_id,
                LLMAnalysis.analysis_type == analysis_type
            ).order_by(
                LLMAnalysis.created_at.desc()
            ).first()
            
            if not analysis:
                return None
            
            competitor = session.query(Competitor).get(competitor_id)
            
            return {
                'analysis_id': analysis.id,
                'competitor_name': competitor.name if competitor else None,
                'analysis_type': analysis.analysis_type,
                'summary': analysis.summary,
                'strengths': analysis.strengths,
                'weaknesses': analysis.weaknesses,
                'opportunities': analysis.opportunities,
                'threats': analysis.threats,
                'recommendations': analysis.recommendations,
                'model_used': analysis.model_used,
                'processing_time': analysis.processing_time,
                'created_at': analysis.created_at.isoformat()
            }
            
        finally:
            session.close()
