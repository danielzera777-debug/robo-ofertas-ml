import os
import secrets


def env_bool(name: str, default: bool = False) -> bool:
    """
    Lê uma variável de ambiente como booleano.
    """
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "sim",
    }


def env_int(name: str, default: int) -> int:
    """
    Lê uma variável de ambiente como inteiro.
    """
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class Config:
    """
    Configuração principal do Robo Ofertas PRO.
    """

    # ========================================================
    # APLICAÇÃO
    # ========================================================

    APP_NAME = os.getenv(
        "APP_NAME",
        "Robo Ofertas PRO",
    )

    APP_VERSION = os.getenv(
        "APP_VERSION",
        "10.0.0",
    )

    ENVIRONMENT = os.getenv(
        "ENVIRONMENT",
        "production",
    )

    DEBUG = env_bool(
        "FLASK_DEBUG",
        False,
    )

    TESTING = env_bool(
        "FLASK_TESTING",
        False,
    )

    # ========================================================
    # PORTA / SERVIDOR
    # ========================================================

    PORT = env_int(
        "PORT",
        5000,
    )

    HOST = os.getenv(
        "HOST",
        "0.0.0.0",
    )

    # ========================================================
    # CHAVE DA SESSÃO
    # ========================================================

    SECRET_KEY = os.getenv(
        "FLASK_SECRET_KEY",
        os.getenv(
            "SECRET_KEY",
            "",
        ),
    ).strip()

    # Em desenvolvimento, cria uma chave temporária.
    # Em produção, recomendamos configurar
    # FLASK_SECRET_KEY no Render.
    if not SECRET_KEY:
        SECRET_KEY = secrets.token_hex(32)

    # ========================================================
    # SESSÃO
    # ========================================================

    SESSION_COOKIE_NAME = os.getenv(
        "SESSION_COOKIE_NAME",
        "robo_ofertas_session",
    )

    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = os.getenv(
        "SESSION_COOKIE_SAMESITE",
        "Lax",
    )

    SESSION_COOKIE_SECURE = env_bool(
        "SESSION_COOKIE_SECURE",
        True,
    )

    PERMANENT_SESSION_LIFETIME = env_int(
        "SESSION_LIFETIME_SECONDS",
        86400,
    )

    # ========================================================
    # MERCADO LIVRE
    # ========================================================

    ML_CLIENT_ID = os.getenv(
        "ML_CLIENT_ID",
        "",
    ).strip()

    ML_CLIENT_SECRET = os.getenv(
        "ML_CLIENT_SECRET",
        "",
    ).strip()

    ML_REDIRECT_URI = os.getenv(
        "ML_REDIRECT_URI",
        "",
    ).strip()

    ML_SITE_ID = os.getenv(
        "ML_SITE_ID",
        "MLB",
    ).strip()

    ML_API_BASE = os.getenv(
        "ML_API_BASE",
        "https://api.mercadolibre.com",
    ).rstrip("/")

    ML_AUTH_URL = os.getenv(
        "ML_AUTH_URL",
        "https://auth.mercadolivre.com.br/authorization",
    ).strip()

    ML_OAUTH_TOKEN_URL = os.getenv(
        "ML_OAUTH_TOKEN_URL",
        "https://api.mercadolibre.com/oauth/token",
    ).strip()

    # ========================================================
    # MERCADO LIVRE — TIMEOUTS
    # ========================================================

    ML_CONNECT_TIMEOUT = env_int(
        "ML_CONNECT_TIMEOUT",
        10,
    )

    ML_READ_TIMEOUT = env_int(
        "ML_READ_TIMEOUT",
        30,
    )

    # ========================================================
    # MERCADO LIVRE — BUSCA
    # ========================================================

    ML_SEARCH_LIMIT = env_int(
        "ML_SEARCH_LIMIT",
        30,
    )

    ML_MAX_SEARCH_LIMIT = env_int(
        "ML_MAX_SEARCH_LIMIT",
        50,
    )

    # ========================================================
    # USER AGENT
    # ========================================================

    ML_USER_AGENT = os.getenv(
        "ML_USER_AGENT",
        "Robo-Ofertas-PRO/10.0",
    ).strip()

    # ========================================================
    # CACHE
    # ========================================================

    CACHE_TYPE = os.getenv(
        "CACHE_TYPE",
        "SimpleCache",
    )

    CACHE_DEFAULT_TIMEOUT = env_int(
        "CACHE_DEFAULT_TIMEOUT",
        120,
    )

    CACHE_REDIS_URL = os.getenv(
        "REDIS_URL",
        "",
    ).strip()

    # ========================================================
    # RATE LIMIT
    # ========================================================

    RATE_LIMIT_DEFAULT = os.getenv(
        "RATE_LIMIT_DEFAULT",
        "60 per minute",
    )

    RATE_LIMIT_SEARCH = os.getenv(
        "RATE_LIMIT_SEARCH",
        "30 per minute",
    )

    RATE_LIMIT_OAUTH = os.getenv(
        "RATE_LIMIT_OAUTH",
        "10 per minute",
    )

    # ========================================================
    # LOGGING
    # ========================================================

    LOG_LEVEL = os.getenv(
        "LOG_LEVEL",
        "INFO",
    ).upper()

    LOG_FILE = os.getenv(
        "LOG_FILE",
        "logs/robo-ofertas.log",
    )

    # ========================================================
    # SEGURANÇA
    # ========================================================

    SECURITY_HEADERS_ENABLED = env_bool(
        "SECURITY_HEADERS_ENABLED",
        True,
    )

    CSRF_ENABLED = env_bool(
        "CSRF_ENABLED",
        True,
    )

    # ========================================================
    # PWA
    # ========================================================

    PWA_ENABLED = env_bool(
        "PWA_ENABLED",
        True,
    )

    # ========================================================
    # WHATSAPP
    # ========================================================

    WHATSAPP_ENABLED = env_bool(
        "WHATSAPP_ENABLED",
        True,
    )

    # ========================================================
    # IMAGENS
    # ========================================================

    IMAGE_GENERATION_ENABLED = env_bool(
        "IMAGE_GENERATION_ENABLED",
        True,
    )

    IMAGE_MAX_WIDTH = env_int(
        "IMAGE_MAX_WIDTH",
        1080,
    )

    IMAGE_MAX_HEIGHT = env_int(
        "IMAGE_MAX_HEIGHT",
        1080,
    )

    # ========================================================
    # MÉTODOS AUXILIARES
    # ========================================================

    @classmethod
    def mercado_livre_configured(cls) -> bool:
        """
        Verifica se as três configurações essenciais
        do OAuth do Mercado Livre existem.
        """

        return bool(
            cls.ML_CLIENT_ID
            and cls.ML_CLIENT_SECRET
            and cls.ML_REDIRECT_URI
        )

    @classmethod
    def security_summary(cls) -> dict:
        """
        Retorna informações de segurança sem expor
        valores secretos.
        """

        return {
            "secret_key_configured": bool(
                cls.SECRET_KEY
            ),
            "session_httponly": cls.SESSION_COOKIE_HTTPONLY,
            "session_samesite": cls.SESSION_COOKIE_SAMESITE,
            "session_secure": cls.SESSION_COOKIE_SECURE,
            "csrf_enabled": cls.CSRF_ENABLED,
            "security_headers_enabled": (
                cls.SECURITY_HEADERS_ENABLED
            ),
        }

    @classmethod
    def mercado_livre_summary(cls) -> dict:
        """
        Retorna o diagnóstico da configuração do
        Mercado Livre sem revelar Client Secret.
        """

        return {
            "client_id_configured": bool(
                cls.ML_CLIENT_ID
            ),
            "client_secret_configured": bool(
                cls.ML_CLIENT_SECRET
            ),
            "redirect_uri_configured": bool(
                cls.ML_REDIRECT_URI
            ),
            "site_id": cls.ML_SITE_ID,
            "api_base": cls.ML_API_BASE,
            "oauth_configured": (
                cls.mercado_livre_configured()
            ),
        }


class DevelopmentConfig(Config):
    """
    Configuração para desenvolvimento local.
    """

    ENVIRONMENT = "development"

    DEBUG = True

    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """
    Configuração utilizada pelos testes.
    """

    ENVIRONMENT = "testing"

    TESTING = True

    DEBUG = False

    SESSION_COOKIE_SECURE = False

    CSRF_ENABLED = False


def get_config():
    """
    Seleciona automaticamente a configuração.
    """

    environment = os.getenv(
        "ENVIRONMENT",
        "production",
    ).strip().lower()

    if environment == "development":
        return DevelopmentConfig

    if environment == "testing":
        return TestingConfig

    return Config
