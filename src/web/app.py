"""
Flask web application for presenting competitive intelligence data.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from threading import Thread
from uuid import uuid4

# Ensure the project root is importable when running inside Docker
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.database.db_manager import DatabaseManager  # noqa: E402
from src.utils.config import config  # noqa: E402
from src.utils.price_analyzer import PriceAnalyzer  # noqa: E402
from src.utils.change_detector import ChangeDetector  # noqa: E402
from src.utils.llm_analyzer import LLMAnalyzer  # noqa: E402
from run_intelligence import CompetitiveIntelligence  # noqa: E402

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=getattr(logging, config.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)

db = DatabaseManager()
price_analyzer = PriceAnalyzer(db)
change_detector = ChangeDetector(db)
llm_analyzer = LLMAnalyzer(db, config.get('ollama.host', 'http://ollama:11434'))
scan_jobs: Dict[str, Dict[str, Any]] = {}


def serialize_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Convert database stats object to JSON serializable dict."""
    last_scan = stats.get('last_scan')
    return {
        'total_products': stats.get('total_products', 0),
        'total_promotions': stats.get('total_promotions', 0),
        'has_seo_data': stats.get('has_seo_data', False),
        'has_company_data': stats.get('has_company_data', False),
        'last_scan_at': (
            last_scan.completed_at.isoformat()
            if last_scan and last_scan.completed_at
            else None
        ),
    }


@app.route('/')
def index():
    """Serve dashboard."""
    return render_template('index.html')

@app.route('/health')
def health():
    """Healthcheck endpoint for Docker."""
    return jsonify({'status': 'ok'}), 200


@app.route('/api/competitors')
def get_competitors():
    """Return list of competitors with aggregated stats."""
    competitors = db.get_all_competitors(enabled_only=False)
    payload: List[Dict[str, Any]] = []

    for competitor in competitors:
        stats = db.get_competitor_stats(competitor.id) or {}
        payload.append({
            'id': competitor.id,
            'name': competitor.name,
            'url': competitor.url,
            'enabled': competitor.enabled,
            'priority': competitor.priority,
            'created_at': competitor.created_at.isoformat() if competitor.created_at else None,
            'stats': serialize_stats(stats),
        })

    return jsonify(payload)


@app.route('/api/competitor/<int:competitor_id>/seo')
def get_seo_data(competitor_id: int):
    """Return SEO snapshot for competitor."""
    seo_data = db.get_latest_seo_data(competitor_id)
    if not seo_data:
        return jsonify({'error': 'No data'}), 404

    return jsonify({
        'title': seo_data.title,
        'meta_description': seo_data.meta_description,
        'meta_keywords': seo_data.meta_keywords,
        'h1_tags': seo_data.h1_tags,
        'h2_tags': seo_data.h2_tags,
        'robots_txt': seo_data.robots_txt,
        'sitemap_url': seo_data.sitemap_url,
        'structured_data': seo_data.structured_data,
        'internal_links_count': seo_data.internal_links_count,
        'external_links_count': seo_data.external_links_count,
        'page_load_time': seo_data.page_load_time,
        'collected_at': seo_data.collected_at.isoformat() if seo_data.collected_at else None,
    })


@app.route('/api/competitor/<int:competitor_id>/company')
def get_company_data(competitor_id: int):
    """Return company/contact data."""
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
        'youtube_url': company_data.youtube_url,
        'collected_at': (
            company_data.collected_at.isoformat()
            if company_data.collected_at else None
        ),
    })


@app.route('/api/competitor/<int:competitor_id>/products')
def get_products(competitor_id: int):
    """Return products for competitor."""
    products = db.get_products(competitor_id)
    data = [{
        'id': product.id,
        'name': product.name,
        'price': product.price,
        'currency': product.currency,
        'url': product.url,
        'category': product.category,
        'in_stock': product.in_stock,
        'main_image': product.main_image,
        'last_seen': product.last_seen.isoformat() if product.last_seen else None,
    } for product in products]

    return jsonify(data)


@app.route('/api/competitor/<int:competitor_id>/promotions')
def get_promotions(competitor_id: int):
    """Return promotions for competitor."""
    promotions = db.get_active_promotions(competitor_id)
    data = [{
        'id': promo.id,
        'title': promo.title,
        'description': promo.description,
        'promotion_type': promo.promotion_type,
        'discount_value': promo.discount_value,
        'discount_type': promo.discount_type,
        'url': promo.url,
        'start_date': promo.start_date.isoformat() if promo.start_date else None,
        'end_date': promo.end_date.isoformat() if promo.end_date else None,
    } for promo in promotions]
    return jsonify(data)

def _run_scan_job(job_id: str, url: str, scan_type: str) -> None:
    """Execute scan in background thread."""
    logger.info("Початок сканування %s (%s)", url, scan_type)
    scan_jobs[job_id] = {'status': 'running'}
    ci = CompetitiveIntelligence()
    results: Dict[str, Any] = {}
    try:
        if scan_type in ('seo', 'full'):
            results['seo'] = ci.run_seo_analysis(url)
        if scan_type in ('company', 'full'):
            results['company'] = ci.run_company_analysis(url)
        if scan_type in ('products', 'full'):
            results['products'] = ci.run_product_analysis(url)
        if scan_type in ('promotions', 'full'):
            results['promotions'] = ci.run_promotion_analysis(url)
        scan_jobs[job_id] = {'status': 'completed', 'result': results}
        logger.info("Сканування %s завершено", url)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Помилка сканування %s", url)
        scan_jobs[job_id] = {'status': 'failed', 'error': str(exc)}

@app.route('/api/scan', methods=['POST'])
def trigger_scan():
    """Start new scan job."""
    payload = request.get_json(force=True) or {}
    url = (payload.get('url') or '').strip()
    scan_type = (payload.get('scan_type') or 'full').lower()
    allowed = {'full', 'seo', 'company', 'products', 'promotions'}

    if not url:
        return jsonify({'error': 'URL обов\'язковий'}), 400
    if scan_type not in allowed:
        return jsonify({'error': 'Невідомий тип сканування'}), 400

    job_id = str(uuid4())
    scan_jobs[job_id] = {'status': 'queued'}
    thread = Thread(target=_run_scan_job, args=(job_id, url, scan_type), daemon=True)
    thread.start()

    return jsonify({'job_id': job_id})

@app.route('/api/scan/<job_id>')
def scan_status(job_id: str):
    """Return status/result for scan job."""
    job = scan_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Не знайдено'}), 404
    return jsonify(job)


# === NEW ANALYTICS ENDPOINTS ===

@app.route('/api/competitor/<int:competitor_id>/price-analysis')
def get_price_analysis(competitor_id: int):
    """Get price analysis for competitor."""
    try:
        days = request.args.get('days', default=30, type=int)
        analysis = price_analyzer.analyze_price_trends(competitor_id, days)
        return jsonify(analysis)
    except Exception as e:
        logger.exception("Error in price analysis")
        return jsonify({'error': str(e)}), 500


@app.route('/api/competitor/<int:competitor_id>/pricing-strategy')
def get_pricing_strategy(competitor_id: int):
    """Get pricing strategy analysis."""
    try:
        strategy = price_analyzer.detect_pricing_strategy(competitor_id)
        return jsonify(strategy)
    except Exception as e:
        logger.exception("Error detecting pricing strategy")
        return jsonify({'error': str(e)}), 500


@app.route('/api/price-comparison')
def get_price_comparison():
    """Compare prices across competitors."""
    try:
        category = request.args.get('category', default=None, type=str)
        comparison = price_analyzer.compare_prices_with_competitors(category)
        return jsonify(comparison)
    except Exception as e:
        logger.exception("Error in price comparison")
        return jsonify({'error': str(e)}), 500


@app.route('/api/competitor/<int:competitor_id>/price-recommendations')
def get_price_recommendations(competitor_id: int):
    """Get price optimization recommendations."""
    try:
        recommendations = price_analyzer.get_price_optimization_recommendations(competitor_id)
        return jsonify({'recommendations': recommendations})
    except Exception as e:
        logger.exception("Error generating price recommendations")
        return jsonify({'error': str(e)}), 500


@app.route('/api/competitor/<int:competitor_id>/changes')
def get_changes(competitor_id: int):
    """Get recent changes for competitor."""
    try:
        hours = request.args.get('hours', default=24, type=int)
        
        new_products = change_detector.detect_new_products(competitor_id, hours)
        new_promotions = change_detector.detect_new_promotions(competitor_id, hours)
        price_increases, price_decreases = change_detector.detect_price_changes(competitor_id, hours)
        back_in_stock, out_of_stock = change_detector.detect_stock_changes(competitor_id, hours)
        
        return jsonify({
            'period_hours': hours,
            'new_products': new_products,
            'new_promotions': new_promotions,
            'price_increases': price_increases,
            'price_decreases': price_decreases,
            'back_in_stock': back_in_stock,
            'out_of_stock': out_of_stock,
            'summary': {
                'total_new_products': len(new_products),
                'total_new_promotions': len(new_promotions),
                'total_price_increases': len(price_increases),
                'total_price_decreases': len(price_decreases),
                'total_back_in_stock': len(back_in_stock),
                'total_out_of_stock': len(out_of_stock)
            }
        })
    except Exception as e:
        logger.exception("Error detecting changes")
        return jsonify({'error': str(e)}), 500


@app.route('/api/changes-summary')
def get_changes_summary():
    """Get changes summary for all competitors."""
    try:
        hours = request.args.get('hours', default=24, type=int)
        competitor_id = request.args.get('competitor_id', default=None, type=int)
        
        summary = change_detector.get_changes_summary(competitor_id, hours)
        return jsonify(summary)
    except Exception as e:
        logger.exception("Error getting changes summary")
        return jsonify({'error': str(e)}), 500


@app.route('/api/competitor/<int:competitor_id>/swot-analysis', methods=['POST'])
def generate_swot_analysis(competitor_id: int):
    """Generate SWOT analysis using LLM."""
    try:
        data = request.get_json() or {}
        model = data.get('model', None)
        
        # Generate analysis in background thread
        job_id = str(uuid4())
        scan_jobs[job_id] = {'status': 'running'}
        
        def _generate():
            try:
                result = llm_analyzer.generate_competitor_swot(competitor_id, model)
                scan_jobs[job_id] = {'status': 'completed', 'result': result}
            except Exception as exc:
                logger.exception("Error generating SWOT")
                scan_jobs[job_id] = {'status': 'failed', 'error': str(exc)}
        
        thread = Thread(target=_generate, daemon=True)
        thread.start()
        
        return jsonify({'job_id': job_id})
    except Exception as e:
        logger.exception("Error initiating SWOT analysis")
        return jsonify({'error': str(e)}), 500


@app.route('/api/competitor/<int:competitor_id>/swot-analysis')
def get_swot_analysis(competitor_id: int):
    """Get latest SWOT analysis."""
    try:
        analysis = llm_analyzer.get_latest_analysis(competitor_id, 'swot')
        if not analysis:
            return jsonify({'error': 'No analysis found'}), 404
        return jsonify(analysis)
    except Exception as e:
        logger.exception("Error retrieving SWOT analysis")
        return jsonify({'error': str(e)}), 500


@app.route('/api/competitor/<int:competitor_id>/content-recommendations', methods=['POST'])
def generate_content_recommendations(competitor_id: int):
    """Generate content recommendations using LLM."""
    try:
        data = request.get_json() or {}
        target_audience = data.get('target_audience', 'B2C')
        model = data.get('model', None)
        
        recommendations = llm_analyzer.generate_content_recommendations(
            competitor_id, 
            target_audience, 
            model
        )
        
        if not recommendations:
            return jsonify({'error': 'Failed to generate recommendations'}), 500
        
        return jsonify(recommendations)
    except Exception as e:
        logger.exception("Error generating content recommendations")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(
        host=config.web_host,
        port=config.web_port,
        debug=config.get('web.debug', False)
    )
