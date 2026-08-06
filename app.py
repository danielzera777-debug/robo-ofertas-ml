import os
import time
import secrets
import hashlib
import base64
import logging
from urllib.parse import urlencode, quote

import requests
from flask import (
    Flask,
    request,
    session,
    redirect,
    jsonify,
    render_template_string,
)


# ============================================================
# APLICAÇÃO
# ============================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    secrets.token_hex(32)
)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("robo-ofertas")


# ============================================================
# MERCADO LIVRE
# ============================================================

CLIENT_ID = os.getenv("ML_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET", "").strip()
REDIRECT_URI = os.getenv("ML_REDIRECT_URI", "").strip()

API_BASE = "https://api.mercadolibre.com"

AUTH_URL = (
    "https://auth.mercadolivre.com.br/authorization"
)

SITE_ID = "MLB"

VERSION = "8.1.0"


# ============================================================
# TOKENS
# ============================================================

ACCESS_TOKEN = None
REFRESH_TOKEN_VALUE = None
TOKEN_EXPIRES_AT = 0


# ============================================================
# NICHOS
# ============================================================

NICHOS = {

    "suplementos": {
        "nome": "🥤 Suplementos",
        "termos": [
            "whey protein",
            "whey",
            "creatina",
            "creatina monohidratada",
            "pre treino",
            "pré treino",
            "hipercalorico",
            "hipercalórico",
            "bcaa",
            "glutamina",
            "multivitaminico",
            "multivitamínico",
            "barra proteica",
            "proteina",
            "proteína",
            "shaker",
            "albumina",
            "caseina",
            "caseína",
            "colageno",
            "colágeno",
            "termogenico",
            "termogênico",
            "omega 3",
            "vitamina d",
            "vitamina c",
            "zinco",
            "magnésio",
        ],
    },

    "fitness_feminino": {
        "nome": "👩 Fitness Feminino",
        "termos": [
            "legging feminina academia",
            "top fitness feminino",
            "conjunto fitness feminino",
            "conjunto academia feminino",
            "short fitness feminino",
            "short feminino academia",
            "cropped fitness feminino",
            "macacao fitness feminino",
            "macacão fitness feminino",
            "calca fitness feminina",
            "calça fitness feminina",
            "camiseta fitness feminina",
            "blusa fitness feminina",
            "jaqueta fitness feminina",
            "bermuda fitness feminina",
            "regata fitness feminina",
            "top academia feminino",
            "body fitness feminino",
        ],
    },

    "fitness_masculino": {
        "nome": "👨 Fitness Masculino",
        "termos": [
            "camiseta dry fit masculina",
            "camiseta academia masculina",
            "regata academia masculina",
            "bermuda fitness masculina",
            "short academia masculino",
            "calca fitness masculina",
            "calça fitness masculina",
            "conjunto fitness masculino",
            "camiseta compressao masculina",
            "camiseta compressão masculina",
            "blusa academia masculina",
            "jaqueta fitness masculina",
            "regata fitness masculina",
            "short fitness masculino",
            "bermuda academia masculina",
        ],
    },
}


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def num(valor, default=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return default


def integer(valor, default=20):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return default


def money(valor):
    valor = num(valor)

    return (
        f"R$ {valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


# ============================================================
# TOKEN
# ============================================================

def get_access_token():
    global ACCESS_TOKEN

    if ACCESS_TOKEN:
        return ACCESS_TOKEN

    ACCESS_TOKEN = session.get("access_token")

    return ACCESS_TOKEN


def save_tokens(data):
    global ACCESS_TOKEN
    global REFRESH_TOKEN_VALUE
    global TOKEN_EXPIRES_AT

    ACCESS_TOKEN = data.get("access_token")

    REFRESH_TOKEN_VALUE = (
        data.get("refresh_token")
        or session.get("refresh_token")
    )

    expires = integer(
        data.get("expires_in", 21600),
        21600,
    )

    TOKEN_EXPIRES_AT = (
        time.time()
        + max(60, expires - 120)
    )

    if ACCESS_TOKEN:
        session["access_token"] = ACCESS_TOKEN

    if REFRESH_TOKEN_VALUE:
        session["refresh_token"] = REFRESH_TOKEN_VALUE

    session["token_expires_at"] = TOKEN_EXPIRES_AT
    session.modified = True


def refresh_access_token():
    global REFRESH_TOKEN_VALUE

    refresh = (
        REFRESH_TOKEN_VALUE
        or session.get("refresh_token")
    )

    if not refresh:
        return False

    if not CLIENT_ID or not CLIENT_SECRET:
        return False

    try:
        response = requests.post(
            f"{API_BASE}/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": refresh,
            },
            timeout=25,
        )

    except requests.RequestException as error:
        logger.error(
            "Erro ao renovar token: %s",
            error,
        )
        return False

    if response.status_code != 200:
        logger.warning(
            "Refresh recusado: HTTP %s - %s",
            response.status_code,
            response.text[:500],
        )
        return False

    try:
        save_tokens(response.json())
        return True

    except Exception as error:
        logger.exception(
            "Erro salvando token renovado: %s",
            error,
        )
        return False


def valid_token():
    current = get_access_token()

    if not current:
        return None

    stored_expiration = num(
        session.get("token_expires_at"),
        0,
    )

    global TOKEN_EXPIRES_AT

    if not TOKEN_EXPIRES_AT and stored_expiration:
        TOKEN_EXPIRES_AT = stored_expiration

    if (
        TOKEN_EXPIRES_AT
        and time.time() >= TOKEN_EXPIRES_AT
    ):
        if not refresh_access_token():
            return None

    return get_access_token()


# ============================================================
# HEADERS API
# ============================================================

def api_headers(auth=True):

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Robo-Ofertas-ML/8.1.0",
    }

    if auth:
        current = valid_token()

        if current:
            headers["Authorization"] = (
                f"Bearer {current}"
            )

    return headers


# ============================================================
# OAUTH PKCE
# ============================================================

def oauth_login():

    if not CLIENT_ID:
        return None, (
            "Configure ML_CLIENT_ID no Render."
        )

    if not CLIENT_SECRET:
        return None, (
            "Configure ML_CLIENT_SECRET no Render."
        )

    if not REDIRECT_URI:
        return None, (
            "Configure ML_REDIRECT_URI no Render."
        )

    state = secrets.token_urlsafe(32)

    verifier = secrets.token_urlsafe(64)

    digest = hashlib.sha256(
        verifier.encode("utf-8")
    ).digest()

    challenge = (
        base64.urlsafe_b64encode(digest)
        .decode("utf-8")
        .rstrip("=")
    )

    session["oauth_state"] = state
    session["code_verifier"] = verifier

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }

    return (
        AUTH_URL
        + "?"
        + urlencode(params),
        None,
    )


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classify(title, fallback=None):

    text = str(title or "").lower()

    supplement_words = [
        "whey",
        "creatina",
        "pré treino",
        "pre treino",
        "hipercalórico",
        "hipercalorico",
        "bcaa",
        "glutamina",
        "multivitamínico",
        "multivitaminico",
        "proteína",
        "proteina",
        "barra proteica",
        "albumina",
        "caseína",
        "caseina",
        "colágeno",
        "colageno",
        "termogênico",
        "termogenico",
        "ômega 3",
        "omega 3",
    ]

    female_words = [
        "legging feminina",
        "top fitness",
        "conjunto fitness feminino",
        "conjunto academia feminino",
        "short feminino",
        "cropped fitness",
        "macacão fitness",
        "macacao fitness",
        "calça fitness feminina",
        "calca fitness feminina",
        "top academia feminino",
        "bermuda fitness feminina",
    ]

    male_words = [
        "camiseta masculina",
        "dry fit masculina",
        "regata masculina",
        "bermuda masculina",
        "short masculino",
        "calça fitness masculina",
        "calca fitness masculina",
        "conjunto fitness masculino",
        "compressão masculina",
        "compressao masculina",
        "camiseta academia masculina",
    ]

    if any(word in text for word in supplement_words):
        return "suplementos"

    if any(word in text for word in female_words):
        return "fitness_feminino"

    if any(word in text for word in male_words):
        return "fitness_masculino"

    return fallback


# ============================================================
# TEXTO WHATSAPP
# ============================================================

def whatsapp_text(
    title,
    price,
    link,
    category,
):

    if category == "suplementos":
        head = "🥤 OFERTA DE SUPLEMENTO"
        icon = "💪"

    elif category == "fitness_feminino":
        head = "👩 OFERTA FITNESS FEMININA"
        icon = "👟"

    else:
        head = "👨 OFERTA FITNESS MASCULINA"
        icon = "🏋️"

    return (
        f"🔥 {head} 🔥\n\n"
        f"{icon} {title}\n\n"
        f"💰 Por apenas: {money(price)}\n\n"
        f"🛒 COMPRAR AGORA 👇\n"
        f"{link}\n\n"
        "⚠️ Preço e disponibilidade "
        "podem mudar no Mercado Livre."
    )


# ============================================================
# TRANSFORMA PRODUTO
# ============================================================

def transform(item, fallback=None):

    if not isinstance(item, dict):
        return None

    title = str(
        item.get("title") or ""
    ).strip()

    price = num(item.get("price"))

    link = str(
        item.get("permalink") or ""
    ).strip()

    if not title or price <= 0:
        return None

    category = classify(
        title,
        fallback,
    )

    if not category:
        return None

    shipping = (
        item.get("shipping")
        or {}
    )

    seller = (
        item.get("seller")
        or {}
    )

    return {
        "id": item.get("id"),
        "titulo": title,
        "preco": price,
        "preco_formatado": money(price),
        "imagem": (
            item.get("thumbnail")
            or ""
        ),
        "link": link,
        "categoria": category,
        "vendidos": integer(
            item.get("sold_quantity"),
            0,
        ),
        "condicao": (
            item.get("condition")
            or ""
        ),
        "frete_gratis": bool(
            shipping.get("free_shipping")
        ),
        "vendedor_id": seller.get("id"),
        "whatsapp": whatsapp_text(
            title,
            price,
            link,
            category,
        ),
    }


# ============================================================
# ORDENAÇÃO
# ============================================================

def sort_products(products):

    return sorted(
        products,
        key=lambda item: (
            integer(
                item.get("vendidos"),
                0,
            ),
            -num(
                item.get("preco"),
                0,
            ),
        ),
        reverse=True,
    )


# ============================================================
# BUSCA MERCADO LIVRE
# ============================================================

def search_ml(term, limit=20):

    term = str(term or "").strip()

    if not term:
        return [], {
            "status": 400,
            "mensagem": "Termo de busca vazio.",
            "resposta": "",
        }

    limit = max(
        1,
        min(integer(limit, 20), 50),
    )

    url = (
        f"{API_BASE}/sites/"
        f"{SITE_ID}/search"
    )

    params = {
        "q": term,
        "limit": limit,
        "offset": 0,
    }

    def do_request():

        try:
            return requests.get(
                url,
                params=params,
                headers=api_headers(True),
                timeout=25,
            )

        except requests.RequestException as error:

            logger.error(
                "Erro de conexão na busca '%s': %s",
                term,
                error,
            )

            return None

    response = do_request()

    if response is None:
        return [], {
            "status": 502,
            "mensagem": (
                "Não foi possível conectar "
                "ao Mercado Livre."
            ),
            "resposta": "",
        }

    if response.status_code == 200:

        try:
            data = response.json()

        except ValueError:
            return [], {
                "status": 502,
                "mensagem": (
                    "Mercado Livre retornou "
                    "resposta inválida."
                ),
                "resposta": response.text[:1000],
            }

        results = data.get(
            "results",
            [],
        )

        if not isinstance(results, list):
            results = []

        return results, None

    # --------------------------------------------------------
    # TOKEN EXPIRADO
    # --------------------------------------------------------

    if response.status_code == 401:

        logger.warning(
            "Token recusado. Tentando renovar."
        )

        if refresh_access_token():

            response = do_request()

            if response is not None:
                if response.status_code == 200:

                    try:
                        data = response.json()

                    except ValueError:
                        return [], {
                            "status": 502,
                            "mensagem": (
                                "Resposta inválida "
                                "após renovar token."
                            ),
                            "resposta": (
                                response.text[:1000]
                            ),
                        }

                    results = data.get(
                        "results",
                        [],
                    )

                    if not isinstance(
                        results,
                        list,
                    ):
                        results = []

                    return results, None

        return [], {
            "status": 401,
            "mensagem": (
                "O token do Mercado Livre "
                "foi recusado. "
                "Conecte novamente."
            ),
            "resposta": response.text[:1000],
        }

    # --------------------------------------------------------
    # 403
    # --------------------------------------------------------

    if response.status_code == 403:

        logger.error(
            "Mercado Livre retornou 403 "
            "na busca '%s': %s",
            term,
            response.text[:1000],
        )

        return [], {
            "status": 403,
            "mensagem": (
                "O Mercado Livre recusou "
                "a consulta (HTTP 403). "
                "O problema está na autorização "
                "da aplicação/token ou no acesso "
                "ao endpoint."
            ),
            "resposta": response.text[:1000],
        }

    return [], {
        "status": response.status_code,
        "mensagem": (
            "Mercado Livre retornou "
            f"HTTP {response.status_code}."
        ),
        "resposta": response.text[:1000],
    }


# ============================================================
# BUSCA DE TERMO
# ============================================================

def search_term(
    term,
    category=None,
    limit=20,
):

    results, error = search_ml(
        term,
        limit,
    )

    if error:
        return [], error

    products = []
    seen = set()

    for item in results:

        product = transform(
            item,
            category,
        )

        if not product:
            continue

        product_id = product.get("id")

        if product_id and product_id in seen:
            continue

        if product_id:
            seen.add(product_id)

        products.append(product)

    return products, None


# ============================================================
# BUSCA POR CATEGORIA
# ============================================================

def search_category(
    category,
    limit=30,
):

    if category not in NICHOS:

        return [], {
            "status": 400,
            "mensagem": "Categoria não encontrada.",
            "resposta": "",
        }

    limit = max(
        1,
        min(integer(limit, 30), 100),
    )

    products = []
    seen = set()
    first_error = None

    for term in NICHOS[category]["termos"]:

        results, error = search_term(
            term,
            category,
            min(20, limit),
        )

        if error:

            if first_error is None:
                first_error = error

            if error.get("status") in (
                401,
                403,
            ):
                return [], error

            continue

        for product in results:

            product_id = product.get("id")

            if product_id in seen:
                continue

            seen.add(product_id)
            products.append(product)

            if len(products) >= limit:

                return (
                    sort_products(products),
                    None,
                )

    if products:
        return (
            sort_products(products),
            None,
        )

    return [], first_error


# ============================================================
# BUSCA TODAS
# ============================================================

def search_all(limit=30):

    limit = max(
        1,
        min(integer(limit, 30), 100),
    )

    products = []
    seen = set()
    first_error = None

    each = max(
        5,
        limit // max(len(NICHOS), 1),
    )

    for category in NICHOS:

        results, error = search_category(
            category,
            each,
        )

        if error:

            if first_error is None:
                first_error = error

            if error.get("status") in (
                401,
                403,
            ):
                return [], error

        for product in results:

            product_id = product.get("id")

            if product_id in seen:
                continue

            seen.add(product_id)
            products.append(product)

            if len(products) >= limit:
                return (
                    sort_products(products),
                    None,
                )

    if products:
        return (
            sort_products(products),
            None,
        )

    return [], first_error


# ============================================================
# HOME — UMA ÚNICA ROTA
# ============================================================

@app.route("/")
def home_page():

    connected = bool(valid_token())

    return render_template_string(
        INDEX_HTML,
        connected=connected,
        version=VERSION,
        niches=NICHOS,
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login")
def login_page():

    url, error = oauth_login()

    if error:
        return (
            f"<h2>Erro de configuração</h2>"
            f"<p>{error}</p>",
            500,
        )

    return redirect(url)


# ============================================================
# CALLBACK OAUTH
# ============================================================

@app.route("/callback")
def oauth_callback():

    oauth_error = request.args.get("error")

    if oauth_error:

        description = request.args.get(
            "error_description",
            oauth_error,
        )

        return (
            "<h2>Erro no Mercado Livre</h2>"
            f"<p>{description}</p>",
            400,
        )

    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        return (
            "Código OAuth não recebido.",
            400,
        )

    saved_state = session.get("oauth_state")

    if not saved_state or state != saved_state:

        return (
            "Sessão OAuth inválida ou expirada. "
            "Tente conectar novamente.",
            400,
        )

    verifier = session.get("code_verifier")

    if not verifier:

        return (
            "code_verifier não encontrado. "
            "Tente conectar novamente.",
            400,
        )

    try:

        response = requests.post(
            f"{API_BASE}/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": verifier,
            },
            timeout=25,
        )

    except requests.RequestException as error:

        logger.exception(
            "Erro OAuth"
        )

        return (
            f"Erro de conexão com Mercado Livre: {error}",
            502,
        )

    if response.status_code != 200:

        logger.error(
            "OAuth recusado: %s",
            response.text[:2000],
        )

        return (
            "<h2>Mercado Livre recusou o login</h2>"
            "<pre>"
            f"{response.text[:2000]}"
            "</pre>",
            400,
        )

    try:

        save_tokens(response.json())

    except Exception as error:

        logger.exception(
            "Erro salvando token"
        )

        return (
            f"Erro salvando token: {error}",
            500,
        )

    session.pop("oauth_state", None)
    session.pop("code_verifier", None)

    return redirect("/")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout_page():

    global ACCESS_TOKEN
    global REFRESH_TOKEN_VALUE
    global TOKEN_EXPIRES_AT

    ACCESS_TOKEN = None
    REFRESH_TOKEN_VALUE = None
    TOKEN_EXPIRES_AT = 0

    session.clear()

    return redirect("/")


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health_check():

    return jsonify(
        ok=True,
        app="Robo de Ofertas",
        versao=VERSION,
        status="online",
    )


# ============================================================
# DIAGNÓSTICO
# ============================================================

@app.route("/diagnostico")
def diagnostic_page():

    return jsonify(
        ok=True,
        app="Robo de Ofertas",
        versao=VERSION,
        mercado_livre=bool(valid_token()),
        ml_client_id=bool(CLIENT_ID),
        ml_client_secret=bool(CLIENT_SECRET),
        ml_redirect_uri=bool(REDIRECT_URI),
        categorias=list(NICHOS.keys()),
    )


# ============================================================
# STATUS
# ============================================================

@app.route("/api/status")
def api_status():

    return jsonify(
        ok=True,
        app="Robo de Ofertas",
        versao=VERSION,
        mercado_livre=bool(valid_token()),
        categorias=list(NICHOS.keys()),
    )


# ============================================================
# BUSCA
# ============================================================

@app.route("/api/buscar")
def api_search():

    term = request.args.get(
        "q",
        "",
    ).strip()

    category = request.args.get(
        "categoria",
        "todos",
    ).strip().lower()

    limit = integer(
        request.args.get(
            "limite",
            30,
        ),
        30,
    )

    if not term:

        return jsonify(
            ok=False,
            mensagem="Informe o produto para buscar.",
            produtos=[],
        ), 400

    if (
        category not in (
            "todos",
            "todas",
            "",
        )
        and category not in NICHOS
    ):

        return jsonify(
            ok=False,
            mensagem="Categoria inválida.",
            produtos=[],
        ), 400

    selected_category = (
        None
        if category in (
            "todos",
            "todas",
            "",
        )
        else category
    )

    products, error = search_term(
        term,
        selected_category,
        limit,
    )

    if error:

        status_code = integer(
            error.get("status"),
            502,
        )

        if not 400 <= status_code <= 599:
            status_code = 502

        return jsonify(
            ok=False,
            quantidade=0,
            produtos=[],
            mensagem=error.get(
                "mensagem",
                "Erro ao consultar o Mercado Livre.",
            ),
            status_mercado_livre=status_code,
            detalhes=error.get(
                "resposta",
                "",
            ),
        ), status_code

    return jsonify(
        ok=True,
        quantidade=len(products),
        produtos=products,
    )


# ============================================================
# OFERTAS
# ============================================================

@app.route("/ofertas/<category>")
def category_offers(category):

    category = category.lower().strip()

    if category not in NICHOS:

        return jsonify(
            ok=False,
            mensagem="Categoria não encontrada.",
            produtos=[],
        ), 404

    limit = integer(
        request.args.get(
            "limite",
            30,
        ),
        30,
    )

    products, error = search_category(
        category,
        limit,
    )

    if error:

        status_code = integer(
            error.get("status"),
            502,
        )

        if not 400 <= status_code <= 599:
            status_code = 502

        return jsonify(
            ok=False,
            quantidade=0,
            produtos=[],
            categoria=category,
            mensagem=error.get(
                "mensagem",
                "Erro ao consultar o Mercado Livre.",
            ),
            status_mercado_livre=status_code,
            detalhes=error.get(
                "resposta",
                "",
            ),
        ), status_code

    return jsonify(
        ok=True,
        categoria=category,
        nome_categoria=NICHOS[category]["nome"],
        quantidade=len(products),
        produtos=products,
    )


# ============================================================
# MELHORES OFERTAS
# ============================================================

@app.route("/melhores")
def best_offers():

    category = request.args.get(
        "categoria",
        "todos",
    ).lower().strip()

    limit = integer(
        request.args.get(
            "limite",
            30,
        ),
        30,
    )

    if category in (
        "todos",
        "todas",
        "",
    ):

        products, error = search_all(limit)

    elif category in NICHOS:

        products, error = search_category(
            category,
            limit,
        )

    else:

        return jsonify(
            ok=False,
            mensagem="Categoria inválida.",
            produtos=[],
        ), 400

    if error:

        status_code = integer(
            error.get("status"),
            502,
        )

        if not 400 <= status_code <= 599:
            status_code = 502

        return jsonify(
            ok=False,
            quantidade=0,
            produtos=[],
            categoria=category,
            mensagem=error.get(
                "mensagem",
                "Erro ao consultar o Mercado Livre.",
            ),
            status_mercado_livre=status_code,
            detalhes=error.get(
                "resposta",
                "",
            ),
        ), status_code

    return jsonify(
        ok=True,
        categoria=category,
        quantidade=len(products),
        produtos=products,
    )


# ============================================================
# WHATSAPP
# ============================================================

@app.route("/api/whatsapp")
def whatsapp_api():

    title = request.args.get(
        "titulo",
        "Oferta Fitness",
    )

    price = num(
        request.args.get(
            "preco",
            0,
        )
    )

    link = request.args.get(
        "link",
        "",
    )

    category = request.args.get(
        "categoria",
        "suplementos",
    )

    if not link:

        return jsonify(
            ok=False,
            mensagem="Link não informado.",
        ), 400

    text = whatsapp_text(
        title,
        price,
        link,
        category,
    )

    return jsonify(
        ok=True,
        mensagem=text,
        whatsapp_url=(
            "https://wa.me/?text="
            + quote(text)
        ),
    )


# ============================================================
# USUÁRIO MERCADO LIVRE
# ============================================================

@app.route("/api/me")
def api_me():

    current = valid_token()

    if not current:

        return jsonify(
            ok=False,
            mercado_livre=False,
            mensagem="Mercado Livre não conectado.",
        ), 401

    try:

        response = requests.get(
            f"{API_BASE}/users/me",
            headers=api_headers(True),
            timeout=25,
        )

    except requests.RequestException as error:

        return jsonify(
            ok=False,
            mensagem=str(error),
        ), 502

    if response.status_code == 401:

        if refresh_access_token():

            try:

                response = requests.get(
                    f"{API_BASE}/users/me",
                    headers=api_headers(True),
                    timeout=25,
                )

            except requests.RequestException as error:

                return jsonify(
                    ok=False,
                    mensagem=str(error),
                ), 502

        else:

            return jsonify(
                ok=False,
                mercado_livre=False,
                mensagem=(
                    "Token expirado. "
                    "Conecte novamente."
                ),
            ), 401

    if response.status_code != 200:

        return jsonify(
            ok=False,
            mercado_livre=True,
            status=response.status_code,
            mensagem=(
                "Mercado Livre recusou "
                "a consulta."
            ),
            resposta=response.text[:2000],
        ), response.status_code

    try:
        data = response.json()
    except ValueError:
        data = {}

    return jsonify(
        ok=True,
        mercado_livre=True,
        dados=data,
    )


# ============================================================
# TESTE DE BUSCA
# ============================================================

@app.route("/api/teste-busca")
def test_search():

    term = request.args.get(
        "q",
        "whey protein",
    ).strip()

    products, error = search_term(
        term,
        "suplementos",
        10,
    )

    if error:

        status_code = integer(
            error.get("status"),
            502,
        )

        if not 400 <= status_code <= 599:
            status_code = 502

        return jsonify(
            ok=False,
            teste=True,
            termo=term,
            produtos=[],
            mensagem=error.get(
                "mensagem",
                "Erro na busca.",
            ),
            status_mercado_livre=status_code,
            detalhes=error.get(
                "resposta",
                "",
            ),
        ), status_code

    return jsonify(
        ok=True,
        teste=True,
        termo=term,
        quantidade=len(products),
        produtos=products,
    )


# ============================================================
# ERROS
# ============================================================

@app.errorhandler(404)
def handle_404(error):

    if (
        request.path.startswith("/api/")
        or request.path.startswith("/ofertas/")
    ):

        return jsonify(
            ok=False,
            mensagem="Rota não encontrada.",
            rota=request.path,
        ), 404

    return (
        "<h2>Rota não encontrada</h2>"
        "<a href='/'>Voltar</a>",
        404,
    )


@app.errorhandler(500)
def handle_500(error):

    logger.exception(
        "Erro interno"
    )

    if (
        request.path.startswith("/api/")
        or request.path.startswith("/ofertas/")
    ):

        return jsonify(
            ok=False,
            mensagem="Erro interno do servidor.",
        ), 500

    return (
        "<h2>Erro interno</h2>"
        "<a href='/'>Voltar</a>",
        500,
    )
    # ============================================================
# ROBO DE OFERTAS ML 8.0
# PARTE 2/2
# ROTAS + API + INTERFACE + SERVIDOR
#
# IMPORTANTE:
# NÃO EXISTE outra função "home" nesta parte.
# Isso evita:
# AssertionError: View function mapping is overwriting
# an existing endpoint function: home
# ============================================================


# ============================================================
# FUNÇÃO AUXILIAR PARA ERROS DA API
# ============================================================

def api_error_response(error, fallback="Erro ao consultar o Mercado Livre."):
    """
    Converte o erro interno em uma resposta JSON padronizada.
    """

    if not isinstance(error, dict):
        error = {}

    status_code = integer(
        error.get("status"),
        502
    )

    if status_code < 400 or status_code > 599:
        status_code = 502

    return jsonify(
        ok=False,
        quantidade=0,
        produtos=[],
        mensagem=error.get(
            "mensagem",
            fallback
        ),
        status_mercado_livre=status_code,
        detalhes=error.get(
            "resposta",
            ""
        )
    ), status_code


# ============================================================
# ROTA PRINCIPAL
#
# ATENÇÃO:
# O endpoint chama "painel_80", NÃO "home".
# ============================================================

@app.route("/", endpoint="painel_80")
def painel_80():

    connected = bool(
        valid_token()
    )

    return render_template_string(
        INDEX_HTML,
        connected=connected,
        version=VERSION,
        niches=NICHOS
    )


# ============================================================
# LOGIN MERCADO LIVRE
# ============================================================

@app.route("/login", endpoint="login_80")
def login_80():

    url, error = oauth_login()

    if error:

        return (
            "<!doctype html>"
            "<html lang='pt-BR'>"
            "<meta charset='utf-8'>"
            "<meta name='viewport' "
            "content='width=device-width,initial-scale=1'>"
            "<body style='font-family:Arial;padding:30px'>"
            "<h2>Erro de configuração</h2>"
            "<p>"
            + escapar(error)
            + "</p>"
            "<p>Verifique as variáveis do Render.</p>"
            "<a href='/'>Voltar</a>"
            "</body>"
            "</html>",
            500
        )

    return redirect(url)


# ============================================================
# CALLBACK OAUTH
# ============================================================

@app.route("/callback", endpoint="callback_80")
def callback_80():

    oauth_error = request.args.get("error")

    if oauth_error:

        description = request.args.get(
            "error_description",
            oauth_error
        )

        return (
            "<!doctype html>"
            "<html lang='pt-BR'>"
            "<meta charset='utf-8'>"
            "<meta name='viewport' "
            "content='width=device-width,initial-scale=1'>"
            "<body style='font-family:Arial;padding:30px'>"
            "<h2>Mercado Livre recusou o login</h2>"
            "<p>"
            + escapar(description)
            + "</p>"
            "<a href='/login'>Tentar novamente</a>"
            "</body>"
            "</html>",
            400
        )


    code = request.args.get("code")

    state = request.args.get("state")


    if not code:

        return (
            "Código OAuth não recebido.",
            400
        )


    saved_state = session.get(
        "oauth_state"
    )


    if not saved_state:

        return (
            "Sessão OAuth expirada. "
            "Inicie o login novamente.",
            400
        )


    if state != saved_state:

        return (
            "Estado OAuth inválido. "
            "Tente conectar novamente.",
            400
        )


    verifier = session.get(
        "code_verifier"
    )


    if not verifier:

        return (
            "code_verifier não encontrado. "
            "Tente conectar novamente.",
            400
        )


    if not CLIENT_ID:

        return (
            "ML_CLIENT_ID não configurado.",
            500
        )


    if not CLIENT_SECRET:

        return (
            "ML_CLIENT_SECRET não configurado.",
            500
        )


    if not REDIRECT_URI:

        return (
            "ML_REDIRECT_URI não configurado.",
            500
        )


    data = {

        "grant_type":
            "authorization_code",

        "client_id":
            CLIENT_ID,

        "client_secret":
            CLIENT_SECRET,

        "code":
            code,

        "redirect_uri":
            REDIRECT_URI,

        "code_verifier":
            verifier

    }


    try:

        response = requests.post(

            f"{API_BASE}/oauth/token",

            data=data,

            headers={
                "Accept":
                    "application/json"
            },

            timeout=30

        )

    except requests.RequestException as error:

        logger.exception(
            "Falha no callback OAuth."
        )

        return (

            "<h2>Erro de conexão</h2>"
            "<p>"
            + escapar(error)
            + "</p>"
            "<a href='/login'>Tentar novamente</a>",

            502

        )


    if response.status_code != 200:

        logger.error(

            "OAuth recusado: HTTP %s - %s",

            response.status_code,

            response.text[:2000]

        )

        return (

            "<!doctype html>"
            "<html lang='pt-BR'>"
            "<meta charset='utf-8'>"
            "<meta name='viewport' "
            "content='width=device-width,initial-scale=1'>"
            "<body style='font-family:Arial;padding:30px'>"

            "<h2>Login recusado pelo Mercado Livre</h2>"

            "<p>HTTP "
            + str(response.status_code)
            + "</p>"

            "<pre>"
            + escapar(response.text[:3000])
            + "</pre>"

            "<a href='/login'>Tentar novamente</a>"

            "</body>"
            "</html>",

            400

        )


    try:

        token_data = response.json()

    except ValueError:

        return (
            "Mercado Livre retornou "
            "uma resposta inválida.",
            502
        )


    access = token_data.get(
        "access_token"
    )


    if not access:

        return (
            "Mercado Livre não retornou "
            "access_token.",
            502
        )


    save_tokens(
        token_data
    )


    session.pop(
        "oauth_state",
        None
    )

    session.pop(
        "code_verifier",
        None
    )


    session.modified = True


    logger.info(
        "Login Mercado Livre concluído."
    )


    return redirect("/")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout", endpoint="logout_80")
def logout_80():

    global ACCESS_TOKEN
    global REFRESH_TOKEN
    global TOKEN_EXPIRES_AT


    ACCESS_TOKEN = None

    REFRESH_TOKEN = None

    TOKEN_EXPIRES_AT = 0


    session.clear()


    return redirect("/")


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health", endpoint="health_80")
def health_80():

    return jsonify(

        ok=True,

        app="Robo de Ofertas ML",

        versao=VERSION,

        status="online"

    )


# ============================================================
# STATUS
# ============================================================

@app.route("/api/status", endpoint="api_status_80")
def api_status_80():

    connected = bool(
        valid_token()
    )


    return jsonify(

        ok=True,

        app="Robo de Ofertas ML",

        versao=VERSION,

        mercado_livre=connected,

        client_id_configurado=bool(
            CLIENT_ID
        ),

        client_secret_configurado=bool(
            CLIENT_SECRET
        ),

        redirect_uri_configurado=bool(
            REDIRECT_URI
        ),

        categorias=list(
            NICHOS.keys()
        )

    )


# ============================================================
# DIAGNÓSTICO
# ============================================================

@app.route("/diagnostico", endpoint="diagnostico_80")
def diagnostico_80():

    connected = bool(
        valid_token()
    )


    return jsonify(

        ok=True,

        app="Robo de Ofertas ML",

        versao=VERSION,

        mercado_livre=connected,

        ml_client_id=bool(
            CLIENT_ID
        ),

        ml_client_secret=bool(
            CLIENT_SECRET
        ),

        ml_redirect_uri=bool(
            REDIRECT_URI
        ),

        categorias=list(
            NICHOS.keys()
        ),

        oauth_callback="/callback",

        api_busca="/api/buscar",

        api_me="/api/me",

        api_teste="/api/teste-busca"

    )


# ============================================================
# BUSCA PRINCIPAL
# ============================================================

@app.route("/api/buscar", endpoint="api_buscar_80")
def api_buscar_80():

    term = request.args.get(
        "q",
        ""
    ).strip()


    category = request.args.get(
        "categoria",
        "todos"
    ).strip().lower()


    limit = integer(

        request.args.get(
            "limite",
            30
        ),

        30

    )


    limit = max(
        1,
        min(limit, 50)
    )


    if not term:

        return jsonify(

            ok=False,

            quantidade=0,

            produtos=[],

            mensagem=(
                "Informe o produto "
                "para buscar."
            )

        ), 400


    allowed_all = (
        "todos",
        "todas",
        ""
    )


    if (
        category not in allowed_all
        and
        category not in NICHOS
    ):

        return jsonify(

            ok=False,

            quantidade=0,

            produtos=[],

            mensagem="Categoria inválida."

        ), 400


    selected_category = (

        None

        if category in allowed_all

        else category

    )


    products, error = search_term(

        term,

        selected_category,

        limit

    )


    if error:

        return api_error_response(
            error
        )


    return jsonify(

        ok=True,

        quantidade=len(
            products
        ),

        produtos=products

    )


# ============================================================
# OFERTAS POR CATEGORIA
# ============================================================

@app.route(
    "/ofertas/<category>",
    endpoint="ofertas_categoria_80"
)
def ofertas_categoria_80(category):

    category = str(
        category or ""
    ).strip().lower()


    if category not in NICHOS:

        return jsonify(

            ok=False,

            quantidade=0,

            produtos=[],

            mensagem=(
                "Categoria não encontrada."
            )

        ), 404


    limit = integer(

        request.args.get(
            "limite",
            30
        ),

        30

    )


    limit = max(
        1,
        min(limit, 100)
    )


    products, error = search_category(

        category,

        limit

    )


    if error:

        response, status_code = api_error_response(
            error
        )

        return response, status_code


    return jsonify(

        ok=True,

        categoria=category,

        nome_categoria=NICHOS[
            category
        ]["nome"],

        quantidade=len(
            products
        ),

        produtos=products

    )


# ============================================================
# MELHORES OFERTAS
# ============================================================

@app.route(
    "/melhores",
    endpoint="melhores_80"
)
def melhores_80():

    category = request.args.get(

        "categoria",

        "todos"

    ).strip().lower()


    limit = integer(

        request.args.get(
            "limite",
            30
        ),

        30

    )


    limit = max(
        1,
        min(limit, 100)
    )


    if category in (
        "todos",
        "todas",
        ""
    ):

        products, error = search_all(
            limit
        )


    elif category in NICHOS:

        products, error = search_category(

            category,

            limit

        )


    else:

        return jsonify(

            ok=False,

            quantidade=0,

            produtos=[],

            mensagem="Categoria inválida."

        ), 400


    if error:

        response, status_code = api_error_response(
            error
        )

        return response, status_code


    return jsonify(

        ok=True,

        categoria=category,

        quantidade=len(
            products
        ),

        produtos=products

    )


# ============================================================
# WHATSAPP
# ============================================================

@app.route(
    "/api/whatsapp",
    endpoint="api_whatsapp_80"
)
def api_whatsapp_80():

    title = request.args.get(
        "titulo",
        "Oferta"
    ).strip()


    price = num(
        request.args.get(
            "preco",
            0
        )
    )


    link = request.args.get(
        "link",
        ""
    ).strip()


    category = request.args.get(
        "categoria",
        "suplementos"
    ).strip().lower()


    if not link:

        return jsonify(

            ok=False,

            mensagem="Link não informado."

        ), 400


    if category not in NICHOS:

        category = "suplementos"


    text = whatsapp_text(

        title,

        price,

        link,

        category

    )


    return jsonify(

        ok=True,

        mensagem=text,

        whatsapp_url=(
            "https://wa.me/?text="
            + quote(text)
        )

    )


# ============================================================
# USUÁRIO MERCADO LIVRE
# ============================================================

@app.route(
    "/api/me",
    endpoint="api_me_80"
)
def api_me_80():

    current = valid_token()


    if not current:

        return jsonify(

            ok=False,

            mercado_livre=False,

            mensagem=(
                "Mercado Livre "
                "não conectado."
            )

        ), 401


    try:

        response = requests.get(

            f"{API_BASE}/users/me",

            headers=api_headers(True),

            timeout=30

        )

    except requests.RequestException as error:

        logger.exception(
            "Erro consultando usuário."
        )

        return jsonify(

            ok=False,

            mensagem=str(error)

        ), 502


    if response.status_code == 401:

        if refresh_token():

            try:

                response = requests.get(

                    f"{API_BASE}/users/me",

                    headers=api_headers(True),

                    timeout=30

                )

            except requests.RequestException as error:

                return jsonify(

                    ok=False,

                    mensagem=str(error)

                ), 502

        else:

            return jsonify(

                ok=False,

                mercado_livre=False,

                mensagem=(
                    "Token expirado. "
                    "Conecte novamente."
                )

            ), 401


    if response.status_code != 200:

        return jsonify(

            ok=False,

            mercado_livre=True,

            status=response.status_code,

            mensagem=(
                "Mercado Livre recusou "
                "a consulta do usuário."
            ),

            resposta=response.text[:2000]

        ), response.status_code


    try:

        data = response.json()

    except ValueError:

        return jsonify(

            ok=False,

            mensagem=(
                "Resposta inválida "
                "do Mercado Livre."
            )

        ), 502


    return jsonify(

        ok=True,

        mercado_livre=True,

        dados=data

    )


# ============================================================
# TESTE DE BUSCA
# ============================================================

@app.route(
    "/api/teste-busca",
    endpoint="api_teste_busca_80"
)
def api_teste_busca_80():

    term = request.args.get(

        "q",

        "whey protein"

    ).strip()


    products, error = search_term(

        term,

        "suplementos",

        10

    )


    if error:

        response, status_code = api_error_response(
            error,
            "Erro na busca de teste."
        )

        return response, status_code


    return jsonify(

        ok=True,

        teste=True,

        termo=term,

        quantidade=len(
            products
        ),

        produtos=products

    )


# ============================================================
# ROTA PARA VER CONFIGURAÇÃO SEM EXPOR SEGREDOS
# ============================================================

@app.route(
    "/api/config",
    endpoint="api_config_80"
)
def api_config_80():

    return jsonify(

        ok=True,

        versao=VERSION,

        site=SITE_ID,

        api_base=API_BASE,

        oauth_configurado=bool(
            CLIENT_ID
            and
            CLIENT_SECRET
            and
            REDIRECT_URI
        ),

        redirect_uri_configurado=bool(
            REDIRECT_URI
        ),

        categorias=list(
            NICHOS.keys()
        )

    )


# ============================================================
# ERRO 404
# ============================================================

@app.errorhandler(404)
def erro_404_80(error):

    if (
        request.path.startswith("/api/")
        or
        request.path.startswith("/ofertas/")
        or
        request.path.startswith("/melhores")
    ):

        return jsonify(

            ok=False,

            mensagem="Rota não encontrada.",

            rota=request.path

        ), 404


    return (

        "<!doctype html>"
        "<html lang='pt-BR'>"
        "<meta charset='utf-8'>"
        "<body style='font-family:Arial;padding:30px'>"
        "<h2>Rota não encontrada</h2>"
        "<a href='/'>Voltar para o robô</a>"
        "</body>"
        "</html>",

        404

    )


# ============================================================
# ERRO 500
# ============================================================

@app.errorhandler(500)
def erro_500_80(error):

    logger.exception(
        "Erro interno do servidor."
    )


    if (
        request.path.startswith("/api/")
        or
        request.path.startswith("/ofertas/")
        or
        request.path.startswith("/melhores")
    ):

        return jsonify(

            ok=False,

            mensagem=(
                "Erro interno "
                "do servidor."
            )

        ), 500


    return (

        "<!doctype html>"
        "<html lang='pt-BR'>"
        "<meta charset='utf-8'>"
        "<body style='font-family:Arial;padding:30px'>"
        "<h2>Erro interno</h2>"
        "<a href='/'>Voltar</a>"
        "</body>"
        "</html>",

        500

    )


# ============================================================
# INTERFACE WEB
#
# NÃO existe função home aqui.
# A rota "/" já está em painel_80().
# ============================================================

INDEX_HTML = r"""
<!doctype html>

<html lang="pt-BR">

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width,initial-scale=1"
>

<meta
    name="theme-color"
    content="#111827"
>

<title>
Robo de Ofertas ML 8.0
</title>

<style>

* {
    box-sizing: border-box;
}

body {

    margin: 0;

    background: #f3f4f6;

    color: #111827;

    font-family:
        Arial,
        Helvetica,
        sans-serif;
}

header {

    background: #111827;

    color: white;

    padding: 22px 16px;

    text-align: center;
}

header h1 {

    margin: 0 0 7px;

    font-size: 25px;
}

header p {

    margin: 0;

    opacity: .85;

    font-size: 14px;
}

main {

    width: 100%;

    max-width: 1050px;

    margin: auto;

    padding: 16px;
}

.card {

    background: white;

    border-radius: 16px;

    padding: 16px;

    margin-bottom: 16px;

    box-shadow:
        0 2px 12px
        rgba(0,0,0,.06);
}

.status {

    padding: 12px;

    border-radius: 10px;

    margin-bottom: 12px;

    font-weight: bold;
}

.connected {

    background: #dcfce7;

    color: #166534;
}

.disconnected {

    background: #fee2e2;

    color: #991b1b;
}

.btn {

    display: inline-block;

    border: 0;

    border-radius: 10px;

    padding: 12px 16px;

    text-decoration: none;

    font-weight: bold;

    cursor: pointer;

    font-size: 14px;
}

.login {

    background: #22c55e;

    color: white;
}

.logout {

    background: #ef4444;

    color: white;
}

.search {

    display: flex;

    gap: 8px;

    flex-wrap: wrap;
}

.search input,
.search select {

    flex: 1;

    min-width: 180px;

    padding: 13px;

    border:
        1px solid #d1d5db;

    border-radius: 10px;

    font-size: 15px;
}

.search button {

    border: 0;

    border-radius: 10px;

    background: #111827;

    color: white;

    padding: 13px 20px;

    font-weight: bold;

    cursor: pointer;
}

.categories {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(140px, 1fr)
        );

    gap: 9px;
}

.categories button {

    border: 0;

    background: #e5e7eb;

    border-radius: 10px;

    padding: 13px;

    font-weight: bold;

    cursor: pointer;
}

#loading {

    display: none;

    background: white;

    border-radius: 12px;

    padding: 15px;

    text-align: center;

    margin-bottom: 15px;

    font-weight: bold;
}

#status {

    margin-bottom: 15px;
}

.error {

    background: #fee2e2;

    color: #991b1b;

    padding: 14px;

    border-radius: 12px;
}

.success {

    background: #dcfce7;

    color: #166534;

    padding: 14px;

    border-radius: 12px;
}

.grid {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(250px, 1fr)
        );

    gap: 14px;
}

.product {

    background: white;

    border-radius: 14px;

    overflow: hidden;

    border:
        1px solid #e5e7eb;
}

.product img {

    display: block;

    width: 100%;

    height: 220px;

    object-fit: contain;

    background: #f8fafc;
}

.product-body {

    padding: 14px;
}

.product-title {

    font-weight: bold;

    line-height: 1.35;
}

.price {

    font-size: 21px;

    font-weight: bold;

    margin: 10px 0;
}

.small {

    font-size: 13px;

    color: #6b7280;

    margin-top: 5px;
}

.whatsapp {

    width: 100%;

    background: #25d366;

    color: white;

    text-align: center;

    margin-top: 12px;
}

.product-link {

    width: 100%;

    background: #e5e7eb;

    color: #111827;

    text-align: center;

    margin-top: 7px;
}

footer {

    text-align: center;

    padding: 25px;

    color: #6b7280;

    font-size: 12px;
}

</style>

</head>

<body>

<header>

<h1>
🔥 Robo de Ofertas ML 8.0
</h1>

<p>
Suplementos • Fitness Feminino • Fitness Masculino
</p>

</header>


<main>


<div class="card">

{% if connected %}

<div class="status connected">

🟢 Mercado Livre conectado

</div>

<a
    class="btn logout"
    href="/logout"
>

Desconectar

</a>

{% else %}

<div class="status disconnected">

🔴 Mercado Livre não conectado

</div>

<a
    class="btn login"
    href="/login"
>

🔗 Conectar Mercado Livre

</a>

{% endif %}

</div>


<div class="card">

<h2>
🔎 Buscar produtos
</h2>

<div class="search">

<input
    id="query"
    type="text"
    value="whey protein"
    placeholder="Digite o produto..."
>

<select id="category">

<option value="todos">
🔥 Todos
</option>

<option value="suplementos">
🥤 Suplementos
</option>

<option value="fitness_feminino">
👩 Fitness Feminino
</option>

<option value="fitness_masculino">
👨 Fitness Masculino
</option>

</select>

<button
    type="button"
    onclick="buscar()"
>

Buscar

</button>

</div>

</div>


<div class="card">

<h2>
📂 Categorias
</h2>

<div class="categories">

<button
    onclick="buscarCategoria('suplementos')"
>
🥤 Suplementos
</button>

<button
    onclick="buscarCategoria('fitness_feminino')"
>
👩 Feminino
</button>

<button
    onclick="buscarCategoria('fitness_masculino')"
>
👨 Masculino
</button>

<button
    onclick="buscarCategoria('todos')"
>
🔥 Todas
</button>

</div>

</div>


<div id="status"></div>


<div id="loading">

🔎 Procurando ofertas...

</div>


<div
    id="results"
    class="grid"
></div>


</main>


<footer>

Robo de Ofertas ML {{ version }}

</footer>


<script>

function esc(value) {

    return String(
        value ?? ""
    ).replace(
        /[&<>"']/g,
        function(char) {

            const map = {

                "&": "&amp;",

                "<": "&lt;",

                ">": "&gt;",

                '"': "&quot;",

                "'": "&#039;"

            };

            return map[char];

        }
    );

}


function setStatus(
    message,
    success
) {

    const status =
        document.getElementById(
            "status"
        );


    status.innerHTML =

        '<div class="'
        +
        (
            success
            ? "success"
            : "error"
        )
        +
        '">'
        +
        message
        +
        '</div>';

}


function buscarCategoria(
    category
) {

    const input =
        document.getElementById(
            "query"
        );

    const select =
        document.getElementById(
            "category"
        );


    select.value =
        category;


    if (
        category === "suplementos"
    ) {

        input.value =
            "whey protein";

    }

    else if (
        category === "fitness_feminino"
    ) {

        input.value =
            "legging feminina academia";

    }

    else if (
        category === "fitness_masculino"
    ) {

        input.value =
            "camiseta dry fit masculina";

    }

    else {

        input.value =
            "whey protein";

    }


    buscar();

}


async function buscar() {

    const input =
        document.getElementById(
            "query"
        );


    const select =
        document.getElementById(
            "category"
        );


    const loading =
        document.getElementById(
            "loading"
        );


    const results =
        document.getElementById(
            "results"
        );


    const query =
        input.value.trim();


    const category =
        select.value;


    if (!query) {

        setStatus(
            "❌ Digite um produto para buscar.",
            false
        );

        return;

    }


    loading.style.display =
        "block";


    results.innerHTML =
        "";


    setStatus(
        "",
        true
    );


    try {

        const url =
            "/api/buscar?q="
            +
            encodeURIComponent(query)
            +
            "&categoria="
            +
            encodeURIComponent(category)
            +
            "&limite=30";


        const response =
            await fetch(
                url,
                {
                    method: "GET",
                    headers: {
                        "Accept":
                            "application/json"
                    },
                    credentials: "same-origin"
                }
            );


        let data;


        try {

            data =
                await response.json();

        }

        catch {

            data = {
                ok: false,
                mensagem:
                    "Resposta inválida do servidor."
            };

        }


        if (
            response.status === 401
        ) {

            setStatus(

                "❌ Mercado Livre não conectado. "
                +
                "Clique em "
                +
                "'Conectar Mercado Livre'.",

                false

            );

            return;

        }


        if (
            response.status === 403
        ) {

            setStatus(

                "❌ Mercado Livre recusou a busca "
                +
                "(HTTP 403). "
                +
                "O token/login pode estar sem "
                +
                "permissão para este endpoint.",

                false

            );

            return;

        }


        if (
            !response.ok
            ||
            !data.ok
        ) {

            setStatus(

                "❌ "
                +
                esc(
                    data.mensagem
                    ||
                    "Erro ao realizar a busca."
                ),

                false

            );

            return;

        }


        const products =
            Array.isArray(
                data.produtos
            )
            ?
            data.produtos
            :
            [];


        if (
            products.length === 0
        ) {

            setStatus(

                "⚠️ Nenhuma oferta encontrada. "
                +
                "Tente outro termo.",

                false

            );

            return;

        }


        setStatus(

            "✅ "
            +
            products.length
            +
            " ofertas encontradas.",

            true

        );


        renderProducts(
            products
        );

    }

    catch (error) {

        console.error(
            error
        );


        setStatus(

            "❌ Não foi possível conectar "
            +
            "ao servidor do robô.",

            false

        );

    }

    finally {

        loading.style.display =
            "none";

    }

}


function renderProducts(
    products
) {

    const box =
        document.getElementById(
            "results"
        );


    box.innerHTML =
        products.map(
            function(product) {

                const image =
                    product.imagem
                    ?
                    (
                        '<img src="'
                        +
                        esc(
                            product.imagem
                        )
                        +
                        '" alt="Produto">'
                    )
                    :
                    "";


                const sold =
                    Number(
                        product.vendidos || 0
                    ) > 0
                    ?
                    (
                        '<div class="small">'
                        +
                        '🛒 '
                        +
                        esc(
                            product.vendidos
                        )
                        +
                        ' vendidos'
                        +
                        '</div>'
                    )
                    :
                    "";


                const shipping =
                    product.frete_gratis
                    ?
                    (
                        '<div class="small">'
                        +
                        '🚚 Frete grátis'
                        +
                        '</div>'
                    )
                    :
                    "";


                const whatsapp =
                    "/api/whatsapp"
                    +
                    "?titulo="
                    +
                    encodeURIComponent(
                        product.titulo || ""
                    )
                    +
                    "&preco="
                    +
                    encodeURIComponent(
                        product.preco || 0
                    )
                    +
                    "&link="
                    +
                    encodeURIComponent(
                        product.link || ""
                    )
                    +
                    "&categoria="
                    +
                    encodeURIComponent(
                        product.categoria || ""
                    );


                const productLink =
                    product.link || "#";


                return `

<article class="product">

${image}

<div class="product-body">

<div class="product-title">

${esc(product.titulo)}

</div>

<div class="price">

${esc(
    product.preco_formatado
    ||
    "R$ 0,00"
)}

</div>

${sold}

${shipping}

<a
    class="btn whatsapp"
    href="${esc(whatsapp)}"
    target="_blank"
    rel="noopener noreferrer"
>

📲 Compartilhar no WhatsApp

</a>

<a
    class="btn product-link"
    href="${esc(productLink)}"
    target="_blank"
    rel="noopener noreferrer"
>

🛒 Ver produto

</a>

</div>

</article>

`;

            }
        ).join("");

}


document
    .getElementById("query")
    .addEventListener(
        "keydown",
        function(event) {

            if (
                event.key === "Enter"
            ) {

                buscar();

            }

        }
    );


</script>


</body>

</html>
"""


# ============================================================
# VERIFICAÇÃO FINAL DO APLICATIVO
# ============================================================

def validate_configuration():

    problems = []


    if not CLIENT_ID:

        problems.append(
            "ML_CLIENT_ID"
        )


    if not CLIENT_SECRET:

        problems.append(
            "ML_CLIENT_SECRET"
        )


    if not REDIRECT_URI:

        problems.append(
            "ML_REDIRECT_URI"
        )


    if problems:

        logger.warning(

            "Variáveis não configuradas: %s",

            ", ".join(problems)

        )

    else:

        logger.info(
            "Configuração OAuth encontrada."
        )


# ============================================================
# STARTUP
# ============================================================

validate_configuration()


# ============================================================
# SERVIDOR LOCAL
# ============================================================

if __name__ == "__main__":

    port = integer(

        os.getenv(
            "PORT",
            "5000"
        ),

        5000

    )


    logger.info(
        "Robo de Ofertas ML %s iniciando na porta %s",
        VERSION,
        port
    )


    app.run(

        host="0.0.0.0",

        port=port,

        debug=False

    )
