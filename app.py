import os
import secrets
import hashlib
import base64
import requests
import html

from urllib.parse import urlencode, quote
from flask import Flask, request, session

app = Flask(__name__)

# ============================================================
# CONFIGURAÇÕES
# ============================================================

CLIENT_ID = os.getenv("ML_CLIENT_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ML_REDIRECT_URI")

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    secrets.token_hex(32)
)

app.secret_key = SECRET_KEY

app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

API_BASE = "https://api.mercadolibre.com"

SITE_ID = "MLB"

# ============================================================
# CATEGORIAS
# ============================================================

CATEGORIAS = {

    "celulares": {
        "nome": "📱 Celulares",
        "domain_id": "MLB-CELLPHONES",
        "category_id": "MLB1055"
    },

    "roupas": {
        "nome": "👕 Roupas",
        "domain_id": None,
        "category_id": "MLB1430"
    },

    "relogios": {
        "nome": "⌚ Relógios",
        "domain_id": None,
        "category_id": "MLB3937"
    },

    "calcados": {
        "nome": "👟 Calçados",
        "domain_id": None,
        "category_id": "MLB1430"
    },

    "beleza": {
        "nome": "💄 Beleza",
        "domain_id": None,
        "category_id": "MLB1246"
    },

    "casa": {
        "nome": "🏠 Casa",
        "domain_id": None,
        "category_id": "MLB1574"
    },

    "games": {
        "nome": "🎮 Games",
        "domain_id": None,
        "category_id": "MLB1144"
    },

    "informatica": {
        "nome": "💻 Informática",
        "domain_id": None,
        "category_id": "MLB1648"
    },

    "eletronicos": {
        "nome": "🔊 Eletrônicos",
        "domain_id": None,
        "category_id": "MLB1000"
    },

    "todas": {
        "nome": "🛒 Todas as categorias",
        "domain_id": None,
        "category_id": None
    }
}


# ============================================================
# PADRÕES DA REVENDA
# ============================================================

MARGEM_PADRAO = 10

LUCRO_MINIMO_PADRAO = 20


# ============================================================
# FUNÇÕES
# ============================================================

def escapar(valor):

    return html.escape(
        str(valor or "")
    )


def numero(valor):

    try:

        return float(valor)

    except Exception:

        return 0.0


def formatar_preco(valor):

    if valor is None:

        return "Preço indisponível"

    try:

        valor = float(valor)

        return (
            f"R$ {valor:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    except Exception:

        return "Preço indisponível"


# ============================================================
# HEADERS
# ============================================================

def headers_api():

    headers = {

        "Accept":
        "application/json",

        "User-Agent":
        "Robo-Ofertas-ML/2.0"

    }

    token = session.get(
        "access_token"
    )

    if token:

        headers["Authorization"] = (
            f"Bearer {token}"
        )

    return headers


# ============================================================
# GET MERCADO LIVRE
# ============================================================

def requisicao_get(
    url,
    params=None
):

    try:

        return requests.get(

            url,

            params=params,

            headers=headers_api(),

            timeout=30

        )

    except requests.RequestException as erro:

        print(
            "ERRO REQUEST:",
            erro
        )

        return None


# ============================================================
# LOGIN
# ============================================================

@app.route("/")
def home():

    code = request.args.get(
        "code"
    )

    state = request.args.get(
        "state"
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

    # ========================================================
    # CALLBACK
    # ========================================================

    if code:

        saved_state = session.get(
            "state"
        )

        if not saved_state:

            return """
            <h2>❌ Sessão expirada.</h2>
            <a href="/">Voltar</a>
            """, 400

        if state != saved_state:

            return """
            <h2>❌ State inválido.</h2>
            <a href="/">Voltar</a>
            """, 400

        code_verifier = session.get(
            "code_verifier"
        )

        if not code_verifier:

            return """
            <h2>
            ❌ Code verifier não encontrado.
            </h2>
            """, 400

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
                    code_verifier
                },

                timeout=30
            )

        except requests.RequestException as erro:

            return f"""

            <h1>❌ Erro de conexão</h1>

            <pre>
            {escapar(erro)}
            </pre>

            <a href="/">Voltar</a>

            """, 500

        if response.status_code != 200:

            return f"""

            <h1>
            ❌ Erro ao obter token
            </h1>

            <p>
            Status:
            {response.status_code}
            </p>

            <pre>
            {escapar(response.text)}
            </pre>

            <a href="/">
            Voltar
            </a>

            """, 400

        try:

            token_data = response.json()

        except Exception:

            return """
            <h2>
            ❌ Resposta inválida.
            </h2>
            """, 400

        access_token = token_data.get(
            "access_token"
        )

        if not access_token:

            return """
            <h2>
            ❌ Access Token não recebido.
            </h2>
            """, 400

        session["access_token"] = (
            access_token
        )

        session["refresh_token"] = (
            token_data.get(
                "refresh_token"
            )
        )

        session.pop(
            "code_verifier",
            None
        )

        session.pop(
            "state",
            None
        )

        # ====================================================
        # USUÁRIO
        # ====================================================

        user_response = requisicao_get(
            f"{API_BASE}/users/me"
        )

        if user_response is None:

            return """
            <h1>
            ❌ Erro ao consultar usuário.
            </h1>
            """, 500

        if user_response.status_code != 200:

            return f"""

            <h1>
            ❌ Erro ao consultar conta.
            </h1>

            <pre>
            {escapar(user_response.text)}
            </pre>

            <a href="/">
            Voltar
            </a>

            """, 400

        user_data = (
            user_response.json()
        )

        nickname = user_data.get(
            "nickname",
            "usuário"
        )

        user_id = user_data.get(
            "id",
            ""
        )

        session["user_id"] = (
            user_id
        )

        return pagina_principal(
            nickname,
            user_id
        )

    # ========================================================
    # PKCE
    # ========================================================

    code_verifier = (
        secrets.token_urlsafe(64)
    )

    code_challenge = (

        base64.urlsafe_b64encode(

            hashlib.sha256(

                code_verifier.encode()

            ).digest()

        )
        .rstrip(b"=")
        .decode()
    )

    state = (
        secrets.token_urlsafe(32)
    )

    session["code_verifier"] = (
        code_verifier
    )

    session["state"] = state

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
        code_challenge,

        "code_challenge_method":
        "S256"
    }

    auth_url = (

        "https://auth.mercadolivre.com.br/"
        "authorization?"
        + urlencode(params)
    )

    return f"""

    <!DOCTYPE html>

    <html>

    <head>

    <meta charset="UTF-8">

    <meta
    name="viewport"
    content="width=device-width, initial-scale=1"
    >

    <title>
    Robô Ofertas ML
    </title>

    </head>

    <body style="
    font-family:Arial;
    background:#f5f5f5;
    padding:30px;
    text-align:center;
    ">

    <h1>
    🤖 Robô Ofertas ML
    </h1>

    <p>
    Conecte sua conta do Mercado Livre
    </p>

    <a href="{auth_url}">

    <button style="
    padding:15px 25px;
    font-size:18px;
    border:0;
    border-radius:8px;
    background:#3483fa;
    color:white;
    ">

    🔐 Conectar Mercado Livre

    </button>

    </a>

    </body>

    </html>

    """


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

def pagina_principal(
    nickname,
    user_id
):

    opcoes = ""

    for chave, dados in CATEGORIAS.items():

        opcoes += f"""

        <option value="{chave}">

        {dados["nome"]}

        </option>

        """

    return f"""

    <!DOCTYPE html>

    <html>

    <head>

    <meta charset="UTF-8">

    <meta
    name="viewport"
    content="width=device-width, initial-scale=1"
    >

    <title>
    Robô Ofertas ML
    </title>

    <style>

    body {{
        font-family:Arial;
        background:#f5f5f5;
        margin:0;
        padding:20px;
    }}

    .container {{
        max-width:700px;
        margin:auto;
        background:white;
        padding:25px;
        border-radius:15px;
    }}

    input,
    select {{
        width:100%;
        box-sizing:border-box;
        padding:15px;
        font-size:17px;
        border:1px solid #ccc;
        border-radius:8px;
        margin-bottom:12px;
    }}

    button {{
        width:100%;
        padding:15px;
        font-size:17px;
        border:0;
        border-radius:8px;
        background:#3483fa;
        color:white;
    }}

    .info {{
        background:#f5f5f5;
        padding:15px;
        border-radius:10px;
        margin-top:15px;
    }}

    </style>

    </head>

    <body>

    <div class="container">

    <h1>
    🤖 Robô Ofertas ML
    </h1>

    <p>
    ✅ Mercado Livre conectado!
    </p>

    <p>
    Usuário:
    <strong>
    {escapar(nickname)}
    </strong>
    </p>

    <p>
    ID:
    <strong>
    {escapar(user_id)}
    </strong>
    </p>

    <hr>

    <h2>
    🔎 Buscar produtos
    </h2>

    <form
    action="/buscar"
    method="get"
    >

    <label>
    📂 Categoria
    </label>

    <select
    name="categoria"
    >

    {opcoes}

    </select>

    <label>
    🔎 Produto
    </label>

    <input
    type="text"
    name="q"
    placeholder="Ex: iPhone 13, relógio, camisa..."
    required
    >

    <label>
    📈 Margem de lucro (%)
    </label>

    <input
    type="number"
    name="margem"
    value="{MARGEM_PADRAO}"
    min="0"
    max="100"
    step="1"
    >

    <label>
    💰 Lucro mínimo
    </label>

    <input
    type="number"
    name="lucro_minimo"
    value="{LUCRO_MINIMO_PADRAO}"
    min="0"
    step="1"
    >

    <button type="submit">
    🔎 Encontrar oportunidades
    </button>

    </form>

    <div class="info">

    <strong>
    💡 Como usar
    </strong>

    <p>
    1. Escolha uma categoria.
    </p>

    <p>
    2. Digite o produto.
    </p>

    <p>
    3. Escolha a margem.
    </p>

    <p>
    4. O robô procura produtos e anúncios.
    </p>

    <p>
    5. As melhores oportunidades aparecem primeiro.
    </p>

    </div>

    <br>

    <a href="/diagnostico">
    🧪 Diagnóstico
    </a>

    <br><br>

    <a href="/logout">
    🔓 Desconectar
    </a>

    </div>

    </body>

    </html>

    """


# ============================================================
# DESCOBRIR DOMÍNIO
# ============================================================

def descobrir_dominio(
    termo
):

    response = requisicao_get(

        f"{API_BASE}/sites/"
        f"{SITE_ID}/domain_discovery/search",

        {
            "q": termo,
            "limit": 5
        }

    )

    if response is None:

        return []

    if response.status_code != 200:

        return []

    try:

        return response.json()

    except Exception:

        return []


# ============================================================
# BUSCAR PRODUTOS
# ============================================================

def buscar_produtos_catalogo(
    termo,
    categoria="todas",
    offset=0,
    limit=20
):

    dados_categoria = CATEGORIAS.get(
        categoria,
        CATEGORIAS["todas"]
    )

    dominio = dados_categoria.get(
        "domain_id"
    )

    # ========================================================
    # CATEGORIA TODAS
    # ========================================================

    if categoria == "todas":

        dominios = descobrir_dominio(
            termo
        )

        if not dominios:

            return None

        # Primeiro domínio encontrado
        dominio = dominios[0].get(
            "domain_id"
        )

        if not dominio:

            return None

    # ========================================================
    # BUSCA
    # ========================================================

    params = {

        "status":
        "active",

        "site_id":
        SITE_ID,

        "q":
        termo,

        "offset":
        offset,

        "limit":
        limit
    }

    if dominio:

        params["domain_id"] = (
            dominio
        )

    return requisicao_get(

        f"{API_BASE}/products/search",

        params

    )


# ============================================================
# PUBLICAÇÕES
# ============================================================

def buscar_publicacoes(
    product_id
):

    response = requisicao_get(

        f"{API_BASE}/products/"
        f"{product_id}/items",

        {
            "offset": 0,
            "limit": 100
        }

    )

    if response is None:

        return []

    if response.status_code != 200:

        return []

    try:

        data = response.json()

        return data.get(
            "results",
            []
        )

    except Exception:

        return []


# ============================================================
# DETALHES
# ============================================================

def buscar_detalhes_itens(
    item_ids
):

    if not item_ids:

        return []

    resultados = []

    item_ids = list(
        dict.fromkeys(
            item_ids
        )
    )

    for inicio in range(
        0,
        len(item_ids),
        20
    ):

        bloco = item_ids[
            inicio:
            inicio + 20
        ]

        ids = ",".join(
            bloco
        )

        response = requisicao_get(

            f"{API_BASE}/items",

            {
                "ids": ids
            }

        )

        if response is None:
            continue

        if response.status_code != 200:
            continue

        try:

            data = response.json()

        except Exception:

            continue

        for resultado in data:

            if resultado.get(
                "code"
            ) != 200:

                continue

            body = resultado.get(
                "body"
            )

            if body:

                resultados.append(
                    body
                )

    return resultados


# ============================================================
# VENDEDORES
# ============================================================

def buscar_vendedores(
    seller_ids
):

    vendedores = {}

    seller_ids = list(
        dict.fromkeys(
            str(x)
            for x in seller_ids
            if x
        )
    )

    for seller_id in seller_ids:

        response = requisicao_get(

            f"{API_BASE}/users/"
            f"{seller_id}"

        )

        if response is None:
            continue

        if response.status_code != 200:
            continue

        try:

            data = response.json()

        except Exception:

            continue

        vendedores[
            seller_id
        ] = data.get(
            "nickname",
            f"Vendedor {seller_id}"
        )

    return vendedores


# ============================================================
# BUSCA PRINCIPAL
# ============================================================

@app.route("/buscar")
def buscar():

    termo = request.args.get(
        "q",
        ""
    ).strip()

    categoria = request.args.get(
        "categoria",
        "todas"
    )

    if categoria not in CATEGORIAS:

        categoria = "todas"

    if not termo:

        return """

        <h2>
        ❌ Digite um produto.
        </h2>

        <a href="/">
        ← Voltar
        </a>

        """, 400

    if not session.get(
        "access_token"
    ):

        return """

        <h1>
        ❌ Mercado Livre não conectado
        </h1>

        <a href="/">
        🔐 Conectar
        </a>

        """, 401

    # ========================================================
    # MARGEM
    # ========================================================

    try:

        margem = float(
            request.args.get(
                "margem",
                MARGEM_PADRAO
            )
        )

    except Exception:

        margem = MARGEM_PADRAO

    margem = max(
        0,
        min(
            margem,
            100
        )
    )

    # ========================================================
    # LUCRO MÍNIMO
    # ========================================================

    try:

        lucro_minimo = float(
            request.args.get(
                "lucro_minimo",
                LUCRO_MINIMO_PADRAO
            )
        )

    except Exception:

        lucro_minimo = (
            LUCRO_MINIMO_PADRAO
        )

    lucro_minimo = max(
        0,
        lucro_minimo
    )

    # ========================================================
    # OFFSET
    # ========================================================

    try:

        offset = int(
            request.args.get(
                "offset",
                0
            )
        )

    except Exception:

        offset = 0

    offset = max(
        0,
        offset
    )

    # ========================================================
    # CATÁLOGO
    # ========================================================

    response = buscar_produtos_catalogo(

        termo,

        categoria,

        offset,

        20

    )

    if response is None:

        return """

        <h1>
        ❌ Não foi possível realizar a busca.
        </h1>

        <p>
        Tente outro produto ou categoria.
        </p>

        <a href="/">
        ← Voltar
        </a>

        """, 500

    if response.status_code != 200:

        return f"""

        <h1>
        ❌ Erro na busca
        </h1>

        <p>
        Status:
        {response.status_code}
        </p>

        <pre>
        {escapar(response.text)}
        </pre>

        <br>

        <a href="/diagnostico">
        🧪 Diagnóstico
        </a>

        <br><br>

        <a href="/">
        ← Voltar
        </a>

        """, response.status_code

    try:

        data = response.json()

    except Exception:

        return """

        <h1>
        ❌ Resposta inválida
        </h1>

        """, 500

    produtos = data.get(
        "results",
        []
    )

    total_produtos = (
        data.get(
            "paging",
            {}
        ).get(
            "total",
            0
        )
    )

    # ========================================================
    # PEGAR PUBLICAÇÕES
    # ========================================================

    anuncios = []

    for produto in produtos:

        product_id = produto.get(
            "id",
            ""
        )

        domain_id = produto.get(
            "domain_id",
            ""
        )

        if not product_id:

            continue

        itens = buscar_publicacoes(
            product_id
        )

        for item in itens:

            item_id = (

                item.get(
                    "item_id"
                )

                or

                item.get(
                    "id"
                )
            )

            if not item_id:

                continue

            custo = numero(
                item.get(
                    "price"
                )
            )

            if custo <= 0:

                continue

            preco_venda = (

                custo *

                (
                    1 +
                    margem / 100
                )
            )

            lucro = (

                preco_venda -
                custo
            )

            if lucro < lucro_minimo:

                continue

            anuncios.append({

                "product_id":
                product_id,

                "product_name":
                produto.get(
                    "name",
                    "Produto"
                ),

                "domain_id":
                domain_id,

                "item_id":
                item_id,

                "price":
                custo,

                "preco_venda":
                preco_venda,

                "lucro":
                lucro,

                "seller_id":
                item.get(
                    "seller_id"
                ),

                "condition":
                item.get(
                    "condition",
                    "Não informado"
                ),

                "category_id":
                item.get(
                    "category_id",
                    ""
                ),

                "sold_quantity":
                item.get(
                    "sold_quantity",
                    0
                ),

                "available_quantity":
                item.get(
                    "available_quantity"
                ),

                "permalink":
                item.get(
                    "permalink",
                    ""
                ),

                "thumbnail":
                item.get(
                    "thumbnail",
                    ""
                ),

                "title":
                item.get(
                    "title",
                    produto.get(
                        "name",
                        "Produto"
                    )
                )
            })


    # ========================================================
    # DETALHES
    # ========================================================

    ids = [

        anuncio[
            "item_id"
        ]

        for anuncio in anuncios
    ]

    detalhes = (
        buscar_detalhes_itens(
            ids
        )
    )

    detalhes_map = {}

    for detalhe in detalhes:

        item_id = detalhe.get(
            "id"
        )

        if item_id:

            detalhes_map[
                item_id
            ] = detalhe

    for anuncio in anuncios:

        detalhe = detalhes_map.get(
            anuncio["item_id"]
        )

        if not detalhe:

            continue

        for campo in [

            "price",
            "title",
            "seller_id",
            "condition",
            "category_id",
            "sold_quantity",
            "available_quantity",
            "permalink",
            "thumbnail"

        ]:

            if detalhe.get(
                campo
            ) is not None:

                anuncio[campo] = (
                    detalhe.get(
                        campo
                    )
                )

        custo = numero(
            anuncio.get(
                "price"
            )
        )

        anuncio["preco_venda"] = (

            custo *

            (
                1 +
                margem / 100
            )
        )

        anuncio["lucro"] = (

            anuncio["preco_venda"] -
            custo
        )

    # ========================================================
    # FILTRAR
    # ========================================================

    anuncios = [

        anuncio

        for anuncio in anuncios

        if anuncio.get(
            "lucro",
            0
        ) >= lucro_minimo
    ]

    # ========================================================
    # DUPLICADOS
    # ========================================================

    unicos = {}

    for anuncio in anuncios:

        unicos[
            anuncio["item_id"]
        ] = anuncio

    anuncios = list(
        unicos.values()
    )

    # ========================================================
    # ORDENAR PELO LUCRO
    # ========================================================

    anuncios.sort(

        key=lambda anuncio:

        anuncio.get(
            "lucro",
            0
        ),

        reverse=True
    )

    # ========================================================
    # VENDEDORES
    # ========================================================

    seller_ids = [

        anuncio.get(
            "seller_id"
        )

        for anuncio in anuncios
    ]

    vendedores = (
        buscar_vendedores(
            seller_ids
        )
    )

    categoria_nome = CATEGORIAS[
        categoria
    ]["nome"]

    # ========================================================
    # HTML
    # ========================================================

    pagina = f"""

    <!DOCTYPE html>

    <html>

    <head>

    <meta charset="UTF-8">

    <meta
    name="viewport"
    content="width=device-width, initial-scale=1"
    >

    <title>
    Oportunidades
    </title>

    <style>

    body {{
        font-family:Arial;
        background:#f5f5f5;
        margin:0;
        padding:15px;
    }}

    .container {{
        max-width:1000px;
        margin:auto;
    }}

    .top {{
        background:white;
        padding:20px;
        border-radius:12px;
        margin-bottom:15px;
    }}

    .card {{
        background:white;
        padding:18px;
        border-radius:12px;
        margin-bottom:15px;
        box-shadow:
        0 2px 8px rgba(0,0,0,.08);
    }}

    .card img {{
        max-width:220px;
        max-height:220px;
        object-fit:contain;
        display:block;
        margin-bottom:12px;
    }}

    .custo {{
        color:#555;
        font-size:18px;
    }}

    .venda {{
        color:#008000;
        font-size:28px;
        font-weight:bold;
        margin:10px 0;
    }}

    .lucro {{
        background:#d4edda;
        color:#155724;
        padding:12px;
        border-radius:8px;
        font-size:21px;
        font-weight:bold;
        margin:10px 0;
    }}

    .margem {{
        background:#e7f1ff;
        padding:10px;
        border-radius:8px;
        margin:10px 0;
    }}

    .info {{
        color:#555;
        margin:7px 0;
    }}

    .botao {{
        display:inline-block;
        background:#3483fa;
        color:white;
        padding:13px 20px;
        border-radius:8px;
        text-decoration:none;
        margin-top:10px;
    }}

    .whatsapp {{
        display:inline-block;
        background:#25D366;
        color:white;
        padding:13px 20px;
        border-radius:8px;
        text-decoration:none;
        margin-top:10px;
    }}

    .melhor {{
        background:#fff3cd;
        padding:10px;
        border-radius:8px;
        display:inline-block;
        font-weight:bold;
        margin-bottom:10px;
    }}

    .nenhum {{
        background:white;
        padding:20px;
        border-radius:12px;
    }}

    </style>

    </head>

    <body>

    <div class="container">

    <div class="top">

    <h1>
    🔥 Oportunidades de revenda
    </h1>

    <h2>
    {categoria_nome}
    </h2>

    <h2>
    🔎 {escapar(termo)}
    </h2>

    <p>
    📦 Produtos encontrados:
    <strong>
    {total_produtos}
    </strong>
    </p>

    <p>
    🛒 Oportunidades:
    <strong>
    {len(anuncios)}
    </strong>
    </p>

    <p>
    📈 Margem:
    <strong>
    {margem:.0f}%
    </strong>
    </p>

    <p>
    💰 Lucro mínimo:
    <strong>
    {formatar_preco(lucro_minimo)}
    </strong>
    </p>

    </div>

    """

    # ========================================================
    # NENHUM
    # ========================================================

    if not anuncios:

        pagina += f"""

        <div class="nenhum">

        <h2>
        😕 Nenhuma oportunidade encontrada
        </h2>

        <p>
        Não encontramos anúncios com lucro
        mínimo de
        <strong>
        {formatar_preco(lucro_minimo)}
        </strong>.
        </p>

        <p>
        Tente diminuir o lucro mínimo,
        mudar a margem ou pesquisar outro produto.
        </p>

        </div>

        """

    # ========================================================
    # CARDS
    # ========================================================

    for indice, anuncio in enumerate(
        anuncios
    ):

        titulo = anuncio.get(
            "title",
            "Produto"
        )

        item_id = anuncio.get(
            "item_id",
            ""
        )

        custo = anuncio.get(
            "price",
            0
        )

        preco_venda = anuncio.get(
            "preco_venda",
            0
        )

        lucro = anuncio.get(
            "lucro",
            0
        )

        seller_id = anuncio.get(
            "seller_id"
        )

        seller_nome = vendedores.get(

            str(seller_id),

            f"Vendedor {seller_id}"
        )

        vendidos = anuncio.get(
            "sold_quantity",
            0
        )

        condicao = anuncio.get(
            "condition",
            "Não informado"
        )

        categoria_anuncio = anuncio.get(
            "category_id",
            ""
        )

        link = anuncio.get(
            "permalink",
            ""
        )

        imagem = anuncio.get(
            "thumbnail",
            ""
        )

        if not link:

            link = (
                "https://www.mercadolivre.com.br/"
                + item_id
            )

        mensagem = (

            f"🛍️ {titulo}\n\n"

            f"💰 Preço: "
            f"{formatar_preco(preco_venda)}\n\n"

            f"🔥 Oferta encontrada!\n\n"

            f"🛒 Comprar:\n"
            f"{link}"
        )

        whatsapp_url = (

            "https://wa.me/?text="

            + quote(
                mensagem
            )
        )

        pagina += """

        <div class="card">

        """

        if indice == 0:

            pagina += """

            <div class="melhor">

            🏆 MELHOR OPORTUNIDADE

            </div>

            """

        if imagem:

            pagina += f"""

            <img
            src="{escapar(imagem)}"
            alt="{escapar(titulo)}"
            loading="lazy"
            >

            """

        pagina += f"""

        <h2>
        🛍️ {escapar(titulo)}
        </h2>

        <div class="custo">

        💵 Compra:

        <strong>
        {formatar_preco(custo)}
        </strong>

        </div>

        <div class="margem">

        📈 Margem:

        <strong>
        {margem:.0f}%
        </strong>

        </div>

        <div class="venda">

        🏷️ Revenda:

        {formatar_preco(preco_venda)}

        </div>

        <div class="lucro">

        💰 Lucro estimado:

        {formatar_preco(lucro)}

        </div>

        <div class="info">

        👤 Vendedor:
        <strong>
        {escapar(seller_nome)}
        </strong>

        </div>

        <div class="info">

        🔥 Vendidos:
        <strong>
        {escapar(vendidos)}
        </strong>

        </div>

        <div class="info">

        🏷️ Condição:
        {escapar(condicao)}

        </div>

        <div class="info">

        📂 Categoria:
        {escapar(categoria_anuncio)}

        </div>

        <div class="info">

        🌐 Domínio:
        {escapar(anuncio.get("domain_id"))}

        </div>

        <div class="info">

        🆔 Anúncio:
        {escapar(item_id)}

        </div>

        <a
        class="botao"
        href="{escapar(link)}"
        target="_blank"
        rel="noopener noreferrer"
        >

        🛒 Ver anúncio

        </a>

        <a
        class="whatsapp"
        href="{escapar(whatsapp_url)}"
        target="_blank"
        rel="noopener noreferrer"
        >

        📲 Enviar no WhatsApp

        </a>

        </div>

        """

    # ========================================================
    # VOLTAR
    # ========================================================

    pagina += """

    <br>

    <a href="/">
    ← Nova pesquisa
    </a>

    <br><br>

    <a href="/diagnostico">
    🧪 Diagnóstico
    </a>

    </div>

    </body>

    </html>

    """

    return pagina


# ============================================================
# DIAGNÓSTICO
# ============================================================

@app.route("/diagnostico")
def diagnostico():

    if not session.get(
        "access_token"
    ):

        return """

        <h1>
        ❌ Conta não conectada
        </h1>

        <a href="/">
        ← Voltar
        </a>

        """, 401

    testes = [

        (
            "1️⃣ /users/me",

            f"{API_BASE}/users/me",

            None
        ),

        (
            "2️⃣ Busca de produtos",

            f"{API_BASE}/products/search",

            {
                "status":
                "active",

                "site_id":
                SITE_ID,

                "q":
                "iPhone 13",

                "domain_id":
                "MLB-CELLPHONES",

                "limit":
                5
            }
        ),

        (
            "3️⃣ Domain Discovery",

            f"{API_BASE}/sites/"
            f"{SITE_ID}/domain_discovery/search",

            {
                "q":
                "relógio",

                "limit":
                5
            }
        ),

        (
            "4️⃣ Produto MLB18500856",

            f"{API_BASE}/products/"
            f"MLB18500856",

            None
        ),

        (
            "5️⃣ Publicações MLB18500856",

            f"{API_BASE}/products/"
            f"MLB18500856/items",

            {
                "offset":
                0,

                "limit":
                100
            }
        )

    ]

    blocos = []

    for nome, url, params in testes:

        response = requisicao_get(
            url,
            params
        )

        if response is None:

            blocos.append(f"""

            <div style="
            background:#f8d7da;
            padding:15px;
            margin-bottom:15px;
            border-radius:10px;
            ">

            <h2>
            {escapar(nome)}
            </h2>

            <p>
            ❌ Falha de conexão
            </p>

            </div>

            """)

            continue

        texto = response.text

        if len(texto) > 10000:

            texto = (
                texto[:10000]
                + "\n\n... cortado ..."
            )

        blocos.append(f"""

        <div style="
        background:#f8f8f8;
        padding:15px;
        margin-bottom:15px;
        border-radius:10px;
        overflow:auto;
        ">

        <h2>
        {escapar(nome)}
        </h2>

        <p>
        Status:
        <strong>
        {response.status_code}
        </strong>
        </p>

        <pre>
        {escapar(texto)}
        </pre>

        </div>

        """)

    return f"""

    <!DOCTYPE html>

    <html>

    <head>

    <meta charset="UTF-8">

    <meta
    name="viewport"
    content="width=device-width, initial-scale=1"
    >

    <title>
    Diagnóstico
    </title>

    </head>

    <body style="
    font-family:Arial;
    background:#f5f5f5;
    padding:20px;
    ">

    <div style="
    max-width:950px;
    margin:auto;
    background:white;
    padding:20px;
    border-radius:12px;
    ">

    <h1>
    🧪 Diagnóstico Mercado Livre
    </h1>

    {"".join(blocos)}

    <a href="/">
    ← Voltar
    </a>

    </div>

    </body>

    </html>

    """


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return """

    <h1>
    🔓 Desconectado
    </h1>

    <p>
    Sessão encerrada.
    </p>

    <a href="/">
    🔐 Conectar novamente
    </a>

    """


# ============================================================
# TESTE CONFIG
# ============================================================

@app.route("/teste-config")
def teste_config():

    return f"""

    <h1>
    🧪 Configuração
    </h1>

    <p>
    CLIENT_ID:
    <strong>
    {"OK" if CLIENT_ID else "FALTANDO"}
    </strong>
    </p>

    <p>
    CLIENT_SECRET:
    <strong>
    {"OK" if CLIENT_SECRET else "FALTANDO"}
    </strong>
    </p>

    <p>
    REDIRECT_URI:
    <strong>
    {
        escapar(REDIRECT_URI)
        if REDIRECT_URI
        else "FALTANDO"
    }
    </strong>
    </p>

    <p>
    SECRET_KEY:
    <strong>
    {"OK" if SECRET_KEY else "FALTANDO"}
    </strong>
    </p>

    <hr>

    <a href="/">
    ← Voltar
    </a>

    """


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=int(
            os.getenv(
                "PORT",
                10000
            )
        )

    )
