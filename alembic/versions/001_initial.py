"""initial async schema"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "competitors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("priority", sa.Integer(), default=1),
        sa.Column("enabled", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), default=sa.func.now()),
    )

    op.create_table(
        "scan_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id"), nullable=False),
        sa.Column("scan_type", sa.String(length=50)),
        sa.Column("status", sa.String(length=20)),
        sa.Column("started_at", sa.DateTime(), default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("items_collected", sa.Integer(), default=0),
        sa.Column("error_message", sa.Text()),
        sa.Column("metadata", sa.JSON()),
    )

    op.create_table(
        "seo_data",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id"), nullable=False),
        sa.Column("title", sa.String(length=500)),
        sa.Column("meta_description", sa.Text()),
        sa.Column("meta_keywords", sa.Text()),
        sa.Column("meta_robots", sa.String(length=100)),
        sa.Column("canonical_url", sa.String(length=500)),
        sa.Column("og_title", sa.String(length=500)),
        sa.Column("og_description", sa.Text()),
        sa.Column("og_image", sa.String(length=500)),
        sa.Column("og_type", sa.String(length=50)),
        sa.Column("h1_tags", sa.JSON()),
        sa.Column("h2_tags", sa.JSON()),
        sa.Column("h3_tags", sa.JSON()),
        sa.Column("robots_txt", sa.Text()),
        sa.Column("sitemap_url", sa.String(length=500)),
        sa.Column("sitemap_urls_count", sa.Integer()),
        sa.Column("structured_data", sa.JSON()),
        sa.Column("internal_links_count", sa.Integer()),
        sa.Column("external_links_count", sa.Integer()),
        sa.Column("broken_links_count", sa.Integer()),
        sa.Column("page_load_time", sa.Float()),
        sa.Column("page_size_kb", sa.Integer()),
        sa.Column("crawled_pages_count", sa.Integer(), default=0),
        sa.Column("semantic_core", sa.JSON()),
        sa.Column("collected_at", sa.DateTime(), default=sa.func.now()),
    )

    op.create_table(
        "company_data",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id"), nullable=False),
        sa.Column("emails", sa.LargeBinary()),
        sa.Column("phones", sa.LargeBinary()),
        sa.Column("addresses", sa.LargeBinary()),
        sa.Column("facebook_url", sa.String(length=500)),
        sa.Column("instagram_url", sa.String(length=500)),
        sa.Column("linkedin_url", sa.String(length=500)),
        sa.Column("twitter_url", sa.String(length=500)),
        sa.Column("youtube_url", sa.String(length=500)),
        sa.Column("telegram_url", sa.String(length=500)),
        sa.Column("company_name", sa.String(length=255)),
        sa.Column("legal_name", sa.String(length=255)),
        sa.Column("tax_id", sa.String(length=100)),
        sa.Column("registration_number", sa.String(length=100)),
        sa.Column("contact_forms", sa.JSON()),
        sa.Column("support_chat", sa.Boolean(), default=False),
        sa.Column("working_hours", sa.Text()),
        sa.Column("collected_at", sa.DateTime(), default=sa.func.now()),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id"), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("sku", sa.String(length=100)),
        sa.Column("url", sa.String(length=1000)),
        sa.Column("category", sa.String(length=255)),
        sa.Column("subcategory", sa.String(length=255)),
        sa.Column("price", sa.Float()),
        sa.Column("currency", sa.String(length=10)),
        sa.Column("old_price", sa.Float()),
        sa.Column("discount_percent", sa.Float()),
        sa.Column("description", sa.Text()),
        sa.Column("short_description", sa.Text()),
        sa.Column("specifications", sa.JSON()),
        sa.Column("main_image", sa.String(length=1000)),
        sa.Column("images", sa.JSON()),
        sa.Column("in_stock", sa.Boolean(), default=True),
        sa.Column("stock_quantity", sa.Integer()),
        sa.Column("available_for_order", sa.Boolean(), default=True),
        sa.Column("rating", sa.Float()),
        sa.Column("reviews_count", sa.Integer()),
        sa.Column("first_seen", sa.DateTime(), default=sa.func.now()),
        sa.Column("last_seen", sa.DateTime(), default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.UniqueConstraint("competitor_id", "url", name="uq_competitor_product_url"),
    )

    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("old_price", sa.Float()),
        sa.Column("in_stock", sa.Boolean(), default=True),
        sa.Column("recorded_at", sa.DateTime(), default=sa.func.now()),
    )

    op.create_table(
        "promotions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id"), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("url", sa.String(length=1000)),
        sa.Column("promotion_type", sa.String(length=50)),
        sa.Column("discount_value", sa.Float()),
        sa.Column("discount_type", sa.String(length=20)),
        sa.Column("promo_code", sa.String(length=100)),
        sa.Column("terms_and_conditions", sa.Text()),
        sa.Column("minimum_purchase", sa.Float()),
        sa.Column("applicable_categories", sa.JSON()),
        sa.Column("start_date", sa.DateTime()),
        sa.Column("end_date", sa.DateTime()),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("image_url", sa.String(length=1000)),
        sa.Column("first_seen", sa.DateTime(), default=sa.func.now()),
        sa.Column("last_seen", sa.DateTime(), default=sa.func.now()),
    )

    op.create_table(
        "llm_analysis",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id")),
        sa.Column("analysis_type", sa.String(length=50)),
        sa.Column("summary", sa.Text()),
        sa.Column("strengths", sa.JSON()),
        sa.Column("weaknesses", sa.JSON()),
        sa.Column("opportunities", sa.JSON()),
        sa.Column("threats", sa.JSON()),
        sa.Column("recommendations", sa.JSON()),
        sa.Column("full_analysis", sa.Text()),
        sa.Column("model_used", sa.String(length=50)),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
        sa.Column("processing_time", sa.Float()),
    )

    op.create_table(
        "functional_test_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id"), nullable=False),
        sa.Column("registration_status", sa.String(length=50)),
        sa.Column("registration_message", sa.Text()),
        sa.Column("contact_form_status", sa.String(length=50)),
        sa.Column("contact_form_message", sa.Text()),
        sa.Column("collected_at", sa.DateTime(), default=sa.func.now()),
    )


def downgrade():
    op.drop_table("functional_test_results")
    op.drop_table("llm_analysis")
    op.drop_table("promotions")
    op.drop_table("price_history")
    op.drop_table("products")
    op.drop_table("company_data")
    op.drop_table("seo_data")
    op.drop_table("scan_history")
    op.drop_table("competitors")
