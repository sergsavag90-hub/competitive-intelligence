import os
from functools import wraps
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor


def init_tracing(service_name: str = "competitive-intelligence") -> None:
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
            "deployment.environment": os.getenv("ENV", "development"),
        }
    )
    provider = TracerProvider(
        sampler=TraceIdRatioBased(float(os.getenv("OTEL_SAMPLE_RATIO", "0.1"))),
        resource=resource,
    )
    trace.set_tracer_provider(provider)

    jaeger_exporter = JaegerExporter(
        agent_host_name=os.getenv("JAEGER_HOST", "jaeger"),
        agent_port=int(os.getenv("JAEGER_PORT", "6831")),
    )

    span_processor = BatchSpanProcessor(jaeger_exporter, max_queue_size=1000)
    provider.add_span_processor(span_processor)

    # Instrument common libraries
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
    CeleryInstrumentor().instrument()


def trace_function(name: str):
    def decorator(func):
        tracer = trace.get_tracer(__name__)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(name) as span:
                return await func(*args, **kwargs)

        return wrapper

    return decorator


tracer = trace.get_tracer(__name__)
