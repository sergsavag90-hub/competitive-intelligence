import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter


service_name = os.getenv("OTEL_SERVICE_NAME", "competitive-intelligence")

resource = Resource.create({"service.name": service_name})
provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)

jaeger_exporter = JaegerExporter(
    agent_host_name=os.getenv("JAEGER_HOST", "jaeger"),
    agent_port=int(os.getenv("JAEGER_PORT", "6831")),
)

span_processor = BatchSpanProcessor(jaeger_exporter)
provider.add_span_processor(span_processor)

tracer = trace.get_tracer(__name__)
