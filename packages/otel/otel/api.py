"""No-op OpenTelemetry API matching the exported pure-R ``otel`` functions."""

from __future__ import annotations

import os
from collections import OrderedDict

invalid_span_id = "0" * 16
invalid_trace_id = "0" * 32
span_kinds = ["internal", "server", "client", "producer", "consumer"]
span_status_codes = ["unset", "ok", "error"]
log_severity_levels = list(range(1, 25))


class SpanContext:
    def is_valid(self): return False
    def get_trace_flags(self): return {}
    def get_trace_id(self): return invalid_trace_id
    def get_span_id(self): return invalid_span_id
    def is_remote(self): return False
    def is_sampled(self): return False
    def to_http_headers(self): return {}


class Span:
    def __init__(self, name=None):
        self.name = "<NA>" if name is None else name
        self.context = SpanContext()
    def get_context(self): return self.context
    def is_valid(self): return False
    def is_recording(self): return False
    def set_attribute(self, name, value=None): return self
    def add_event(self, name, attributes=None, timestamp=None): return self
    def add_link(self, target, attributes=None): return self
    def set_status(self, status_code="unset", description=None): return self
    def update_name(self, name): return self
    def end(self, options=None, status_code=None): return self
    def record_exception(self, attributes=None): return self
    def activate(self, activation_scope=None, end_on_exit=False): return self
    def deactivate(self, activation_scope=None): return self


class Tracer:
    def start_span(self, name=None, attributes=None, links=None, options=None, **kwargs):
        return Span(name)
    def get_active_span_context(self): return SpanContext()
    def get_active_span(self): return Span()
    def is_enabled(self): return False
    def flush(self): return self
    def extract_http_context(self, headers): return SpanContext()


class TracerProvider:
    def get_tracer(self, name=None, version=None, schema_url=None, attributes=None, **kwargs):
        return Tracer()
    def flush(self): return self
    def get_spans(self): return []


class Logger:
    def trace(self, *args, **kwargs): return self
    debug = trace
    info = trace
    warn = trace
    error = trace
    fatal = trace
    def is_enabled(self, severity="info", event_id=None): return False
    def get_minimum_severity(self): return {"maximumseverity": 255}
    def set_minimum_severity(self, minimum_severity): return self
    def log(self, msg="", severity="info", span_context=None, **kwargs): return self


class LoggerProvider:
    def get_logger(self, name=None, minimum_severity=None, version=None, schema_url=None, attributes=None, **kwargs):
        return Logger()
    def flush(self): return None


class Instrument:
    def add(self, value, attributes=None, span_context=None, **kwargs): return self
    def record(self, value, attributes=None, span_context=None, **kwargs): return self


class Meter:
    def is_enabled(self): return False
    def create_counter(self, name, description=None, unit=None): return Instrument()
    def create_up_down_counter(self, name, description=None, unit=None): return Instrument()
    def create_histogram(self, name, description=None, unit=None): return Instrument()
    def create_gauge(self, name, description=None, unit=None): return Instrument()


class MeterProvider:
    def get_meter(self, name=None, version=None, schema_url=None, attributes=None, **kwargs): return Meter()
    def flush(self, timeout=None, **kwargs): return self
    def shutdown(self, timeout=None, **kwargs): return self
    def get_metrics(self): return []


_tracer_provider = _logger_provider = _meter_provider = None

def tracer_provider_noop(): return TracerProvider()
def meter_provider_noop(): return MeterProvider()
def logger_provider_noop(): return LoggerProvider()

def get_default_tracer_provider():
    global _tracer_provider
    if _tracer_provider is None: _tracer_provider = tracer_provider_noop()
    return _tracer_provider

def get_default_meter_provider():
    global _meter_provider
    if _meter_provider is None: _meter_provider = meter_provider_noop()
    return _meter_provider

def get_default_logger_provider():
    global _logger_provider
    if _logger_provider is None: _logger_provider = logger_provider_noop()
    return _logger_provider

def default_tracer_name(name=None):
    if name is not None:
        package = None
        return {"name": name, "package": package, "on": _scope_on(name, package)}
    return {"name": "org.r-project.R", "package": "R", "on": _scope_on("org.r-project.R", "R")}

def _scope_on(name, package):
    inc, exc = os.getenv("OTEL_R_EMIT_SCOPES"), os.getenv("OTEL_R_SUPPRESS_SCOPES")
    candidates = [name, package]
    if inc and not any(_glob_match(x, p.strip()) for x in candidates if x for p in inc.split(",")): return False
    if exc and any(_glob_match(x, p.strip()) for x in candidates if x for p in exc.split(",")): return False
    return True

def _glob_match(value, pattern):
    import fnmatch
    return fnmatch.fnmatchcase(value, pattern)

def get_tracer(name=None, version=None, schema_url=None, attributes=None, provider=None, **kwargs):
    return (provider or get_default_tracer_provider()).get_tracer(name, version, schema_url, attributes, **kwargs)

def get_meter(name=None, version=None, schema_url=None, attributes=None, provider=None, **kwargs):
    return (provider or get_default_meter_provider()).get_meter(name, version, schema_url, attributes, **kwargs)

def get_logger(name=None, minimum_severity=None, version=None, schema_url=None, attributes=None, provider=None, **kwargs):
    return (provider or get_default_logger_provider()).get_logger(name, minimum_severity, version, schema_url, attributes, **kwargs)

def get_active_span(): return get_tracer().get_active_span()
def get_active_span_context(): return get_tracer().get_active_span_context()
def start_span(name=None, attributes=None, links=None, options=None, tracer=None, **kwargs):
    return (tracer if isinstance(tracer, Tracer) else get_tracer(tracer)).start_span(name, attributes, links, options, **kwargs)
def end_span(span): span.end(); return span
def local_active_span(span, end_on_exit=False, activation_scope=None): span.activate(activation_scope, end_on_exit); return span
def with_active_span(span, expr, end_on_exit=False):
    span.activate(end_on_exit=end_on_exit)
    return expr() if callable(expr) else expr
def start_local_active_span(name=None, attributes=None, links=None, options=None, tracer=None, activation_scope=None, end_on_exit=True, **kwargs):
    span = (tracer if isinstance(tracer, Tracer) else get_tracer(tracer)).start_span(name, attributes, links, options, **kwargs)
    span.activate(activation_scope, end_on_exit)
    return span
def is_tracing_enabled(tracer=None): return (tracer if isinstance(tracer, Tracer) else get_tracer(tracer)).is_enabled()
def is_measuring_enabled(meter=None): return (meter if isinstance(meter, Meter) else get_meter(meter)).is_enabled()
def is_logging_enabled(severity="info", logger=None): return (logger if isinstance(logger, Logger) else get_logger(logger)).is_enabled(severity)
def log(msg, *args, severity="info", logger=None, **kwargs): return (logger if isinstance(logger, Logger) else get_logger()).log(msg, severity, *args, **kwargs)
def _log_at(level, msg, *args, logger=None, **kwargs): return log(msg, *args, severity=level, logger=logger, **kwargs)
def log_trace(msg, *args, logger=None, **kwargs): return _log_at("trace", msg, *args, logger=logger, **kwargs)
def log_debug(msg, *args, logger=None, **kwargs): return _log_at("debug", msg, *args, logger=logger, **kwargs)
def log_info(msg, *args, logger=None, **kwargs): return _log_at("info", msg, *args, logger=logger, **kwargs)
def log_warn(msg, *args, logger=None, **kwargs): return _log_at("warn", msg, *args, logger=logger, **kwargs)
def log_error(msg, *args, logger=None, **kwargs): return _log_at("error", msg, *args, logger=logger, **kwargs)
def log_fatal(msg, *args, logger=None, **kwargs): return _log_at("fatal", msg, *args, logger=logger, **kwargs)
def counter_add(name, value=1, attributes=None, context=None, meter=None):
    x = (meter if isinstance(meter, Meter) else get_meter(meter)).create_counter(name); return x.add(value, attributes, context)
def up_down_counter_add(name, value=1, attributes=None, context=None, meter=None):
    x = (meter if isinstance(meter, Meter) else get_meter(meter)).create_up_down_counter(name); return x.add(value, attributes, context)
def histogram_record(name, value, attributes=None, context=None, meter=None):
    x = (meter if isinstance(meter, Meter) else get_meter(meter)).create_histogram(name); return x.record(value, attributes, context)
def gauge_record(name, value, attributes=None, context=None, meter=None):
    x = (meter if isinstance(meter, Meter) else get_meter(meter)).create_gauge(name); return x.record(value, attributes, context)
def as_attributes(x):
    if not isinstance(x, (dict, list, tuple)): raise TypeError("Invalid argument: `x` must be a list in `as_attributes()`.")
    items = list(x.items()) if isinstance(x, dict) else list(enumerate(x, 1))
    limit = int(os.getenv("OTEL_ATTRIBUTE_COUNT_LIMIT", "128"))
    val_limit = os.getenv("OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT")
    val_limit = float("inf") if val_limit is None else int(val_limit)
    ret = OrderedDict()
    for i, (key, value) in enumerate(items[:limit], 1):
        key = str(key) if key not in (None, "") else str(i)
        base = key; n = 1
        while key in ret: n += 1; key = f"{base}.{n}"
        if isinstance(value, (list, tuple)) and val_limit != float("inf"):
            value = list(value[:int(val_limit)])
        ret[key] = value
    return ret
def pack_http_context(): return get_active_span_context().to_http_headers()
def extract_http_context(headers): return get_tracer().extract_http_context(headers)
