"""
WSGI - Robo Ofertas PRO

Ponto de entrada utilizado pelo Gunicorn/Render.

O Render executará:

    gunicorn wsgi:app

Este arquivo mantém a inicialização do servidor separada
do código principal da aplicação.
"""

import logging
import os


# ============================================================
# CONFIGURAÇÃO BÁSICA DE LOG
# ============================================================

logging.basicConfig(
    level=os.getenv(
        "LOG_LEVEL",
        "INFO",
    ).upper(),
    format=(
        "%(asctime)s "
        "[%(levelname)s] "
        "%(name)s: "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "robo-ofertas.wsgi"
)


# ============================================================
# CARREGAMENTO DA APLICAÇÃO
# ============================================================

try:

    from app import create_app

    app = create_app()

    logger.info(
        "Robo Ofertas PRO carregado pelo WSGI."
    )

except Exception:

    logger.exception(
        "Falha ao carregar a aplicação."
    )

    raise


# ============================================================
# EXECUÇÃO LOCAL
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "5000",
        )
    )

    host = os.getenv(
        "HOST",
        "0.0.0.0",
    )

    logger.info(
        "Iniciando servidor local em %s:%s",
        host,
        port,
    )

    app.run(
        host=host,
        port=port,
        debug=False,
    )
