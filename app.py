"""
Robo Ofertas PRO
================

Núcleo da aplicação Flask.

Responsabilidades deste arquivo:

- criar a aplicação Flask;
- carregar configurações;
- inicializar extensões;
- registrar rotas;
- configurar segurança básica;
- disponibilizar health check;
- disponibilizar diagnóstico inicial;
- tratar erros;
- manter a aplicação preparada para crescimento.

A integração completa com Mercado Livre ficará em services/.
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
    """
    Configura o sistema de logs da aplicação.
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

    logger.setLevel(level)

    # Evita adicionar handlers duplicados
    # quando a aplicação for inicializada novamente.
    if not logger.handlers:

        console_handler = logging.StreamHandler()

        console_handler.setLevel(level)

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
    Cria os diretórios utilizados pelo projeto.
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
# SEGURANÇA — HEADERS
# ============================================================

def register_security_headers(
    app: Flask,
) -> None:
    """
    Adiciona headers básicos de segurança às respostas.

    Não substitui um firewall/WAF, mas cria uma camada
    adicional de proteção para o aplicativo.
    """

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
# REQUEST ID
# ============================================================

def register_request_tracking(
    app: Flask,
) -> None:
    """
    Adiciona um identificador simples às requisições.

    Futuramente ele será utilizado no sistema de logs
    para rastrear erros específicos.
    """

    @app.before_request
    def request_started():

        request._robo_request_started = time.time()

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
# ROTAS INTERNAS
# ============================================================

def register_core_routes(
    app: Flask,
) -> None:
    """
    Rotas fundamentais que estarão disponíveis desde
    a primeira versão.
    """

    @app.route("/")
    def home():

        connected = False

        try:

            return render_template(
                "index.html",
                connected=connected,
                app_name=app.config.get(
                    "APP_NAME"
                ),
                version=app.config.get(
                    "APP_VERSION"
                ),
            )

        except Exception:

            # Durante a montagem inicial do projeto,
            # o template pode ainda não existir.
            return jsonify(
                ok=True,
                app=app.config.get(
                    "APP_NAME"
                ),
                version=app.config.get(
                    "APP_VERSION"
                ),
                status="online",
                mensagem=(
                    "Aplicação funcionando. "
                    "Interface ainda em construção."
                ),
            )


    @app.route("/health")
    def health():

        return jsonify(
            ok=True,
            status="online",
            app=app.config.get(
                "APP_NAME"
            ),
            version=app.config.get(
                "APP_VERSION"
            ),
            environment=app.config.get(
                "ENVIRONMENT"
            ),
            timestamp=int(
                time.time()
            ),
        )


    @app.route("/api/status")
    def api_status():

        config_class = app.config.get(
            "_ROBO_CONFIG_CLASS"
        )

        if config_class:

            ml_configured = (
                config_class.mercado_livre_configured()
            )

            ml_summary = (
                config_class.mercado_livre_summary()
            )

            security_summary = (
                config_class.security_summary()
            )

        else:

            ml_configured = False

            ml_summary = {}

            security_summary = {}


        return jsonify(
            ok=True,
            application={
                "name": app.config.get(
                    "APP_NAME"
                ),
                "version": app.config.get(
                    "APP_VERSION"
                ),
                "environment": app.config.get(
                    "ENVIRONMENT"
                ),
            },
            mercado_livre={
                "configured": ml_configured,
                **ml_summary,
            },
            security=security_summary,
        )


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
# ROTAS FUTURAS
# ============================================================

def register_future_routes(
    app: Flask,
) -> None:
    """
    Local reservado para registro dos módulos.

    Conforme criarmos os arquivos:

        routes/auth.py
        routes/produtos.py
        routes/diagnostico.py
        routes/whatsapp.py
        routes/admin.py

    eles serão registrados aqui.

    O carregamento é feito de forma segura para que a aplicação
    não quebre enquanto os módulos ainda estiverem sendo criados.
    """

    modules = [
        (
            "routes.auth",
            "register_auth_routes",
        ),
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

            register_function(app)

            logger.info(
                "Módulo carregado: %s",
                module_name,
            )

        except ModuleNotFoundError:

            # Normal nesta fase do desenvolvimento:
            # os módulos ainda serão criados.
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
# TRATAMENTO 404
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
                mensagem="Rota não encontrada.",
                rota=request.path,
            ), 404

        return (
            "<!doctype html>"
            "<html lang='pt-BR'>"
            "<head>"
            "<meta charset='utf-8'>"
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
# CONFIGURAÇÃO DA SESSÃO
# ============================================================

def configure_session(
    app: Flask,
) -> None:
    """
    Configura cookies de sessão.
    """

    app.config["SESSION_COOKIE_NAME"] = (
        app.config.get(
            "SESSION_COOKIE_NAME",
            "robo_ofertas_session",
        )
    )

    app.config["SESSION_COOKIE_HTTPONLY"] = (
        True
    )

    app.config["SESSION_COOKIE_SAMESITE"] = (
        app.config.get(
            "SESSION_COOKIE_SAMESITE",
            "Lax",
        )
    )

    app.config["SESSION_COOKIE_SECURE"] = (
        app.config.get(
            "SESSION_COOKIE_SECURE",
            True,
        )
    )

    app.config["PERMANENT_SESSION_LIFETIME"] = (
        app.config.get(
            "PERMANENT_SESSION_LIFETIME",
            86400,
        )
    )


# ============================================================
# APPLICATION FACTORY
# ============================================================

def create_app(
    config_class=None,
) -> Flask:
    """
    Cria e configura uma instância da aplicação Flask.
    """

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

    # Guarda a classe para os endpoints
    # de diagnóstico.
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
    # ROTAS
    # --------------------------------------------------------

    register_core_routes(
        app
    )

    register_error_handlers(
        app
    )

    register_future_routes(
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
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":

    application = create_app()

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

    application.run(
        host=host,
        port=port,
        debug=False,
    )
