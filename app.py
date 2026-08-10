"""
Robo Ofertas PRO
================

Aplicação principal Flask.

Esta versão foi ajustada para o projeto atual, onde
"routes.py" é um arquivo e NÃO uma pasta "routes/".
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
# CONSTANTES
# ============================================================

LOGGER_NAME = "robo-ofertas"

BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# LOGGING
# ============================================================

def configure_logging(app: Flask) -> None:

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

    logger.setLevel(level)

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
# SEGURANÇA
# ============================================================

def register_security_headers(
    app: Flask,
) -> None:

    if not app.config.get(
        "SECURITY_HEADERS_ENABLED",
        True,
    ):
        return

    @app.after_request
    def security_headers(response):

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

    @app.before_request
    def request_started():

        request._robo_request_started = (
            time.time()
        )

    @app.after_request
    def request_finished(response):

        started = getattr(
            request,
            "_robo_request_started",
            None,
        )

        if started is not None:

            duration = (
                time.time() - started
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

    @app.route("/")
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

        except Exception as error:

            logging.getLogger(
                LOGGER_NAME
            ).exception(
                "Erro carregando index.html: %s",
                error,
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


    # --------------------------------------------------------
    # HEALTH
    # --------------------------------------------------------

    @app.route("/health")
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


    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    @app.route("/api/status")
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


        return jsonify(

            ok=True,

            application={

                "name": app.config.get(
                    "APP_NAME",
                    "Robo Ofertas PRO",
                ),

                "version": app.config.get(
                    "APP_VERSION",
                    "10.0.0",
                ),

                "environment": app.config.get(
                    "ENVIRONMENT",
                    "production",
                ),

            },

            mercado_livre={

                "configured":
                    ml_configured,

                **ml_summary,

            },

            security=
                security_summary,

        )


    # --------------------------------------------------------
    # PING
    # --------------------------------------------------------

    @app.route("/api/ping")
    def api_ping():

        return jsonify(

            ok=True,

            message="pong",

            timestamp=int(
                time.time()
            ),

        )


# ============================================================
# AUTENTICAÇÃO MERCADO LIVRE
# ============================================================

def register_auth_routes(
    app: Flask,
) -> None:

    from flask import redirect
    from flask import session
    from urllib.parse import urlencode

    logger = logging.getLogger(
        LOGGER_NAME
    )


    # --------------------------------------------------------
    # STATUS AUTH
    # --------------------------------------------------------

    @app.route(
        "/api/auth/status",
        methods=["GET"],
    )
    def auth_status():

        token = session.get(
            "access_token"
        )

        return jsonify({

            "sucesso": True,

            "conectado": bool(
                token
            ),

            "mercado_livre": bool(
                token
            ),

        })


    # --------------------------------------------------------
    # LOGIN MERCADO LIVRE
    # --------------------------------------------------------

    @app.route(
        "/auth/mercadolivre",
        methods=["GET"],
    )
    @app.route(
        "/login",
        methods=["GET"],
    )
    def auth_mercadolivre():

        client_id = app.config.get(
            "ML_CLIENT_ID",
            "",
        )

        redirect_uri = app.config.get(
            "ML_REDIRECT_URI",
            "",
        )

        auth_url = app.config.get(
            "ML_AUTH_URL",
            "https://auth.mercadolivre.com.br/authorization",
        )

        if not client_id:

            return jsonify({

                "sucesso": False,

                "erro":
                    "ML_CLIENT_ID não configurado.",

                "mensagem":
                    (
                        "Configure ML_CLIENT_ID "
                        "nas variáveis de ambiente "
                        "do Render."
                    ),

            }), 500


        if not redirect_uri:

            return jsonify({

                "sucesso": False,

                "erro":
                    "ML_REDIRECT_URI não configurado.",

                "mensagem":
                    (
                        "Configure ML_REDIRECT_URI "
                        "nas variáveis de ambiente "
                        "do Render."
                    ),

            }), 500


        params = {

            "response_type":
                "code",

            "client_id":
                client_id,

            "redirect_uri":
                redirect_uri,

        }

        url = (
            auth_url
            +
            "?"
            +
            urlencode(params)
        )

        logger.info(
            "Iniciando autenticação Mercado Livre."
        )

        return redirect(
            url
        )


    # --------------------------------------------------------
    # LOGOUT
    # --------------------------------------------------------

    @app.route(
        "/logout",
        methods=["GET"],
    )
    def logout():

        session.pop(
            "access_token",
            None,
        )

        session.pop(
            "refresh_token",
            None,
        )

        session.pop(
            "user_id",
            None,
        )

        return redirect(
            "/"
        )


# ============================================================
# REGISTRAR ROTAS DO routes.py
# ============================================================

def register_existing_routes(
    app: Flask,
) -> None:
    """
    O projeto atual possui routes.py como ARQUIVO.

    Portanto NÃO fazemos:

        from routes.auth import ...

    e NÃO fazemos:

        import routes.auth

    Aqui carregamos somente o blueprint existente
    dentro de routes.py.
    """

    logger = logging.getLogger(
        LOGGER_NAME
    )

    try:

        import routes as routes_module

        blueprint = getattr(
            routes_module,
            "routes",
            None,
        )

        if blueprint is None:

            logger.warning(
                "routes.py encontrado, "
                "mas o blueprint 'routes' não existe."
            )

            return

        app.register_blueprint(
            blueprint
        )

        logger.info(
            "Blueprint routes.py registrado."
        )

    except ModuleNotFoundError:

        logger.warning(
            "routes.py não encontrado. "
            "A aplicação continuará funcionando "
            "com as rotas principais."
        )

    except Exception:

        logger.exception(
            "Erro ao registrar routes.py."
        )

        # Não derruba o servidor durante o boot.
        # O objetivo é permitir que o Render
        # continue online enquanto corrigimos
        # módulos individuais.


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

                mensagem=
                    "Rota não encontrada.",

                rota=request.path,

            ), 404

        return (

            "<!doctype html>"
            "<html lang='pt-BR'>"
            "<head>"
            "<meta charset='utf-8'>"
            "<meta name='viewport' "
            "content='width=device-width,initial-scale=1'>"
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

                erro=
                    "method_not_allowed",

                mensagem=
                    "Método HTTP não permitido.",

                metodo=
                    request.method,

                rota=
                    request.path,

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

                erro=
                    "internal_server_error",

                mensagem=
                    "Erro interno do servidor.",

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

    ensure_directories()

    if config_class is None:

        config_class = get_config()

    app = Flask(
        __name__,
        instance_relative_config=True,
    )

    # --------------------------------------------------------
    # CONFIGURAÇÃO
    # --------------------------------------------------------

    app.config.from_object(
        config_class
    )

    app.config[
        "_ROBO_CONFIG_CLASS"
    ] = config_class

    # --------------------------------------------------------
    # LOG
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
            "APP_NAME",
            "Robo Ofertas PRO",
        ),
        app.config.get(
            "APP_VERSION",
            "10.0.0",
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
    # AUTENTICAÇÃO
    # --------------------------------------------------------

    register_auth_routes(
        app
    )

    # --------------------------------------------------------
    # BLUEPRINT EXISTENTE
    # --------------------------------------------------------

    register_existing_routes(
        app
    )

    # --------------------------------------------------------
    # ERROS
    # --------------------------------------------------------

    register_error_handlers(
        app
    )

    # --------------------------------------------------------
    # LOG FINAL
    # --------------------------------------------------------

    logger.info(
        "Aplicação inicializada."
    )

    return app


# ============================================================
# INSTÂNCIA GLOBAL PARA GUNICORN
# ============================================================

app = create_app()


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

    app.run(
        host=host,
        port=port,
        debug=False,
    )
