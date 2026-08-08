import os


class Config:

    # =========================================================
    # APLICAÇÃO
    # =========================================================

    APP_NAME = os.getenv(
        "APP_NAME",
        "Robo de Ofertas ML"
    )

    APP_ENV = os.getenv(
        "APP_ENV",
        "production"
    )

    DEBUG = (
        os.getenv(
            "DEBUG",
            "false"
        ).lower()
        in (
            "1",
            "true",
            "yes",
            "sim"
        )
    )

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "troque-esta-chave-no-render"
    )

    # =========================================================
    # MERCADO LIVRE
    # =========================================================

    ML_CLIENT_ID = os.getenv(
        "ML_CLIENT_ID",
        ""
    )

    ML_CLIENT_SECRET = os.getenv(
        "ML_CLIENT_SECRET",
        ""
    )

    ML_REDIRECT_URI = os.getenv(
        "ML_REDIRECT_URI",
        ""
    )

    ML_ACCESS_TOKEN = os.getenv(
        "ML_ACCESS_TOKEN",
        ""
    )

    ML_REFRESH_TOKEN = os.getenv(
        "ML_REFRESH_TOKEN",
        ""
    )

    ML_API_BASE = os.getenv(
        "ML_API_BASE",
        "https://api.mercadolibre.com"
    )

    API_BASE = ML_API_BASE

    ML_SITE_ID = os.getenv(
        "ML_SITE_ID",
        "MLB"
    )

    SITE_ID = ML_SITE_ID

    # =========================================================
    # CATEGORIAS
    # =========================================================

    CATEGORIAS = {

        "celulares":
            "MLB1055",

        "roupas":
            "MLB1430",

        "relogios":
            "MLB3937",

        "eletronicos":
            "MLB1000",

        "informatica":
            "MLB1648",

        "beleza":
            "MLB1246",

        "casa":
            "MLB1574",

        "esportes":
            "MLB1276",

        "ferramentas":
            "MLB1144",

        "automotivo":
            "MLB1747"

    }

    # =========================================================
    # OFERTAS
    # =========================================================

    MARGEM_PADRAO = float(
        os.getenv(
            "MARGEM_PADRAO",
            "10"
        )
    )

    LUCRO_MINIMO_PADRAO = float(
        os.getenv(
            "LUCRO_MINIMO_PADRAO",
            "20"
        )
    )

    DESCONTO_MINIMO_PADRAO = float(
        os.getenv(
            "DESCONTO_MINIMO_PADRAO",
            "0"
        )
    )

    LIMITE_OFERTAS = int(
        os.getenv(
            "LIMITE_OFERTAS",
            "20"
        )
    )

    # =========================================================
    # AGENDAMENTO
    # =========================================================

    INTERVALO_OFERTAS = int(
        os.getenv(
            "INTERVALO_OFERTAS",
            "3600"
        )
    )

    AUTO_START = (
        os.getenv(
            "AUTO_START",
            "false"
        ).lower()
        in (
            "1",
            "true",
            "yes",
            "sim"
        )
    )

    # =========================================================
    # WHATSAPP
    # =========================================================

    WHATSAPP_ACCESS_TOKEN = os.getenv(
        "WHATSAPP_ACCESS_TOKEN",
        ""
    )

    WHATSAPP_PHONE_NUMBER_ID = os.getenv(
        "WHATSAPP_PHONE_NUMBER_ID",
        ""
    )

    WHATSAPP_API_VERSION = os.getenv(
        "WHATSAPP_API_VERSION",
        "v23.0"
    )

    WHATSAPP_GROUP_ID = os.getenv(
        "WHATSAPP_GROUP_ID",
        ""
    )

    # =========================================================
    # ARQUIVOS
    # =========================================================

    GENERATED_DIR = os.getenv(
        "GENERATED_DIR",
        os.path.join(
            "static",
            "generated"
        )
    )

    # =========================================================
    # REQUISIÇÕES
    # =========================================================

    REQUEST_TIMEOUT = int(
        os.getenv(
            "REQUEST_TIMEOUT",
            "20"
        )
    )

    MAX_RETRIES = int(
        os.getenv(
            "MAX_RETRIES",
            "3"
        )
    )

    # =========================================================
    # SESSÃO
    # =========================================================

    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = os.getenv(
        "SESSION_COOKIE_SAMESITE",
        "Lax"
    )

    SESSION_COOKIE_SECURE = (
        os.getenv(
            "SESSION_COOKIE_SECURE",
            "true"
        ).lower()
        in (
            "1",
            "true",
            "yes",
            "sim"
        )
    )

    # =========================================================
    # MÉTODOS
    # =========================================================

    @classmethod
    def mercado_livre_configurado(cls):

        return bool(
            cls.ML_CLIENT_ID
            and cls.ML_CLIENT_SECRET
            and cls.ML_REDIRECT_URI
        )

    @classmethod
    def whatsapp_configurado(cls):

        return bool(
            cls.WHATSAPP_ACCESS_TOKEN
            and cls.WHATSAPP_PHONE_NUMBER_ID
        )

    @classmethod
    def resumo(cls):

        return {

            "app_name":
                cls.APP_NAME,

            "environment":
                cls.APP_ENV,

            "debug":
                cls.DEBUG,

            "mercado_livre":
                cls.mercado_livre_configurado(),

            "whatsapp":
                cls.whatsapp_configurado(),

            "site_id":
                cls.ML_SITE_ID,

            "limite_ofertas":
                cls.LIMITE_OFERTAS,

            "intervalo":
                cls.INTERVALO_OFERTAS

        }


# =============================================================
# INSTÂNCIA PRINCIPAL
# =============================================================

config = Config()


# =============================================================
# COMPATIBILIDADE COM O APP.PY
# =============================================================

def get_config():
    return Config
