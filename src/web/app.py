"""
Flask web application for presenting competitive intelligence data.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template
from flask_cors import CORS

# Ensure the project root is importable when running inside Docker
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.database.db_manager import DatabaseManager  # noqa: E402
from src.utils.config import config  # noqa: E402

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=getattr(logging, config.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)

db = DatabaseManager()


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


if __name__ == '__main__':
    app.run(
        host=config.web_host,
        port=config.web_port,
        debug=config.get('web.debug', False)
    )
