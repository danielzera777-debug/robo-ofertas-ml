"""
Middleware do Robo de Ofertas ML.

Responsável por pequenas camadas executadas antes e depois
das requisições Flask, sem depender de extensões externas.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from flask import Flask, g, request


LOGGER_NAME = "robo-ofertas.middleware"


# ============================================================
# LOGGER
# ============================================================

def get_logger():
    return logging.getLogger(
        LOGGER_NAME
    )


# ============================================================
# REQUEST ID
# ============================================================

def register_request_id(
    app: Flask,
) -> None:
    """
    Adiciona um identificador único a cada requisição.
    """

    @app.before_request
    def before_request_id():

        request_id = (
            request.headers.get(
                "X-Request-ID"
            )
            or str(
                uuid.uuid4()
            )
        )

        g.robo_request_id = request_id

        g.robo_request_started = (
            time.perf_counter()
        )

    @app.after_request
    def after_request_id(
        response,
    ):

        request_id = getattr(
            g,
            "robo_request_id",
            None,
        )

        if request_id:

            response.headers[
                "X-Request-ID"
            ] = request_id

        return response


# ============================================================
# TEMPO DA REQUISIÇÃO
# ============================================================

def register_request_timing(
    app: Flask,
) -> None:
    """
    Mede o tempo de processamento da requisição.
    """

    @app.after_request
    def request_timing(
        response,
    ):

        started = getattr(
            g,
            "robo_request_started",
            None,
        )

        if started is not None:

            elapsed = (
                time.perf_counter()
                - started
            )

            response.headers[
                "X-Response-Time"
            ] = f"{elapsed:.4f}s"

        return response


# ============================================================
# LOG DE REQUISIÇÕES
# ============================================================

def register_request_logging(
    app: Flask,
) -> None:
    """
    Registra informações básicas das requisições.
    """

    logger = get_logger()

    @app.after_request
    def request_logging(
        response,
    ):

        started = getattr(
            g,
            "robo_request_started",
            None,
        )

        elapsed = 0.0

        if started is not None:

            elapsed = (
                time.perf_counter()
                - started
            )

        request_id = getattr(
            g,
            "robo_request_id",
            "-",
        )

        logger.info(
            "%s %s -> %s "
            "(%.4fs) request_id=%s",
            request.method,
            request.path,
            response.status_code,
            elapsed,
            request_id,
        )

        return response


# ============================================================
# HEADERS BÁSICOS
# ============================================================

def register_basic_headers(
    app: Flask,
) -> None:
    """
    Adiciona headers básicos de segurança e identificação.
    """

    @app.after_request
    def basic_headers(
        response,
    ):

        response.headers.setdefault(
            "X-Content-Type-Options",
            "nosniff",
        )

        response.headers.setdefault(
            "X-Frame-Options",
            "SAMEORIGIN",
        )

        response.headers.setdefault(
            "Referrer-Policy",
            "strict-origin-when-cross-origin",
        )

        return response


# ============================================================
# CORS SIMPLES
# ============================================================

def register_cors(
    app: Flask,
    allowed_origins: Optional[str] = None,
) -> None:
    """
    CORS simples sem dependência externa.

    Por padrão não habilita acesso externo indiscriminado.
    """

    origins = (
        allowed_origins
        or app.config.get(
            "CORS_ALLOWED_ORIGINS",
            "",
        )
    )

    if not origins:

        return

    origin_list = [
        item.strip()
        for item in str(
            origins
        ).split(",")
        if item.strip()
    ]

    @app.after_request
    def cors_headers(
        response,
    ):

        request_origin = request.headers.get(
            "Origin"
        )

        if (
            request_origin
            and request_origin in origin_list
        ):

            response.headers[
                "Access-Control-Allow-Origin"
            ] = request_origin

            response.headers[
                "Vary"
            ] = "Origin"

            response.headers[
                "Access-Control-Allow-Headers"
            ] = (
                "Content-Type, "
                "Authorization, "
                "X-Request-ID"
            )

            response.headers[
                "Access-Control-Allow-Methods"
            ] = (
                "GET, POST, PUT, PATCH, "
                "DELETE, OPTIONS"
            )

        return response


# ============================================================
# HEALTH / MONITORAMENTO
# ============================================================

def is_health_path(
    path: str,
) -> bool:
    """
    Identifica endpoints de monitoramento.
    """

    return path in (
        "/health",
        "/api/ping",
        "/api/status",
    )


# ============================================================
# INSTALAÇÃO
# ============================================================

def init_middleware(
    app: Flask,
) -> Flask:
    """
    Instala todos os middleware internos.
    """

    register_request_id(
        app
    )

    register_request_timing(
        app
    )

    register_request_logging(
        app
    )

    register_basic_headers(
        app
    )

    cors_enabled = app.config.get(
        "CORS_ENABLED",
        False,
    )

    if cors_enabled:

        register_cors(
            app
        )

    get_logger().info(
        "Middleware inicializado."
    )

    return app


__all__ = [
    "init_middleware",
    "register_request_id",
    "register_request_timing",
    "register_request_logging",
    "register_basic_headers",
    "register_cors",
    "is_health_path",
]
