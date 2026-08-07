"""
Extensões compartilhadas do Robo Ofertas PRO.

Este módulo mantém as extensões separadas da criação da aplicação.
Isso evita imports circulares e facilita testes.
"""

from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


# ============================================================
# CACHE
# ============================================================

cache = Cache()


# ============================================================
# RATE LIMITER
# ============================================================

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)


# ============================================================
# INICIALIZAÇÃO
# ============================================================

def init_extensions(app):
    """
    Inicializa todas as extensões utilizando a aplicação Flask.
    """

    # --------------------------------------------------------
    # CACHE
    # --------------------------------------------------------

    cache_config = {
        "CACHE_TYPE": app.config.get(
            "CACHE_TYPE",
            "SimpleCache",
        ),
        "CACHE_DEFAULT_TIMEOUT": app.config.get(
            "CACHE_DEFAULT_TIMEOUT",
            120,
        ),
    }

    # Se Redis estiver configurado, utiliza Redis.
    redis_url = app.config.get(
        "CACHE_REDIS_URL",
        "",
    )

    if redis_url:
        cache_config.update(
            {
                "CACHE_TYPE": "RedisCache",
                "CACHE_REDIS_URL": redis_url,
            }
        )

    cache.init_app(
        app,
        config=cache_config,
    )

    # --------------------------------------------------------
    # RATE LIMITER
    # --------------------------------------------------------

    limiter.init_app(app)

    return app
