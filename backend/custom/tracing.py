# -*- coding: utf-8 -*-
"""Inicialização do OpenTelemetry, exportando pro Google Cloud Trace.

Mesma separação por processo do Cloud Profiler (ver `gunicorn.conf.py` e
`run_huey.py`): cada processo (Gunicorn, Huey) chama `init_tracing()` com
seu próprio nome de serviço, uma vez, depois do fork.

Exporta via OTLP direto pro endpoint nativo do Cloud Trace
(`telemetry.googleapis.com`), não pelo pacote `opentelemetry-exporter-gcp-trace`
— esse está deprecated (ver
https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/blob/main/MIGRATION.md),
e em staging, testado de verdade, não gerou nenhum trace visível mesmo sem
erro nenhum no processo.

Amostragem parcial por padrão (`SAMPLE_RATIO`) — o volume real de tráfego do
`api-prod` excede a franquia gratuita de 2,5M spans/mês do Cloud Trace se
toda requisição for amostrada.
"""

import google.auth
import google.auth.transport.grpc
import google.auth.transport.requests
import grpc
from huey import Huey
from huey.signals import SIGNAL_COMPLETE, SIGNAL_ERROR, SIGNAL_EXECUTING
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.resourcedetector.gcp_resource_detector import (
    GoogleCloudResourceDetector,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

OTLP_ENDPOINT = "telemetry.googleapis.com"

# Fração das requisições/tasks amostradas. Ajustar depois de ver volume real
# em staging — 1.0 (tudo) provavelmente estoura a franquia gratuita.
SAMPLE_RATIO = 0.1

_started = False


def _otlp_channel_credentials() -> grpc.ChannelCredentials:
    """Credenciais gRPC autenticadas com a mesma ADC do pod (Workload Identity)."""
    credentials, _ = google.auth.default()
    request = google.auth.transport.requests.Request()
    return grpc.composite_channel_credentials(
        grpc.ssl_channel_credentials(),
        grpc.metadata_call_credentials(
            google.auth.transport.grpc.AuthMetadataPlugin(credentials=credentials, request=request)
        ),
    )


def init_tracing(service_name: str) -> None:
    """Inicializa o tracer provider e instrumenta Django/psycopg2/requests.

    Idempotente: chamadas repetidas depois da primeira são ignoradas, como o
    `googlecloudprofiler.start()`.

    Args:
        service_name: nome do serviço no Cloud Trace (ex: `api-prod-gunicorn`).
    """
    global _started
    if _started:
        return

    resource = Resource.create({"service.name": service_name}).merge(
        GoogleCloudResourceDetector().detect()
    )
    provider = TracerProvider(sampler=TraceIdRatioBased(SAMPLE_RATIO), resource=resource)
    exporter = OTLPSpanExporter(endpoint=OTLP_ENDPOINT, credentials=_otlp_channel_credentials())
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    DjangoInstrumentor().instrument(is_sql_commentor_enabled=True)
    RequestsInstrumentor().instrument()
    # Psycopg2Instrumentor, não dbapi.wrap_connect genérico: esse troca só a
    # cursor_factory, mantendo a conexão como um objeto psycopg2 real. O
    # wrap_connect genérico devolve um proxy Python, e o Django chama
    # `psycopg2.extras.register_default_jsonb(connection)` logo depois de
    # conectar — função de nível C que rejeita o proxy
    # (TypeError: argument 2 must be a connection, cursor or None).
    Psycopg2Instrumentor().instrument()
    _started = True


def instrument_huey(huey: Huey) -> None:
    """Dá ao Huey um span raiz por execução de task.

    Não existe instrumentação pronta pro Huey (diferente do Django, que já
    cria um span por requisição sozinho) — sem isso, as queries/chamadas de
    uma task apareceriam soltas no Cloud Trace, sem nada que as agrupe.
    """
    tracer = trace.get_tracer(__name__)
    spans: dict[str, trace.Span] = {}

    @huey.signal(SIGNAL_EXECUTING)
    def _start_span(signal, task) -> None:
        spans[task.id] = tracer.start_span(task.name)

    @huey.signal(SIGNAL_COMPLETE, SIGNAL_ERROR)
    def _end_span(signal, task, exc=None) -> None:
        span = spans.pop(task.id, None)
        if span is None:
            return
        if exc is not None:
            span.record_exception(exc)
        span.end()
