# Structured JSON logging (NFR-7). structlog is the Python-side equivalent of
# the Gateway's pino setup (gateway/src/logger.js) -- every log line is a JSON
# object, not free text, so it's directly queryable in Loki (see
# infra/grafana-dashboard.json).
import logging
import sys

import structlog


def configure_logging():
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
    )


configure_logging()
logger = structlog.get_logger(service="resource-service")
