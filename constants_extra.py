"""
Constantes complementares do Robo de Ofertas ML.

Este arquivo mantém configurações auxiliares separadas
das constantes principais.
"""

# ============================================================
# CACHE
# ============================================================

CACHE_DEFAULT_TIMEOUT = 300

CACHE_SEARCH_TIMEOUT = 180

CACHE_PRODUCT_TIMEOUT = 600

CACHE_DIAGNOSTIC_TIMEOUT = 60


# ============================================================
# PAGINAÇÃO
# ============================================================

DEFAULT_PAGE = 1

DEFAULT_PAGE_SIZE = 20

MAX_PAGE_SIZE = 100


# ============================================================
# BUSCA
# ============================================================

DEFAULT_SEARCH_LIMIT = 20

MAX_SEARCH_LIMIT = 100

MIN_SEARCH_TERM_LENGTH = 2

MAX_SEARCH_TERM_LENGTH = 100


# ============================================================
# MERCADO LIVRE
# ============================================================

ML_SEARCH_ENDPOINT = (
    "/sites/MLB/search"
)

ML_ITEMS_ENDPOINT = (
    "/items"
)

ML_CATEGORIES_ENDPOINT = (
    "/categories"
)

ML_USERS_ENDPOINT = (
    "/users"
)


# ============================================================
# RETENTATIVAS
# ============================================================

RETRY_STATUS_CODES = (
    408,
    429,
    500,
    502,
    503,
    504,
)

DEFAULT_RETRY_DELAY = 1

MAX_RETRY_DELAY = 10


# ============================================================
# TIMEOUTS
# ============================================================

CONNECT_TIMEOUT = 10

READ_TIMEOUT = 20

TOTAL_TIMEOUT = 30


# ============================================================
# OFERTAS
# ============================================================

MIN_PRODUCT_PRICE = 0.01

MAX_PRODUCT_PRICE = 9999999.99

MIN_SOLD_QUANTITY = 0

DEFAULT_MINIMUM_SOLD = 0


# ============================================================
# DUPLICIDADE
# ============================================================

DUPLICATE_BY_ID = "id"

DUPLICATE_BY_LINK = "link"

DUPLICATE_BY_TITLE = "titulo"


# ============================================================
# ORDENAÇÃO
# ============================================================

SORT_PRICE_ASC = "price_asc"

SORT_PRICE_DESC = "price_desc"

SORT_SOLD_DESC = "sold_desc"

SORT_RELEVANCE = "relevance"


# ============================================================
# STATUS
# ============================================================

STATUS_OK = "ok"

STATUS_ERROR = "error"

STATUS_PENDING = "pending"

STATUS_PROCESSING = "processing"

STATUS_COMPLETED = "completed"

STATUS_CANCELLED = "cancelled"


# ============================================================
# FORMATO DE RESPOSTA
# ============================================================

RESPONSE_OK = "ok"

RESPONSE_ERROR = "erro"

RESPONSE_MESSAGE = "mensagem"

RESPONSE_DATA = "dados"


# ============================================================
# LOG
# ============================================================

LOG_SEARCH = "search"

LOG_OAUTH = "oauth"

LOG_API = "api"

LOG_SECURITY = "security"

LOG_WHATSAPP = "whatsapp"

LOG_DATABASE = "database"


# ============================================================
# SEGURANÇA
# ============================================================

MAX_REQUESTS_PER_MINUTE = 60

MAX_REQUESTS_PER_HOUR = 1000

MAX_LOGIN_ATTEMPTS = 5

LOCKOUT_SECONDS = 900


# ============================================================
# WHATSAPP
# ============================================================

WHATSAPP_MAX_MESSAGE_LENGTH = 4096

WHATSAPP_MAX_RETRIES = 3


# ============================================================
# ARQUIVOS
# ============================================================

MAX_IMAGE_SIZE_MB = 10

MAX_IMAGE_SIZE_BYTES = (
    MAX_IMAGE_SIZE_MB
    * 1024
    * 1024
)

ALLOWED_IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def clamp_limit(
    value,
    default=DEFAULT_SEARCH_LIMIT,
):
    """
    Mantém um limite dentro do intervalo permitido.
    """

    try:

        value = int(value)

    except (
        TypeError,
        ValueError,
    ):

        value = default

    return max(
        1,
        min(
            value,
            MAX_SEARCH_LIMIT,
        ),
    )


def clamp_page_size(
    value,
    default=DEFAULT_PAGE_SIZE,
):
    """
    Mantém o tamanho da página dentro do limite.
    """

    try:

        value = int(value)

    except (
        TypeError,
        ValueError,
    ):

        value = default

    return max(
        1,
        min(
            value,
            MAX_PAGE_SIZE,
        ),
    )


def is_allowed_image(
    filename,
):
    """
    Verifica se a extensão da imagem é permitida.
    """

    if not filename:

        return False

    filename = str(
        filename
    ).lower()

    return filename.endswith(
        ALLOWED_IMAGE_EXTENSIONS
    )
