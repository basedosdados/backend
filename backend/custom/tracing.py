# -*- coding: utf-8 -*-
"""Inicialização do OpenTelemetry.

Cada processo (Gunicorn, Huey) chama `init_tracing()` com seu próprio
nome de serviço, uma vez, depois do fork. Exporta via OTLP pro endpoint
em `OTEL_EXPORTER_OTLP_ENDPOINT`.
"""

import os

from huey import Huey
from huey.signals import SIGNAL_COMPLETE, SIGNAL_ERROR, SIGNAL_EXECUTING
from opentelemetry import context, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

DEFAULT_OTLP_ENDPOINT = "localhost:4317"

# Fração das requisições/tasks amostradas. Configurável via env var —
# localmente não tem custo nenhum amostrar tudo (`compose.yaml` seta 1.0);
# em staging/prod, 1.0 provavelmente estoura a franquia gratuita do Cloud
# Trace, então o padrão fica baixo.
DEFAULT_SAMPLE_RATIO = 0.1

_started = False


def init_tracing(service_name: str) -> None:
    """Inicializa o tracer provider e instrumenta Django/psycopg2/requests.

    Idempotente — chamadas repetidas são ignoradas.

    Args:
        service_name: nome do serviço no backend de trace.
    """
    global _started
    if _started:
        return

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", DEFAULT_OTLP_ENDPOINT)
    sample_ratio = float(os.environ.get("OTEL_TRACES_SAMPLE_RATIO", DEFAULT_SAMPLE_RATIO))
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(sampler=TraceIdRatioBased(sample_ratio), resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    DjangoInstrumentor().instrument(is_sql_commentor_enabled=True)
    RequestsInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()
    _started = True


def instrument_huey(huey: Huey) -> None:
    """Dá ao Huey um span raiz por execução de task.

    Args:
        huey: instância configurada do Huey.
    """
    tracer = trace.get_tracer(__name__)
    # (span, token do contexto anexado) por task em execução. O token é o
    # que `context.detach()` precisa pra desfazer o anexo depois.
    spans: dict[str, tuple[trace.Span, object]] = {}

    @huey.signal(SIGNAL_EXECUTING)
    def _start_span(signal, task) -> None:
        span = tracer.start_span(task.name)
        # `start_span` só cria o span — sem isso, as queries/chamadas HTTP
        # que a task dispara não sabem que devem aninhar nele (cada uma
        # vira um trace solto, sem span pai).
        token = context.attach(trace.set_span_in_context(span))
        spans[task.id] = (span, token)

    @huey.signal(SIGNAL_COMPLETE, SIGNAL_ERROR)
    def _end_span(signal, task, exc=None) -> None:
        entry = spans.pop(task.id, None)
        if entry is None:
            return
        span, token = entry
        context.detach(token)
        if exc is not None:
            span.record_exception(exc)
        span.end()
