import os
import secrets


def env_bool(name: str, default: bool = False) -> bool:
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
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class Config:

    # ========================================================
    # APLICAÇÃO
    # ========================================================

    APP_NAME = os.getenv(
        "APP_NAME",
        "Robo Ofertas ML",
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
    # SERVIDOR
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
    # SEGURANÇA / SESSÃO
    # ========================================================

    SECRET_KEY = os.getenv(
        "FLASK_SECRET_KEY",
        os.getenv(
            "SECRET_KEY",
            "",
        ),
    ).strip()

    if not SECRET_KEY:
        SECRET_KEY = secrets.token_hex(32)

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

    ML_ACCESS_TOKEN = os.getenv(
        "ML_ACCESS_TOKEN",
        "",
    ).strip()

    ML_REFRESH_TOKEN = os.getenv(
        "ML_REFRESH_TOKEN",
        "",
    ).strip()

    # ========================================================
    # MERCADO LIVRE - TIMEOUT
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
    # MERCADO LIVRE - BUSCA
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
        "Robo-Ofertas-ML/10.0",
    ).strip()

    # ========================================================
    # OFERTAS
    # ========================================================

    MARGEM_PADRAO = env_int(
        "MARGEM_PADRAO",
        10,
    )

    LUCRO_MINIMO_PADRAO = env_int(
        "LUCRO_MINIMO_PADRAO",
        20,
    )

    DESCONTO_MINIMO_PADRAO = env_int(
        "DESCONTO_MINIMO_PADRAO",
        5,
    )

    LIMITE_OFERTAS = env_int(
        "LIMITE_OFERTAS",
        20,
    )

    INTERVALO_OFERTAS = env_int(
        "INTERVALO_OFERTAS",
        60,
    )

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
    # LOG
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
    # MERCADO LIVRE - VERIFICAÇÃO
    # ========================================================

    @classmethod
    def mercado_livre_configured(cls) -> bool:
        """
        Nome utilizado pelas rotas de autenticação.
        Mantido em inglês para compatibilidade.
        """

        return bool(
            cls.ML_CLIENT_ID
            and cls.ML_CLIENT_SECRET
            and cls.ML_REDIRECT_URI
        )

    @classmethod
    def mercado_livre_configurado(cls) -> bool:
        """
        Alias em português.
        """

        return cls.mercado_livre_configured()

    # ========================================================
    # RESUMO DO MERCADO LIVRE
    # ========================================================

    @classmethod
    def mercado_livre_summary(cls) -> dict:

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

            "site_id":
                cls.ML_SITE_ID,

            "api_base":
                cls.ML_API_BASE,

            "oauth_configured":
                cls.mercado_livre_configured(),
        }

    # ========================================================
    # RESUMO DE SEGURANÇA
    # ========================================================

    @classmethod
    def security_summary(cls) -> dict:

        return {

            "secret_key_configured":
                bool(cls.SECRET_KEY),

            "session_httponly":
                cls.SESSION_COOKIE_HTTPONLY,

            "session_samesite":
                cls.SESSION_COOKIE_SAMESITE,

            "session_secure":
                cls.SESSION_COOKIE_SECURE,

            "csrf_enabled":
                cls.CSRF_ENABLED,

            "security_headers_enabled":
                cls.SECURITY_HEADERS_ENABLED,

        }


class DevelopmentConfig(Config):

    ENVIRONMENT = "development"

    DEBUG = True

    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):

    ENVIRONMENT = "testing"

    TESTING = True

    DEBUG = False

    SESSION_COOKIE_SECURE = False

    CSRF_ENABLED = False


def get_config():

    environment = os.getenv(
        "ENVIRONMENT",
        "production",
    ).strip().lower()

    if environment == "development":
        return DevelopmentConfig

    if environment == "testing":
        return TestingConfig

    return Config


# ============================================================
# COMPATIBILIDADE
# ============================================================

config = Config
