"""
Constantes centrais do Robo de Ofertas ML.

Este arquivo concentra valores fixos utilizados por
diferentes partes da aplicação.
"""

# ============================================================
# APLICAÇÃO
# ============================================================

APP_NAME = "Robo de Ofertas ML"

APP_VERSION = "10.0.0"

ENVIRONMENT_PRODUCTION = "production"

ENVIRONMENT_DEVELOPMENT = "development"


# ============================================================
# MERCADO LIVRE
# ============================================================

ML_SITE_ID = "MLB"

ML_API_BASE = (
    "https://api.mercadolibre.com"
)

ML_AUTH_URL = (
    "https://auth.mercadolivre.com.br"
)

ML_OAUTH_AUTHORIZE = (
    f"{ML_AUTH_URL}/authorization"
)

ML_OAUTH_TOKEN = (
    f"{ML_API_BASE}/oauth/token"
)


# ============================================================
# LIMITES
# ============================================================

DEFAULT_OFFER_LIMIT = 20

MAX_OFFER_LIMIT = 100

DEFAULT_REQUEST_TIMEOUT = 20

DEFAULT_MAX_RETRIES = 3


# ============================================================
# OFERTAS
# ============================================================

DEFAULT_MARGIN_PERCENT = 10.0

DEFAULT_MINIMUM_PROFIT = 20.0

DEFAULT_MINIMUM_DISCOUNT = 0.0


# ============================================================
# CATEGORIAS
# ============================================================

CATEGORY_SUPPLEMENTS = (
    "suplementos"
)

CATEGORY_FITNESS_FEMALE = (
    "fitness_feminino"
)

CATEGORY_FITNESS_MALE = (
    "fitness_masculino"
)


# ============================================================
# NICHOS
# ============================================================

NICHES = {

    CATEGORY_SUPPLEMENTS: [
        "whey",
        "whey protein",
        "creatina",
        "bcaa",
        "hipercalorico",
        "hipercalórico",
        "pre treino",
        "pré treino",
        "glutamina",
        "albumina",
        "proteina",
        "proteína",
        "multivitaminico",
        "multivitamínico",
        "vitamina",
        "suplemento",
    ],

    CATEGORY_FITNESS_FEMALE: [
        "legging",
        "legging fitness",
        "conjunto fitness feminino",
        "top fitness",
        "top academia",
        "short feminino fitness",
        "short academia feminino",
        "calca fitness feminina",
        "calça fitness feminina",
        "blusa fitness feminina",
        "regata fitness feminina",
        "camiseta fitness feminina",
    ],

    CATEGORY_FITNESS_MALE: [
        "bermuda fitness",
        "bermuda academia",
        "short fitness masculino",
        "short academia masculino",
        "camiseta fitness masculina",
        "camiseta academia masculina",
        "regata fitness masculina",
        "regata academia masculina",
        "roupa fitness masculina",
        "conjunto fitness masculino",
    ],

}


# ============================================================
# CATEGORIAS MERCADO LIVRE
# ============================================================

ML_CATEGORIES = {

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
        "MLB1747",

}


# ============================================================
# HTTP
# ============================================================

HTTP_OK = 200

HTTP_CREATED = 201

HTTP_BAD_REQUEST = 400

HTTP_UNAUTHORIZED = 401

HTTP_FORBIDDEN = 403

HTTP_NOT_FOUND = 404

HTTP_TOO_MANY_REQUESTS = 429

HTTP_INTERNAL_SERVER_ERROR = 500


# ============================================================
# STATUS DE OFERTA
# ============================================================

OFFER_NEW = "nova"

OFFER_READY = "pronta"

OFFER_PUBLISHED = "publicada"

OFFER_ERROR = "erro"

OFFER_INACTIVE = "inativa"


# ============================================================
# STATUS DE PUBLICAÇÃO
# ============================================================

PUBLICATION_PENDING = "pendente"

PUBLICATION_SENT = "enviado"

PUBLICATION_ERROR = "erro"

PUBLICATION_CANCELLED = "cancelado"


# ============================================================
# CANAIS
# ============================================================

CHANNEL_WHATSAPP = "whatsapp"

CHANNEL_INSTAGRAM = "instagram"

CHANNEL_TELEGRAM = "telegram"


# ============================================================
# MENSAGENS
# ============================================================

MESSAGE_PRICE_WARNING = (
    "Preço e disponibilidade "
    "podem mudar no Mercado Livre."
)

MESSAGE_BUY_NOW = (
    "🛒 COMPRAR AGORA 👇"
)

MESSAGE_NO_OFFERS = (
    "Nenhuma oferta encontrada."
)

MESSAGE_MERCADO_LIVRE_ERROR = (
    "Não foi possível consultar "
    "o Mercado Livre."
)


# ============================================================
# SEGURANÇA
# ============================================================

DEFAULT_SESSION_COOKIE_NAME = (
    "robo_ofertas_session"
)

DEFAULT_SESSION_SAMESITE = "Lax"

DEFAULT_SESSION_LIFETIME = 86400


# ============================================================
# WHATSAPP
# ============================================================

DEFAULT_WHATSAPP_API_VERSION = (
    "v23.0"
)

WHATSAPP_API_BASE = (
    "https://graph.facebook.com"
)


# ============================================================
# ARQUIVOS
# ============================================================

GENERATED_DIRECTORY = (
    "static/generated"
)

LOG_DIRECTORY = "logs"

DATABASE_DIRECTORY = "database"


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def all_niches():
    """
    Retorna a lista de nichos disponíveis.
    """

    return list(
        NICHES.keys()
    )


def is_valid_niche(
    niche
):
    """
    Verifica se um nicho existe.
    """

    return (
        str(niche or "").strip()
        in NICHES
    )


def normalize_niche(
    niche
):
    """
    Normaliza o nome do nicho.
    """

    value = str(
        niche or ""
    ).strip().lower()

    aliases = {

        "suplemento":
            CATEGORY_SUPPLEMENTS,

        "suplementos":
            CATEGORY_SUPPLEMENTS,

        "fitness feminino":
            CATEGORY_FITNESS_FEMALE,

        "fitness_feminino":
            CATEGORY_FITNESS_FEMALE,

        "fitness feminino":
            CATEGORY_FITNESS_FEMALE,

        "fitness masculino":
            CATEGORY_FITNESS_MALE,

        "fitness_masculino":
            CATEGORY_FITNESS_MALE,

    }

    return aliases.get(
        value,
        value
    )


def get_niche_terms(
    niche
):
    """
    Retorna os termos de busca de um nicho.
    """

    niche = normalize_niche(
        niche
    )

    return list(
        NICHES.get(
            niche,
            []
        )
    )
