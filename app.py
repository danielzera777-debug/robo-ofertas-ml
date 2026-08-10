"""
Robo Ofertas PRO
================

Núcleo principal da aplicação Flask.

Responsabilidades:
- criar a aplicação Flask;
- carregar configurações;
- inicializar extensões;
- registrar rotas;
- registrar autenticação do Mercado Livre;
- configurar segurança;
- disponibilizar health check;
- disponibilizar diagnóstico;
- tratar erros;
- iniciar o servidor local quando executado diretamente.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
)

from config import get_config
from extensions import init_extensions

# ============================================================
# AUTENTICAÇÃO MERCADO LIVRE
# ============================================================

from routes.auth import register_auth_routes


# ============================================================
# CONSTANTES
# ============================================================

LOGGER_NAME = "robo-ofertas"

BASE_DIR = Path(
    __file__
).resolve().parent


# ============================================================
# LOGGING
# ============================================================

def configure_logging(
    app: Flask,
) -> None:
    """
    Configura o sistema de logs.
    """

    level_name = app.config.get(
        "LOG_LEVEL",
        "INFO",
    )

    level = getattr(
        logging,
        str(level_name).upper(),
        logging.INFO,
    )

    formatter = logging.Formatter(
        "%(asctime)s "
        "[%(levelname)s] "
        "%(name)s: "
        "%(message)s"
    )

    logger = logging.getLogger(
        LOGGER_NAME
    )

    logger.setLevel(
        level
    )

    if not logger.handlers:

        console_handler = (
            logging.StreamHandler()
        )

        console_handler.setLevel(
            level
        )

        console_handler.setFormatter(
            formatter
        )

        logger.addHandler(
            console_handler
        )

    logger.propagate = False


# ============================================================
# DIRETÓRIOS
# ============================================================

def ensure_directories() -> None:
    """
    Garante que os diretórios básicos existam.
    """

    directories = [

        BASE_DIR / "logs",

        BASE_DIR / "database",

        BASE_DIR / "static",

        BASE_DIR / "static" / "css",

        BASE_DIR / "static" / "js",

        BASE_DIR / "static" / "img",

        BASE_DIR / "static" / "icons",

        BASE_DIR / "templates",

        BASE_DIR / "tests",

    ]

    for directory in directories:

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )


# ============================================================
# HEADERS DE SEGURANÇA
# ============================================================

def register_security_headers(
    app: Flask,
) -> None:
    """
    Adiciona headers básicos de segurança.
    """

    if not app.config.get(
        "SECURITY_HEADERS_ENABLED",
        True,
    ):
        return

    @app.after_request
    def security_headers(
        response
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

        response.headers.setdefault(
            "Permissions-Policy",
            (
                "camera=(), "
                "microphone=(), "
                "geolocation=()"
            ),
        )

        response.headers.setdefault(
            "Content-Security-Policy",
            (
                "default-src 'self'; "
                "img-src 'self' data: https:; "
                "style-src 'self' 'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline'; "
                "connect-src 'self' https:; "
                "font-src 'self' data: https:; "
                "frame-ancestors 'self';"
            ),
        )

        return response


# ============================================================
# REQUEST TRACKING
# ============================================================

def register_request_tracking(
    app: Flask,
) -> None:
    """
    Registra tempo básico das requisições.
    """

    @app.before_request
    def request_started():

        request._robo_request_started = (
            time.time()
        )

    @app.after_request
    def request_finished(
        response
    ):

        started = getattr(
            request,
            "_robo_request_started",
            None,
        )

        if started is not None:

            duration = (
                time.time()
                -
                started
            )

            response.headers.setdefault(
                "X-Request-Time",
                f"{duration:.4f}",
            )

        return response


# ============================================================
# ROTAS PRINCIPAIS
# ============================================================

def register_core_routes(
    app: Flask,
) -> None:
    """
    Registra as rotas básicas da aplicação.
    """

    @app.route(
        "/",
        methods=["GET"],
    )
    def home():

        connected = False

        try:

            from flask import session

            connected = bool(
                session.get(
                    "access_token"
                )
            )

        except Exception:

            connected = False

        try:

            return render_template(
                "index.html",
                connected=connected,
                app_name=app.config.get(
                    "APP_NAME",
                    "Robo Ofertas PRO",
                ),
                version=app.config.get(
                    "APP_VERSION",
                    "10.0.0",
                ),
            )

        except Exception as exc:

            logging.getLogger(
                LOGGER_NAME
            ).exception(
                "Erro carregando index.html: %s",
                exc,
            )

            return jsonify(

                ok=True,

                app=app.config.get(
                    "APP_NAME",
                    "Robo Ofertas PRO",
                ),

                version=app.config.get(
                    "APP_VERSION",
                    "10.0.0",
                ),

                status="online",

                mensagem=(
                    "Aplicação funcionando."
                ),

            )


    # ========================================================
    # HEALTH
    # ========================================================

    @app.route(
        "/health",
        methods=["GET"],
    )
    def health():

        return jsonify(

            ok=True,

            status="online",

            app=app.config.get(
                "APP_NAME",
                "Robo Ofertas PRO",
            ),

            version=app.config.get(
                "APP_VERSION",
                "10.0.0",
            ),

            environment=app.config.get(
                "ENVIRONMENT",
                "production",
            ),

            timestamp=int(
                time.time()
            ),

        )


    # ========================================================
    # PING
    # ========================================================

    @app.route(
        "/api/ping",
        methods=["GET"],
    )
    def api_ping():

        return jsonify(

            ok=True,

            message="pong",

            timestamp=int(
                time.time()
            ),

        )


    # ========================================================
    # STATUS GERAL
    # ========================================================

    @app.route(
        "/api/status",
        methods=["GET"],
    )
    def api_status():

        config_class = app.config.get(
            "_ROBO_CONFIG_CLASS"
        )

        if config_class:

            try:

                ml_configured = (
                    config_class
                    .mercado_livre_configured()
                )

            except Exception:

                ml_configured = False

            try:

                ml_summary = (
                    config_class
                    .mercado_livre_summary()
                )

            except Exception:

                ml_summary = {}

            try:

                security_summary = (
                    config_class
                    .security_summary()
                )

            except Exception:

                security_summary = {}

        else:

            ml_configured = False

            ml_summary = {}

            security_summary = {}


        try:

            from flask import session

            connected = bool(
                session.get(
                    "access_token"
                )
            )

        except Exception:

            connected = False


        return jsonify(

            ok=True,

            application={

                "name":
                    app.config.get(
                        "APP_NAME",
                        "Robo Ofertas PRO",
                    ),

                "version":
                    app.config.get(
                        "APP_VERSION",
                        "10.0.0",
                    ),

                "environment":
                    app.config.get(
                        "ENVIRONMENT",
                        "production",
                    ),

            },

            mercado_livre={

                "configured":
                    ml_configured,

                "connected":
                    connected,

                **ml_summary,

            },

            security=
                security_summary,

        )


# ============================================================
# ROTAS FUTURAS
# ============================================================

def register_future_routes(
    app: Flask,
) -> None:
    """
    Registra módulos adicionais quando disponíveis.

    O módulo de autenticação NÃO é carregado aqui.
    Ele é registrado diretamente em create_app().
    """

    modules = [

        (
            "routes.produtos",
            "register_product_routes",
        ),

        (
            "routes.diagnostico",
            "register_diagnostic_routes",
        ),

        (
            "routes.whatsapp",
            "register_whatsapp_routes",
        ),

        (
            "routes.admin",
            "register_admin_routes",
        ),

    ]

    logger = logging.getLogger(
        LOGGER_NAME
    )

    for module_name, function_name in modules:

        try:

            module = __import__(
                module_name,
                fromlist=[
                    function_name
                ],
            )

            register_function = getattr(
                module,
                function_name,
            )

            register_function(
                app
            )

            logger.info(
                "Módulo carregado: %s",
                module_name,
            )

        except ModuleNotFoundError:

            logger.debug(
                "Módulo ainda não criado: %s",
                module_name,
            )

        except AttributeError:

            logger.warning(
                "Função %s não encontrada em %s.",
                function_name,
                module_name,
            )

        except Exception:

            logger.exception(
                "Erro carregando módulo %s.",
                module_name,
            )

            raise


# ============================================================
# ERROS
# ============================================================

def register_error_handlers(
    app: Flask,
) -> None:

    @app.errorhandler(404)
    def not_found(error):

        if request.path.startswith(
            "/api/"
        ):

            return jsonify(

                ok=False,

                erro="not_found",

                mensagem=(
                    "Rota não encontrada."
                ),

                rota=request.path,

            ), 404


        return (

            "<!doctype html>"

            "<html lang='pt-BR'>"

            "<head>"

            "<meta charset='utf-8'>"

            "<meta name='viewport' "
            "content='width=device-width, "
            "initial-scale=1.0'>"

            "<title>Não encontrado</title>"

            "</head>"

            "<body>"

            "<h1>404</h1>"

            "<p>Rota não encontrada.</p>"

            "<a href='/'>Voltar</a>"

            "</body>"

            "</html>",

            404,

        )


    @app.errorhandler(405)
    def method_not_allowed(error):

        if request.path.startswith(
            "/api/"
        ):

            return jsonify(

                ok=False,

                erro="method_not_allowed",

                mensagem=(
                    "Método HTTP não permitido."
                ),

                metodo=request.method,

                rota=request.path,

            ), 405


        return (
            "Método HTTP não permitido.",
            405,
        )


    @app.errorhandler(500)
    def internal_error(error):

        logger = logging.getLogger(
            LOGGER_NAME
        )

        logger.exception(
            "Erro interno do servidor."
        )

        if request.path.startswith(
            "/api/"
        ):

            return jsonify(

                ok=False,

                erro="internal_server_error",

                mensagem=(
                    "Erro interno do servidor."
                ),

            ), 500


        return (

            "<!doctype html>"

            "<html lang='pt-BR'>"

            "<head>"

            "<meta charset='utf-8'>"

            "<title>Erro interno</title>"

            "</head>"

            "<body>"

            "<h1>Erro interno</h1>"

            "<p>"
            "O servidor encontrou um problema."
            "</p>"

            "<a href='/'>Voltar</a>"

            "</body>"

            "</html>",

            500,

        )


# ============================================================
# SESSÃO
# ============================================================

def configure_session(
    app: Flask,
) -> None:
    """
    Configura os cookies da sessão.
    """

    app.config[
        "SESSION_COOKIE_NAME"
    ] = app.config.get(
        "SESSION_COOKIE_NAME",
        "robo_ofertas_session",
    )

    app.config[
        "SESSION_COOKIE_HTTPONLY"
    ] = True

    app.config[
        "SESSION_COOKIE_SAMESITE"
    ] = app.config.get(
        "SESSION_COOKIE_SAMESITE",
        "Lax",
    )

    app.config[
        "SESSION_COOKIE_SECURE"
    ] = app.config.get(
        "SESSION_COOKIE_SECURE",
        True,
    )

    app.config[
        "PERMANENT_SESSION_LIFETIME"
    ] = app.config.get(
        "PERMANENT_SESSION_LIFETIME",
        86400,
    )


# ============================================================
# APPLICATION FACTORY
# ============================================================

def create_app(
    config_class=None,
) -> Flask:
    """
    Cria e configura a aplicação Flask.
    """

    ensure_directories()


    # --------------------------------------------------------
    # CONFIGURAÇÃO
    # --------------------------------------------------------

    if config_class is None:

        config_class = get_config()


    app = Flask(
        __name__,
        instance_relative_config=True,
    )


    app.config.from_object(
        config_class
    )


    # --------------------------------------------------------
    # GARANTIAS DE CONFIGURAÇÃO
    # --------------------------------------------------------

    if not app.config.get(
        "APP_NAME"
    ):

        app.config[
            "APP_NAME"
        ] = "Robo Ofertas PRO"


    if not app.config.get(
        "APP_VERSION"
    ):

        app.config[
            "APP_VERSION"
        ] = "10.0.0"


    if not app.config.get(
        "ENVIRONMENT"
    ):

        app.config[
            "ENVIRONMENT"
        ] = "production"


    # Guarda a classe de configuração
    # para os endpoints de diagnóstico.

    app.config[
        "_ROBO_CONFIG_CLASS"
    ] = config_class


    # --------------------------------------------------------
    # LOGGING
    # --------------------------------------------------------

    configure_logging(
        app
    )

    logger = logging.getLogger(
        LOGGER_NAME
    )


    logger.info(
        "Criando %s v%s",
        app.config.get(
            "APP_NAME"
        ),
        app.config.get(
            "APP_VERSION"
        ),
    )


    # --------------------------------------------------------
    # SESSÃO
    # --------------------------------------------------------

    configure_session(
        app
    )


    # --------------------------------------------------------
    # EXTENSÕES
    # --------------------------------------------------------

    init_extensions(
        app
    )


    # --------------------------------------------------------
    # SEGURANÇA
    # --------------------------------------------------------

    register_security_headers(
        app
    )

    register_request_tracking(
        app
    )


    # --------------------------------------------------------
    # ROTAS PRINCIPAIS
    # --------------------------------------------------------

    register_core_routes(
        app
    )


    # --------------------------------------------------------
    # AUTENTICAÇÃO MERCADO LIVRE
    #
    # IMPORTANTE:
    # Registro direto para garantir que:
    #
    # /auth/mercadolivre
    # /auth/mercadolivre/connect
    # /auth/callback
    # /auth/mercadolivre/callback
    # /api/auth/status
    #
    # estejam disponíveis.
    # --------------------------------------------------------

    register_auth_routes(
        app
    )


    logger.info(
        "Rotas de autenticação carregadas."
    )


    # --------------------------------------------------------
    # TRATAMENTO DE ERROS
    # --------------------------------------------------------

    register_error_handlers(
        app
    )


    # --------------------------------------------------------
    # OUTROS MÓDULOS
    # --------------------------------------------------------

    register_future_routes(
        app
    )


    # --------------------------------------------------------
    # DIAGNÓSTICO
    # --------------------------------------------------------

    try:

        ml_configured = (
            config_class
            .mercado_livre_configured()
        )

    except Exception:

        ml_configured = False


    logger.info(
        "Mercado Livre configurado: %s",
        ml_configured,
    )


    logger.info(
        "Aplicação inicializada."
    )


    return app


# ============================================================
# OBJETO WSGI
#
# O Render executa:
#
# gunicorn app:app
#
# Portanto a variável "app" precisa existir.
# ============================================================

app = create_app()


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            str(
                app.config.get(
                    "PORT",
                    5000,
                )
            ),
        )
    )

    host = os.getenv(
        "HOST",
        str(
            app.config.get(
                "HOST",
                "0.0.0.0",
            )
        ),
    )

    app.run(
        host=host,
        port=port,
        debug=False,
    )
