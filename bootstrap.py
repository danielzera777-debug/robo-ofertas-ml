"""
Bootstrap do Robo de Ofertas ML.

Responsável por centralizar a inicialização da aplicação
e evitar que o Gunicorn precise conhecer detalhes internos
do projeto.

Uso no Render:

    gunicorn app:app

O objeto `app` continua sendo disponibilizado pelo app.py.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from flask import Flask


LOGGER_NAME = "robo-ofertas.bootstrap"


# ============================================================
# LOGGER
# ============================================================

logger = logging.getLogger(
    LOGGER_NAME
)


# ============================================================
# CRIAÇÃO DA APLICAÇÃO
# ============================================================

def create_application(
    config_class: Optional[object] = None,
) -> Flask:
    """
    Cria a aplicação Flask usando o factory existente
    em app.py.
    """

    from app import create_app

    if config_class is not None:

        application = create_app(
            config_class=config_class
        )

    else:

        application = create_app()

    return application


# ============================================================
# CONFIGURAÇÃO DE AMBIENTE
# ============================================================

def get_environment() -> str:
    """
    Retorna o ambiente atual.
    """

    return (
        os.getenv(
            "ENVIRONMENT"
        )
        or os.getenv(
            "FLASK_ENV"
        )
        or "production"
    ).strip().lower()


def get_port(
    default: int = 5000,
) -> int:
    """
    Retorna a porta definida pelo ambiente.
    """

    value = os.getenv(
        "PORT"
    )

    if not value:

        return default

    try:

        return int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


def get_host(
    default: str = "0.0.0.0",
) -> str:
    """
    Retorna o host da aplicação.
    """

    return (
        os.getenv(
            "HOST"
        )
        or default
    ).strip()


# ============================================================
# CONFIGURAÇÃO DE LOG
# ============================================================

def log_bootstrap_info(
    application: Flask,
) -> None:
    """
    Registra informações básicas sobre a aplicação.
    """

    app_name = application.config.get(
        "APP_NAME",
        "Robo de Ofertas ML",
    )

    version = application.config.get(
        "APP_VERSION",
        "unknown",
    )

    environment = application.config.get(
        "ENVIRONMENT",
        get_environment(),
    )

    logger.info(
        "%s %s inicializado.",
        app_name,
        version,
    )

    logger.info(
        "Ambiente: %s",
        environment,
    )

    logger.info(
        "Host: %s",
        get_host(),
    )

    logger.info(
        "Porta: %s",
        get_port(),
    )


# ============================================================
# VALIDAÇÃO MÍNIMA
# ============================================================

def validate_application(
    application: Flask,
) -> bool:
    """
    Confirma que o objeto recebido é uma aplicação Flask.
    """

    if not isinstance(
        application,
        Flask,
    ):

        raise TypeError(
            "A aplicação criada não é uma instância Flask."
        )

    if not application.name:

        raise RuntimeError(
            "A aplicação Flask não possui nome."
        )

    return True


# ============================================================
# BOOTSTRAP PRINCIPAL
# ============================================================

def bootstrap(
    config_class: Optional[object] = None,
) -> Flask:
    """
    Inicializa e valida a aplicação.
    """

    application = create_application(
        config_class=config_class
    )

    validate_application(
        application
    )

    log_bootstrap_info(
        application
    )

    return application


# ============================================================
# WSGI
# ============================================================

def get_wsgi_application() -> Flask:
    """
    Retorna a aplicação pronta para WSGI/Gunicorn.
    """

    return bootstrap()


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":

    application = bootstrap()

    host = get_host()

    port = get_port()

    debug = (
        get_environment()
        in (
            "development",
            "dev",
        )
    )

    application.run(
        host=host,
        port=port,
        debug=debug,
    )


__all__ = [
    "create_application",
    "get_environment",
    "get_port",
    "get_host",
    "log_bootstrap_info",
    "validate_application",
    "bootstrap",
    "get_wsgi_application",
]
