"""
OpenTelemetry tracing setup for l8e-harbor.
"""

from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor


def setup_tracing(
    service_name: str = "l8e-harbor",
    jaeger_endpoint: Optional[str] = None,
    enable_console: bool = False
) -> None:
    """
    Setup OpenTelemetry tracing.
    
    Args:
        service_name: Service name for traces
        jaeger_endpoint: Jaeger collector endpoint
        enable_console: Enable console span exporter
    """
    # Set up the tracer provider
    trace.set_tracer_provider(TracerProvider())
    tracer_provider = trace.get_tracer_provider()
    
    # Add span processors
    if jaeger_endpoint:
        try:
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=6831,
                collector_endpoint=jaeger_endpoint,
            )
            tracer_provider.add_span_processor(
                BatchSpanProcessor(jaeger_exporter)
            )
        except ImportError:
            print("Jaeger exporter not available")
    
    if enable_console:
        try:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            console_exporter = ConsoleSpanExporter()
            tracer_provider.add_span_processor(
                BatchSpanProcessor(console_exporter)
            )
        except ImportError:
            print("Console exporter not available")
    
    # Set up auto-instrumentation
    FastAPIInstrumentor.instrument()
    HTTPXClientInstrumentor.instrument()


def get_tracer(name: str = "l8e-harbor"):
    """Get a tracer instance."""
    return trace.get_tracer(name)


class TracingContext:
    """Helper for creating custom spans."""
    
    def __init__(self, tracer_name: str = "l8e-harbor"):
        self.tracer = get_tracer(tracer_name)
    
    def start_span(self, name: str, attributes: Optional[dict] = None):
        """Start a new span."""
        span = self.tracer.start_span(name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        return span
    
    def trace_route_matching(self, path: str, route_id: Optional[str] = None):
        """Trace route matching operation."""
        attributes = {"http.path": path}
        if route_id:
            attributes["route.id"] = route_id
        return self.start_span("route.match", attributes)
    
    def trace_backend_call(self, backend_url: str, method: str):
        """Trace backend HTTP call."""
        attributes = {
            "http.url": backend_url,
            "http.method": method
        }
        return self.start_span("backend.call", attributes)
    
    def trace_auth_check(self, adapter_type: str):
        """Trace authentication check."""
        attributes = {"auth.adapter": adapter_type}
        return self.start_span("auth.check", attributes)