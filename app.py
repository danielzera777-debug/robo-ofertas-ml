import os
import time
import secrets
import hashlib
import base64
import logging
from urllib.parse import urlencode, quote

import requests
from flask import Flask, request, session, redirect, jsonify, render_template_string


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

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("robo-ofertas")


# ============================================================
# CONFIGURAÇÕES MERCADO LIVRE
# ============================================================

CLIENT_ID = os.getenv("ML_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("ML_REDIRECT_URI", "")

API_BASE = "https://api.mercadolibre.com"

AUTH_URL = (
    "https://auth.mercadolivre.com.br/authorization"
)

SITE_ID = "MLB"

VERSION = "8.0"


# ============================================================
# TOKENS
# ============================================================

ACCESS_TOKEN = None
REFRESH_TOKEN = None
TOKEN_EXPIRES_AT = 0


# ============================================================
# NICHOS DO ROBÔ
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
            "magnésio"

        ]

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
            "body fitness feminino"

        ]

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
            "bermuda academia masculina"

        ]

    }

}


# ============================================================
# FUNÇÕES BÁSICAS
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

    return (
        f"R$ {num(valor):,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


# ============================================================
# TOKEN
# ============================================================

def token():

    global ACCESS_TOKEN

    if ACCESS_TOKEN:
        return ACCESS_TOKEN

    ACCESS_TOKEN = session.get(
        "access_token"
    )

    return ACCESS_TOKEN


# ============================================================
# SALVAR TOKENS
# ============================================================

def save_tokens(data):

    global ACCESS_TOKEN
    global REFRESH_TOKEN
    global TOKEN_EXPIRES_AT

    ACCESS_TOKEN = data.get(
        "access_token"
    )

    REFRESH_TOKEN = (
        data.get("refresh_token")
        or session.get("refresh_token")
    )

    expires = integer(
        data.get("expires_in", 21600),
        21600
    )

    TOKEN_EXPIRES_AT = (
        time.time()
        + max(60, expires - 120)
    )

    if ACCESS_TOKEN:

        session["access_token"] = (
            ACCESS_TOKEN
        )

    if REFRESH_TOKEN:

        session["refresh_token"] = (
            REFRESH_TOKEN
        )

    session["token_expires_at"] = (
        TOKEN_EXPIRES_AT
    )

    session.modified = True


# ============================================================
# RENOVAR TOKEN
# ============================================================

def refresh_token():

    refresh = (
        REFRESH_TOKEN
        or session.get("refresh_token")
    )

    if not refresh:
        return False

    if not CLIENT_ID:
        return False

    if not CLIENT_SECRET:
        return False

    try:

        response = requests.post(

            f"{API_BASE}/oauth/token",

            data={

                "grant_type":
                    "refresh_token",

                "client_id":
                    CLIENT_ID,

                "client_secret":
                    CLIENT_SECRET,

                "refresh_token":
                    refresh

            },

            timeout=25

        )

    except requests.RequestException as error:

        logger.error(
            "Erro ao renovar token: %s",
            error
        )

        return False


    if response.status_code != 200:

        logger.warning(

            "Refresh recusado: HTTP %s - %s",

            response.status_code,

            response.text[:500]

        )

        return False


    try:

        save_tokens(
            response.json()
        )

        return True

    except Exception as error:

        logger.error(
            "Erro salvando token renovado: %s",
            error
        )

        return False


# ============================================================
# TOKEN VÁLIDO
# ============================================================

def valid_token():

    current = token()

    if not current:
        return None


    if (
        TOKEN_EXPIRES_AT
        and time.time() >= TOKEN_EXPIRES_AT
    ):

        if not refresh_token():

            return None


    return token()


# ============================================================
# HEADERS
# ============================================================

def api_headers(auth=True):

    headers = {

        "Accept":
            "application/json",

        "Content-Type":
            "application/json",

        "User-Agent":
            "Robo-Ofertas-ML/8.0"

    }


    if auth:

        current = valid_token()

        if current:

            headers["Authorization"] = (
                f"Bearer {current}"
            )


    return headers


# ============================================================
# LOGIN OAUTH
# ============================================================

def oauth_login():

    if not CLIENT_ID:

        return (
            None,
            "Configure ML_CLIENT_ID no Render."
        )


    if not REDIRECT_URI:

        return (
            None,
            "Configure ML_REDIRECT_URI no Render."
        )


    state = secrets.token_urlsafe(32)

    verifier = secrets.token_urlsafe(64)

    digest = hashlib.sha256(
        verifier.encode()
    ).digest()

    challenge = (
        base64.urlsafe_b64encode(
            digest
        )
        .decode()
        .rstrip("=")
    )


    session["oauth_state"] = state

    session["code_verifier"] = verifier


    params = {

        "response_type":
            "code",

        "client_id":
            CLIENT_ID,

        "redirect_uri":
            REDIRECT_URI,

        "state":
            state,

        "code_challenge":
            challenge,

        "code_challenge_method":
            "S256"

    }


    return (
        AUTH_URL
        + "?"
        + urlencode(params)
    ), None


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classify(title, fallback=None):

    text = (
        title or ""
    ).lower()


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
        "omega 3"

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
        "bermuda fitness feminina"

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
        "camiseta academia masculina"

    ]


    if any(
        word in text
        for word in supplement_words
    ):

        return "suplementos"


    if any(
        word in text
        for word in female_words
    ):

        return "fitness_feminino"


    if any(
        word in text
        for word in male_words
    ):

        return "fitness_masculino"


    return fallback


# ============================================================
# WHATSAPP
# ============================================================

def whatsapp_text(
    title,
    price,
    link,
    category
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

        f"💰 Por apenas: "
        f"{money(price)}\n\n"

        f"🛒 COMPRAR AGORA 👇\n"
        f"{link}\n\n"

        "⚠️ Preço e disponibilidade "
        "podem mudar no Mercado Livre."

    )


# ============================================================
# TRANSFORMAR PRODUTO
# ============================================================

def transform(item, fallback=None):

    if not isinstance(item, dict):

        return None


    title = str(
        item.get("title")
        or ""
    ).strip()


    price = num(
        item.get("price")
    )


    link = (
        item.get("permalink")
        or ""
    )


    if not title:

        return None


    if price <= 0:

        return None


    category = classify(
        title,
        fallback
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

        "id":
            item.get("id"),

        "titulo":
            title,

        "preco":
            price,

        "preco_formatado":
            money(price),

        "imagem":
            item.get("thumbnail")
            or "",

        "link":
            link,

        "categoria":
            category,

        "vendidos":
            integer(
                item.get(
                    "sold_quantity"
                ),
                0
            ),

        "condicao":
            item.get(
                "condition"
            )
            or "",

        "frete_gratis":
            bool(
                shipping.get(
                    "free_shipping"
                )
            ),

        "vendedor_id":
            seller.get("id"),

        "whatsapp":
            whatsapp_text(
                title,
                price,
                link,
                category
            )

    }


# ============================================================
# BUSCA MERCADO LIVRE - CORRIGIDA
# ============================================================

def search_ml(term, limit=20):

    term = str(
        term or ""
    ).strip()


    if not term:

        return [], {

            "status": 400,

            "mensagem":
                "Termo de busca vazio.",

            "resposta":
                ""

        }


    limit = max(
        1,
        min(
            integer(limit, 20),
            50
        )
    )


    url = (
        f"{API_BASE}/sites/"
        f"{SITE_ID}/search"
    )


    params = {

        "q":
            term,

        "limit":
            limit,

        "offset":
            0

    }


    # ========================================================
    # PRIMEIRA TENTATIVA AUTENTICADA
    # ========================================================

    try:

        response = requests.get(

            url,

            params=params,

            headers=api_headers(True),

            timeout=25

        )

    except requests.RequestException as error:

        logger.warning(

            "Busca '%s' falhou: %s",

            term,

            error

        )

        return [], {

            "status": 502,

            "mensagem":
                "Não foi possível conectar "
                "ao Mercado Livre.",

            "resposta":
                str(error)

        }


    # ========================================================
    # SUCESSO
    # ========================================================

    if response.status_code == 200:

        try:

            data = response.json()

        except ValueError:

            return [], {

                "status": 502,

                "mensagem":
                    "Mercado Livre retornou "
                    "uma resposta inválida.",

                "resposta":
                    response.text[:1000]

            }


        results = data.get(
            "results",
            []
        )


        if not isinstance(
            results,
            list
        ):

            results = []


        return results, None


    # ========================================================
    # TOKEN EXPIRADO
    # ========================================================

    if response.status_code == 401:

        logger.warning(

            "Token recusado na busca '%s'. "
            "Tentando renovar.",

            term

        )


        if refresh_token():

            try:

                retry = requests.get(

                    url,

                    params=params,

                    headers=api_headers(True),

                    timeout=25

                )

            except requests.RequestException as error:

                return [], {

                    "status": 502,

                    "mensagem":
                        "Falha de conexão "
                        "após renovar o token.",

                    "resposta":
                        str(error)

                }


            if retry.status_code == 200:

                try:

                    data = retry.json()

                except ValueError:

                    return [], {

                        "status": 502,

                        "mensagem":
                            "Resposta inválida "
                            "após renovar o token.",

                        "resposta":
                            retry.text[:1000]

                    }


                results = data.get(
                    "results",
                    []
                )


                if not isinstance(
                    results,
                    list
                ):

                    results = []


                return results, None


            response = retry


        return [], {

            "status": 401,

            "mensagem":
                "O token do Mercado Livre "
                "foi recusado. "
                "Conecte novamente.",

            "resposta":
                response.text[:1000]

        }


    # ========================================================
    # 403 - NÃO TRANSFORMAR EM []
    # ========================================================

    if response.status_code == 403:

        logger.warning(

            "Mercado Livre recusou "
            "a busca '%s': HTTP 403: %s",

            term,

            response.text[:1000]

        )


        return [], {

            "status": 403,

            "mensagem":
                "O Mercado Livre recusou "
                "a consulta de busca (HTTP 403). "
                "O login está válido, mas a "
                "aplicação/token não tem "
                "autorização para este endpoint.",

            "resposta":
                response.text[:1000]

        }


    # ========================================================
    # OUTROS ERROS
    # ========================================================

    logger.warning(

        "Busca '%s' falhou: HTTP %s: %s",

        term,

        response.status_code,

        response.text[:1000]

    )


    return [], {

        "status":
            response.status_code,

        "mensagem":
            (
                "Mercado Livre retornou "
                f"HTTP {response.status_code}."
            ),

        "resposta":
            response.text[:1000]

    }


# ============================================================
# BUSCA DE UM TERMO
# ============================================================

def search_term(
    term,
    category=None,
    limit=20
):

    results, error = search_ml(
        term,
        limit
    )


    if error:

        return [], error


    products = []

    seen = set()


    for item in results:

        product = transform(
            item,
            category
        )


        if not product:

            continue


        product_id = product.get(
            "id"
        )


        if product_id in seen:

            continue


        seen.add(product_id)

        products.append(
            product
        )


    return products, None


# ============================================================
# BUSCA POR CATEGORIA
# ============================================================

def search_category(
    category,
    limit=30
):

    if category not in NICHOS:

        return [], {

            "status": 400,

            "mensagem":
                "Categoria não encontrada.",

            "resposta":
                ""

        }


    limit = max(

        1,

        min(
            integer(limit, 30),
            100
        )

    )


    products = []

    seen = set()


    per_term = min(

        20,

        max(
            5,
            limit
        )

    )


    first_error = None


    for term in NICHOS[
        category
    ]["termos"]:


        results, error = search_term(

            term,

            category,

            per_term

        )


        if error:

            if first_error is None:

                first_error = error


            # 401/403 não devem ser
            # escondidos como ausência
            # de produtos.

            if error.get(
                "status"
            ) in (401, 403):

                return [], error


            continue


        for product in results:

            product_id = product.get(
                "id"
            )


            if product_id in seen:

                continue


            seen.add(
                product_id
            )


            products.append(
                product
            )


            if len(products) >= limit:

                return (
                    sort_products(
                        products
                    ),
                    None
                )


    if products:

        return (
            sort_products(
                products
            ),
            None
        )


    return [], first_error


# ============================================================
# BUSCA TODAS AS CATEGORIAS
# ============================================================

def search_all(limit=30):

    limit = max(

        1,

        min(
            integer(limit, 30),
            100
        )

    )


    products = []

    seen = set()


    each = max(

        5,

        limit // 3

    )


    first_error = None


    for category in NICHOS:

        results, error = search_category(

            category,

            each

        )


        if error:

            if first_error is None:

                first_error = error


            if error.get(
                "status"
            ) in (401, 403):

                return [], error


        for product in results:

            product_id = product.get(
                "id"
            )


            if product_id in seen:

                continue


            seen.add(
                product_id
            )


            products.append(
                product
            )


            if len(products) >= limit:

                return (
                    sort_products(
                        products
                    ),
                    None
                )


    if products:

        return (
            sort_products(
                products
            ),
            None
        )


    return [], first_error


# ============================================================
# ORDENAÇÃO
# ============================================================

def sort_products(products):

    return sorted(

        products,

        key=lambda item: (

            integer(
                item.get(
                    "vendidos"
                ),
                0
            ),

            -num(
                item.get(
                    "preco"
                )
            )

        ),

        reverse=True

    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

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
# LOGIN
# ============================================================

@app.route("/login")
def login():

    url, error = oauth_login()


    if error:

        return error, 500


    return redirect(url)


# ============================================================
# CALLBACK
# ============================================================

@app.route("/callback")
def callback():

    if request.args.get(
        "error"
    ):

        return (

            "<h2>Erro no Mercado Livre</h2>"

            "<p>"

            + request.args.get(
                "error_description",
                request.args.get(
                    "error"
                )
            )

            + "</p>",

            400

        )


    code = request.args.get(
        "code"
    )

    state = request.args.get(
        "state"
    )


    if not code:

        return (
            "Código OAuth não recebido.",
            400
        )


    if state != session.get(
        "oauth_state"
    ):

        return (

            "Sessão OAuth inválida "
            "ou expirada. "
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


    try:

        response = requests.post(

            f"{API_BASE}/oauth/token",

            data={

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

            },

            timeout=25

        )

    except requests.RequestException as error:

        return (

            f"Erro de conexão "
            f"com Mercado Livre: {error}",

            502

        )


    if response.status_code != 200:

        return (

            "<h2>Mercado Livre "
            "recusou o login</h2>"

            "<pre>"

            + response.text[:2000]

            + "</pre>",

            400

        )


    try:

        save_tokens(
            response.json()
        )

    except Exception as error:

        return (
            f"Erro salvando token: {error}",
            500
        )


    session.pop(
        "oauth_state",
        None
    )

    session.pop(
        "code_verifier",
        None
    )


    return redirect("/")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    global ACCESS_TOKEN
    global REFRESH_TOKEN
    global TOKEN_EXPIRES_AT


    ACCESS_TOKEN = None

    REFRESH_TOKEN = None

    TOKEN_EXPIRES_AT = 0


    session.clear()


    return redirect("/")


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify(

        ok=True,

        app="Robo de Ofertas",

        versao=VERSION

    )


# ============================================================
# DIAGNÓSTICO
# ============================================================

@app.route("/diagnostico")
def diagnostico():

    return jsonify(

        ok=True,

        app="Robo de Ofertas",

        versao=VERSION,

        mercado_livre=bool(
            valid_token()
        ),

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
        )

    )


# ============================================================
# STATUS
# ============================================================

@app.route("/api/status")
def status():

    return jsonify(

        ok=True,

        app="Robo de Ofertas",

        versao=VERSION,

        mercado_livre=bool(
            valid_token()
        ),

        categorias=list(
            NICHOS.keys()
        )

    )


# ============================================================
# BUSCAR
# ============================================================

@app.route("/api/buscar")
def api_buscar():

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


    if not term:

        return jsonify(

            ok=False,

            mensagem:
                "Informe o produto "
                "para buscar.",

            produtos=[]

        ), 400


    if (

        category not in (
            "todos",
            "todas",
            ""
        )

        and

        category not in NICHOS

    ):

        return jsonify(

            ok=False,

            mensagem:
                "Categoria inválida.",

            produtos=[]

        ), 400


    products, error = search_term(

        term,

        None

        if category in (
            "todos",
            "todas",
            ""
        )

        else category,

        limit

    )


    # ========================================================
    # IMPORTANTE:
    # ERRO NÃO É "NENHUM PRODUTO"
    # ========================================================

    if error:

        status_code = integer(

            error.get(
                "status"
            ),

            502

        )


        if (
            status_code < 400
            or status_code > 599
        ):

            status_code = 502


        return jsonify(

            ok=False,

            quantidade=0,

            produtos=[],

            mensagem=error.get(

                "mensagem",

                "Erro ao consultar "
                "o Mercado Livre."

            ),

            status_mercado_livre=
                status_code,

            detalhes=error.get(

                "resposta",

                ""

            )

        ), status_code


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

@app.route("/ofertas/<category>")
def offers(category):

    category = category.lower().strip()

    if category not in NICHOS:

        return jsonify(
            ok=False,
            mensagem="Categoria não encontrada.",
            produtos=[]
        ), 404

    limit = integer(
        request.args.get("limite", 30),
        30
    )

    products, error = search_category(
        category,
        limit
    )

    if error:

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
            categoria=category,
            mensagem=error.get(
                "mensagem",
                "Erro ao consultar o Mercado Livre."
            ),
            status_mercado_livre=status_code,
            detalhes=error.get("resposta", "")
        ), status_code

    return jsonify(
        ok=True,
        categoria=category,
        nome_categoria=NICHOS[category]["nome"],
        quantidade=len(products),
        produtos=products
    )


# ============================================================
# MELHORES OFERTAS
# ============================================================

@app.route("/melhores")
def melhores():

    category = request.args.get(
        "categoria",
        "todos"
    ).lower().strip()

    limit = integer(
        request.args.get("limite", 30),
        30
    )

    if category in ("todos", "todas", ""):

        products, error = search_all(limit)

    elif category in NICHOS:

        products, error = search_category(
            category,
            limit
        )

    else:

        return jsonify(
            ok=False,
            mensagem="Categoria inválida.",
            produtos=[]
        ), 400

    if error:

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
            categoria=category,
            mensagem=error.get(
                "mensagem",
                "Erro ao consultar o Mercado Livre."
            ),
            status_mercado_livre=status_code,
            detalhes=error.get("resposta", "")
        ), status_code

    return jsonify(
        ok=True,
        categoria=category,
        quantidade=len(products),
        produtos=products
    )


# ============================================================
# WHATSAPP
# ============================================================

@app.route("/api/whatsapp")
def whatsapp_api():

    title = request.args.get(
        "titulo",
        "Oferta Fitness"
    )

    price = num(
        request.args.get("preco")
    )

    link = request.args.get(
        "link",
        ""
    )

    category = request.args.get(
        "categoria",
        "suplementos"
    )

    if not link:

        return jsonify(
            ok=False,
            mensagem="Link não informado."
        ), 400

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
# DADOS DO USUÁRIO MERCADO LIVRE
# ============================================================

@app.route("/api/me")
def me():

    current = valid_token()

    if not current:

        return jsonify(
            ok=False,
            mercado_livre=False,
            mensagem="Mercado Livre não conectado."
        ), 401

    try:

        response = requests.get(

            f"{API_BASE}/users/me",

            headers=api_headers(True),

            timeout=25

        )

    except requests.RequestException as error:

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

                    timeout=25

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
                    "Conecte o Mercado Livre novamente."
                )
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

            resposta=response.text[:2000]

        ), response.status_code

    try:

        data = response.json()

    except ValueError:

        data = {}

    return jsonify(
        ok=True,
        mercado_livre=True,
        dados=data
    )


# ============================================================
# ROTA PARA TESTAR BUSCA
# ============================================================

@app.route("/api/teste-busca")
def teste_busca():

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

        status_code = integer(
            error.get("status"),
            502
        )

        if status_code < 400 or status_code > 599:
            status_code = 502

        return jsonify(

            ok=False,

            teste=True,

            termo=term,

            produtos=[],

            mensagem=error.get(
                "mensagem",
                "Erro na busca."
            ),

            status_mercado_livre=status_code,

            detalhes=error.get(
                "resposta",
                ""
            )

        ), status_code

    return jsonify(

        ok=True,

        teste=True,

        termo=term,

        quantidade=len(products),

        produtos=products

    )


# ============================================================
# ERRO 404
# ============================================================

@app.errorhandler(404)
def not_found(error):

    if (
        request.path.startswith("/api/")
        or request.path.startswith("/ofertas/")
    ):

        return jsonify(
            ok=False,
            mensagem="Rota não encontrada.",
            rota=request.path
        ), 404

    return (
        "<h2>Rota não encontrada</h2>"
        "<a href='/'>Voltar</a>"
    ), 404


# ============================================================
# ERRO 500
# ============================================================

@app.errorhandler(500)
def server_error(error):

    logger.exception(
        "Erro interno"
    )

    if (
        request.path.startswith("/api/")
        or request.path.startswith("/ofertas/")
    ):

        return jsonify(

            ok=False,

            mensagem=(
                "Erro interno do servidor."
            ),

            erro=str(error)

        ), 500

    return (
        "<h2>Erro interno</h2>"
        "<a href='/'>Voltar</a>"
    ), 500


# ============================================================
# INTERFACE
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
Robo de Ofertas Fitness
</title>

<style>

* {
    box-sizing: border-box;
}

body {

    margin: 0;

    background: #f4f6f8;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    color: #111827;
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

header div {

    font-size: 14px;

    opacity: .9;
}

main {

    max-width: 1000px;

    margin: auto;

    padding: 16px;
}

.card {

    background: white;

    border-radius: 16px;

    padding: 16px;

    margin-bottom: 16px;

    box-shadow:
        0 2px 10px
        rgba(0,0,0,.06);
}

h2 {

    font-size: 19px;

    margin-top: 0;
}

.connect {

    background: #22c55e;

    color: white;
}

.logout {

    background: #ef4444;

    color: white;
}

.btn {

    border: 0;

    border-radius: 10px;

    padding: 12px 15px;

    font-weight: bold;

    text-decoration: none;

    display: inline-block;

    cursor: pointer;
}

.search {

    display: flex;

    gap: 8px;

    flex-wrap: wrap;
}

input,
select {

    padding: 12px;

    border:
        1px solid #ddd;

    border-radius: 10px;

    flex: 1;

    min-width: 180px;

    font-size: 15px;
}

.search button {

    background: #111827;

    color: white;

    border: 0;

    border-radius: 10px;

    padding: 12px 18px;

    font-weight: bold;
}

.categories {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(140px, 1fr)
        );

    gap: 8px;
}

.categories button {

    background: #e5e7eb;

    border: 0;

    border-radius: 10px;

    padding: 13px 10px;

    font-weight: bold;

    cursor: pointer;
}

#status {

    margin-top: 12px;

    font-weight: bold;
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

    border:
        1px solid #e5e7eb;

    border-radius: 14px;

    overflow: hidden;

    background: white;
}

.product img {

    width: 100%;

    height: 210px;

    object-fit: contain;

    background: #f8fafc;
}

.product .body {

    padding: 13px;
}

.price {

    font-size: 20px;

    font-weight: bold;

    margin: 8px 0;
}

.whats {

    background: #25d366;

    color: white;

    width: 100%;

    margin-top: 8px;

    text-align: center;
}

.product-link {

    background: #e5e7eb;

    color: #111827;

    width: 100%;

    margin-top: 7px;

    text-align: center;
}

.small {

    font-size: 13px;

    color: #6b7280;

    margin-top: 4px;
}

#loading {

    display: none;

    padding: 15px;

    text-align: center;

    font-weight: bold;
}

.error {

    background: #fee2e2;

    color: #991b1b;

    border-radius: 12px;

    padding: 14px;

    margin-top: 12px;
}

.success {

    color: #166534;
}

</style>

</head>

<body>


<header>

<h1>
🔥 Robo de Ofertas Fitness
</h1>

<div>
Suplementos • Fitness Feminino • Fitness Masculino
</div>

</header>


<main>


<div class="card">

{% if connected %}

<div>

🟢

<b>
Mercado Livre conectado
</b>

</div>

<a
    class="btn logout"
    href="/logout"
    style="margin-top:10px"
>

Desconectar

</a>

{% else %}

<div>

🔴

<b>
Mercado Livre não conectado
</b>

</div>

<a
    class="btn connect"
    href="/login"
    style="margin-top:10px"
>

🔗 Conectar Mercado Livre

</a>

{% endif %}

<div id="status"></div>

</div>


<div class="card">

<h2>
🔎 Procurar produto
</h2>

<div class="search">

<input
    id="query"
    placeholder="Ex.: Whey, Creatina, Legging..."
    value="Whey"
/>

<select id="category">

<option value="todos">
Todos
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

<button onclick="buscar()">
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
    onclick="categoria('suplementos')"
>
🥤 Suplementos
</button>

<button
    onclick="categoria('fitness_feminino')"
>
👩 Feminino
</button>

<button
    onclick="categoria('fitness_masculino')"
>
👨 Masculino
</button>

<button
    onclick="categoria('todos')"
>
🔥 Todas
</button>

</div>

</div>


<div id="loading">
🔎 Procurando ofertas...
</div>


<div
    id="results"
    class="grid"
></div>


</main>


<script>


function esc(value) {

    return String(
        value ?? ""
    ).replace(

        /[&<>"']/g,

        function(match) {

            return {

                "&": "&amp;",

                "<": "&lt;",

                ">": "&gt;",

                '"': "&quot;",

                "'": "&#039;"

            }[match];

        }

    );

}


function categoria(category) {

    document
        .getElementById("category")
        .value = category;


    if (
        category === "todos"
    ) {

        document
            .getElementById("query")
            .value = "whey";

        buscar();

        return;
    }


    let query;


    if (
        category === "suplementos"
    ) {

        query =
            "whey protein";

    }


    else if (
        category === "fitness_feminino"
    ) {

        query =
            "legging feminina academia";

    }


    else {

        query =
            "camiseta dry fit masculina";

    }


    document
        .getElementById("query")
        .value = query;


    buscar();

}


async function buscar() {

    const query =
        document
            .getElementById("query")
            .value
            .trim();


    const category =
        document
            .getElementById("category")
            .value;


    const status =
        document
            .getElementById("status");


    const loading =
        document
            .getElementById("loading");


    const results =
        document
            .getElementById("results");


    if (!query) {

        status.innerHTML =
            '<div class="error">'
            + 'Digite um produto.'
            + '</div>';

        return;

    }


    loading.style.display =
        "block";


    results.innerHTML =
        "";


    status.innerHTML =
        "";


    try {


        const response =
            await fetch(

                "/api/buscar?q="
                + encodeURIComponent(query)

                + "&categoria="
                + encodeURIComponent(category)

                + "&limite=30"

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


        /*
         * IMPORTANTE:
         * Agora 403 aparece como erro real.
         */

        if (
            response.status === 401
            ||
            response.status === 403
        ) {

            status.innerHTML =

                '<div class="error">'
                + '❌ '
                + esc(
                    data.mensagem
                    ||
                    "Mercado Livre recusou a consulta."
                )
                + '<br><br>'
                + 'Verifique a conexão OAuth '
                + 'e as permissões da aplicação.'
                + '</div>';

            return;

        }


        if (
            !response.ok
            ||
            !data.ok
        ) {

            status.innerHTML =

                '<div class="error">'
                + '❌ '
                + esc(
                    data.mensagem
                    ||
                    "Erro na busca."
                )
                + '</div>';

            return;

        }


        if (
            !data.produtos
            ||
            !data.produtos.length
        ) {

            status.innerHTML =

                '<div class="error">'
                + '❌ Nenhuma oferta encontrada.'
                + '<br>'
                + 'Tente outro termo.'
                + '</div>';

            return;

        }


        status.innerHTML =

            '<div class="success">'
            + '✅ '
            + data.quantidade
            + ' ofertas encontradas.'
            + '</div>';


        render(
            data.produtos
        );


    }

    catch (error) {

        status.innerHTML =

            '<div class="error">'
            + '❌ Erro de conexão '
            + 'com o robô.'
            + '</div>';

    }

    finally {

        loading.style.display =
            "none";

    }

}


function render(products) {

    const box =
        document
            .getElementById("results");


    box.innerHTML =

        products.map(

            function(product) {

                const image =
                    product.imagem
                    ?
                    '<img src="'
                    + esc(product.imagem)
                    + '" alt="">'
                    :
                    "";


                const sold =
                    product.vendidos
                    ?
                    '<div class="small">'
                    + '🛒 '
                    + esc(product.vendidos)
                    + ' vendidos'
                    + '</div>'
                    :
                    "";


                const shipping =
                    product.frete_gratis
                    ?
                    '<div class="small">'
                    + '🚚 Frete grátis'
                    + '</div>'
                    :
                    "";


                const whatsappUrl =

                    "/api/whatsapp"
                    + "?titulo="
                    + encodeURIComponent(
                        product.titulo
                    )
                    + "&preco="
                    + encodeURIComponent(
                        product.preco
                    )
                    + "&link="
                    + encodeURIComponent(
                        product.link
                    )
                    + "&categoria="
                    + encodeURIComponent(
                        product.categoria
                    );


                return `

<article class="product">

${image}

<div class="body">

<b>
${esc(product.titulo)}
</b>

<div class="price">
${esc(product.preco_formatado)}
</div>

${sold}

${shipping}

<a
    class="btn whats"
    target="_blank"
    href="${whatsappUrl}"
>

📲 Compartilhar no WhatsApp

</a>

<a
    class="btn product-link"
    target="_blank"
    href="${esc(product.link)}"
>

🛒 Ver produto

</a>

</div>

</article>

`;

            }

        ).join("");

}


</script>


</body>

</html>
"""


# ============================================================
# INICIAR SERVIDOR
# ============================================================

if __name__ == "__main__":

    port = integer(
        os.getenv(
            "PORT",
            5000
        ),
        5000
    )

    app.run(

        host="0.0.0.0",

        port=port,

        debug=False

    )
