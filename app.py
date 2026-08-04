import os
import secrets
import hashlib
import base64
import requests
import html

from urllib.parse import urlencode
from flask import Flask, request, session, redirect

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

SITE_ID = "MLB"

API_BASE = "https://api.mercadolibre.com"


# ============================================================
# FORMATAÇÃO
# ============================================================

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

    except:

        return "Preço indisponível"


def escapar(valor):

    return html.escape(
        str(valor or "")
    )


def calcular_desconto(
    preco_atual,
    preco_original
):

    try:

        atual = float(preco_atual)
        original = float(preco_original)

        if original > atual:

            desconto = (
                (original - atual)
                / original
                * 100
            )

            return round(
                desconto
            )

    except:

        pass

    return 0


# ============================================================
# REQUISIÇÃO À API
# ============================================================

def api_get(
    endpoint,
    access_token,
    params=None
):

    try:

        response = requests.get(

            API_BASE + endpoint,

            headers={
                "Authorization":
                    f"Bearer {access_token}"
            },

            params=params or {},

            timeout=30,
        )

        return response

    except requests.RequestException as erro:

        return None


# ============================================================
# PÁGINA INICIAL
# ============================================================

@app.route("/")
def home():

    code = request.args.get(
        "code"
    )

    state = request.args.get(
        "state"
    )


    # ========================================================
    # VERIFICA CONFIGURAÇÕES
    # ========================================================

    if not CLIENT_ID:

        return (
            "ML_CLIENT_ID não configurado no Render.",
            500
        )


    if not CLIENT_SECRET:

        return (
            "ML_CLIENT_SECRET não configurado no Render.",
            500
        )


    if not REDIRECT_URI:

        return (
            "ML_REDIRECT_URI não configurado no Render.",
            500
        )


    # ========================================================
    # CALLBACK DO MERCADO LIVRE
    # ========================================================

    if code:

        saved_state = session.get(
            "state"
        )


        if not saved_state:

            return """
            <h2>Erro: sessão expirada.</h2>

            <p>
                Volte para o início e conecte novamente sua conta.
            </p>

            <a href="/">
                Voltar
            </a>
            """, 400


        if state != saved_state:

            return """
            <h2>Erro: state inválido.</h2>

            <a href="/">
                Voltar
            </a>
            """, 400


        code_verifier = session.get(
            "code_verifier"
        )


        if not code_verifier:

            return """
            <h2>
                Erro: code_verifier não encontrado.
            </h2>

            <a href="/">
                Voltar
            </a>
            """, 400


        # ====================================================
        # TROCA CODE POR TOKEN
        # ====================================================

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
                    code_verifier,
            },

            timeout=30,
        )


        if response.status_code != 200:

            return f"""
            <h1>Erro ao obter token</h1>

            <p>
                Status:
                <strong>
                    {response.status_code}
                </strong>
            </p>

            <pre>
{escapar(response.text)}
            </pre>

            <a href="/">
                Voltar
            </a>
            """, 400


        token_data = response.json()


        access_token = token_data.get(
            "access_token"
        )


        if not access_token:

            return """
            <h2>
                Access Token não recebido.
            </h2>

            <a href="/">
                Voltar
            </a>
            """, 400


        # ====================================================
        # LIMPA PKCE
        # ====================================================

        session.pop(
            "code_verifier",
            None
        )

        session.pop(
            "state",
            None
        )


        # ====================================================
        # CONSULTA USUÁRIO
        # ====================================================

        user_response = api_get(

            "/users/me",

            access_token
        )


        if not user_response:

            return """
            <h2>
                Erro de conexão com Mercado Livre.
            </h2>

            <a href="/">
                Voltar
            </a>
            """, 500


        if user_response.status_code != 200:

            return f"""
            <h1>
                Erro ao consultar conta
            </h1>

            <p>
                Status:
                {user_response.status_code}
            </p>

            <pre>
{escapar(user_response.text)}
            </pre>

            <a href="/">
                Voltar
            </a>
            """, 400


        user_data = user_response.json()


        nickname = user_data.get(
            "nickname",
            "usuário"
        )


        user_id = user_data.get(
            "id",
            "não informado"
        )


        # ====================================================
        # GUARDA TOKEN NA SESSÃO
        # ====================================================

        session["access_token"] = (
            access_token
        )

        session["user_id"] = (
            user_id
        )


        return pagina_principal(
            nickname,
            user_id
        )


    # ========================================================
    # CRIA PKCE
    # ========================================================

    code_verifier = secrets.token_urlsafe(
        64
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


    state = secrets.token_urlsafe(
        32
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
            "S256",
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
            content="width=device-width,
                     initial-scale=1.0"
        >

        <title>
            Robô Ofertas ML
        </title>

        <style>

            body {{
                font-family: Arial;
                background: #f5f5f5;
                padding: 30px;
                text-align: center;
            }}

            .box {{
                max-width: 500px;
                margin: auto;
                background: white;
                padding: 30px;
                border-radius: 15px;
            }}

            button {{
                padding: 15px 25px;
                font-size: 18px;
                border: 0;
                border-radius: 8px;
                background: #3483fa;
                color: white;
            }}

        </style>

    </head>

    <body>

        <div class="box">

            <h1>
                🤖 Robô Ofertas ML
            </h1>

            <p>
                Conecte sua conta do Mercado Livre
            </p>

            <a href="{auth_url}">

                <button>
                    🔐 Conectar Mercado Livre
                </button>

            </a>

        </div>

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

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width,
                     initial-scale=1.0"
        >

        <title>
            Robô Ofertas ML
        </title>

        <style>

            body {{
                font-family: Arial;
                background: #f5f5f5;
                margin: 0;
                padding: 20px;
            }}

            .container {{
                max-width: 700px;
                margin: auto;
                background: white;
                padding: 25px;
                border-radius: 15px;
            }}

            input {{
                width: 100%;
                box-sizing: border-box;
                padding: 14px;
                font-size: 17px;
                border: 1px solid #ccc;
                border-radius: 8px;
                margin-bottom: 10px;
            }}

            button {{
                width: 100%;
                padding: 14px;
                font-size: 17px;
                border: 0;
                border-radius: 8px;
                background: #3483fa;
                color: white;
                cursor: pointer;
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
                🔎 Produtos atuais
            </h2>

            <p>
                Pesquise qualquer produto.
                Os resultados serão organizados
                priorizando os anúncios com mais vendas.
            </p>

            <form
                action="/buscar"
                method="get"
            >

                <input
                    type="text"
                    name="q"
                    placeholder="Ex: celular, tênis, relógio..."
                    required
                >

                <button type="submit">
                    🔥 Buscar mais vendidos
                </button>

            </form>

            <br>

            <a href="/mais-vendidos"
               style="
                    display:block;
                    text-align:center;
                    background:#ffe600;
                    padding:14px;
                    border-radius:8px;
                    color:#333;
                    text-decoration:none;
                    font-weight:bold;
               ">
                🏆 Ver produtos mais vendidos
            </a>

        </div>

    </body>

    </html>
    """


# ============================================================
# BUSCA DE PRODUTOS
# ============================================================

@app.route("/buscar")
def buscar():

    termo = request.args.get(
        "q",
        ""
    ).strip()


    if not termo:

        return """
        <h2>
            Digite um produto.
        </h2>

        <a href="/">
            Voltar
        </a>
        """, 400


    access_token = session.get(
        "access_token"
    )


    if not access_token:

        return """
        <h2>
            Conta não conectada.
        </h2>

        <a href="/">
            Conectar Mercado Livre
        </a>
        """, 401


    try:

        offset = int(
            request.args.get(
                "offset",
                0
            )
        )

    except:

        offset = 0


    # ========================================================
    # 50 RESULTADOS
    # ========================================================

    limit = 50


    # ========================================================
    # BUSCA ATUAL
    #
    # sold_quantity_desc:
    # prioriza os anúncios com maior quantidade vendida.
    # ========================================================

    response = api_get(

        f"/sites/{SITE_ID}/search",

        access_token,

        params={

            "q":
                termo,

            "limit":
                limit,

            "offset":
                offset,

            "status":
                "active",

            "sort":
                "sold_quantity_desc",
        }
    )


    # ========================================================
    # FALLBACK
    #
    # Algumas buscas podem não aceitar a ordenação.
    # Nesse caso fazemos uma busca normal e ordenamos
    # localmente pelos dados retornados.
    # ========================================================

    if not response:

        return erro_api(
            "Erro de conexão com Mercado Livre."
        )


    if response.status_code != 200:

        response_fallback = api_get(

            f"/sites/{SITE_ID}/search",

            access_token,

            params={

                "q":
                    termo,

                "limit":
                    limit,

                "offset":
                    offset,

                "status":
                    "active",
            }
        )


        if (
            response_fallback
            and
            response_fallback.status_code == 200
        ):

            response = response_fallback

        else:

            return erro_api(
                response.text,
                response.status_code
            )


    data = response.json()


    produtos = data.get(
        "results",
        []
    )


    # ========================================================
    # REMOVE PRODUTOS SEM PREÇO
    # ========================================================

    produtos = [

        produto

        for produto in produtos

        if produto.get("price") is not None

    ]


    # ========================================================
    # ORDENA PELOS MAIS VENDIDOS
    # ========================================================

    produtos.sort(

        key=lambda produto:
            int(
                produto.get(
                    "sold_quantity",
                    0
                ) or 0
            ),

        reverse=True
    )


    paging = data.get(
        "paging",
        {}
    )


    total = paging.get(
        "total",
        0
    )


    # ========================================================
    # HTML
    # ========================================================

    html_page = f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width,
                     initial-scale=1.0"
        >

        <title>
            Mais vendidos - {escapar(termo)}
        </title>

        <style>

            body {{
                font-family: Arial;
                background: #f5f5f5;
                margin: 0;
                padding: 15px;
            }}

            .container {{
                max-width: 1000px;
                margin: auto;
            }}

            .top {{
                background: white;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 15px;
            }}

            .produto {{
                background: white;
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 15px;
                box-shadow:
                    0 2px 8px
                    rgba(0,0,0,.08);
            }}

            .produto img {{
                width: 200px;
                height: 200px;
                object-fit: contain;
                display: block;
                margin-bottom: 10px;
                border-radius: 10px;
            }}

            .preco {{
                font-size: 26px;
                font-weight: bold;
                color: #008000;
                margin: 8px 0;
            }}

            .preco-original {{
                color: #777;
                text-decoration: line-through;
                font-size: 15px;
            }}

            .desconto {{
                display: inline-block;
                background: #00a650;
                color: white;
                padding: 5px 8px;
                border-radius: 5px;
                font-weight: bold;
                margin-bottom: 8px;
            }}

            .vendidos {{
                font-size: 17px;
                color: #333;
                margin: 8px 0;
            }}

            .estoque {{
                color: #555;
                margin: 6px 0;
            }}

            .atualizado {{
                color: #777;
                font-size: 13px;
                margin: 8px 0;
            }}

            .botao {{
                display: inline-block;
                background: #3483fa;
                color: white;
                padding: 12px 18px;
                border-radius: 8px;
                text-decoration: none;
                margin-top: 10px;
            }}

            .ranking {{
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 8px;
            }}

            .paginas {{
                display: flex;
                justify-content: space-between;
                gap: 10px;
                margin: 20px 0;
            }}

            .paginas a {{
                background: #3483fa;
                color: white;
                padding: 12px 18px;
                border-radius: 8px;
                text-decoration: none;
            }}

            .voltar {{
                display: inline-block;
                margin-top: 10px;
            }}

        </style>

    </head>

    <body>

    <div class="container">

        <div class="top">

            <h1>
                🔥 {escapar(termo)}
            </h1>

            <p>
                <strong>
                    Produtos atuais mais vendidos
                </strong>
            </p>

            <p>
                Total encontrado:
                <strong>
                    {total}
                </strong>
            </p>

            <p>
                🟢 Anúncios ativos
            </p>

            <a
                class="voltar"
                href="/"
            >
                ← Nova pesquisa
            </a>

        </div>
    """


    if not produtos:

        html_page += """

        <div class="produto">

            <h2>
                Nenhum produto encontrado.
            </h2>

        </div>

        """


    # ========================================================
    # PRODUTOS
    # ========================================================

    for posicao, produto in enumerate(
        produtos,
        start=offset + 1
    ):

        item_id = produto.get(
            "id",
            ""
        )


        titulo = produto.get(
            "title",
            "Produto sem título"
        )


        preco = produto.get(
            "price"
        )


        preco_original = produto.get(
            "original_price"
        )


        vendidos = produto.get(
            "sold_quantity",
            0
        ) or 0


        estoque = produto.get(
            "available_quantity"
        )


        link = produto.get(
            "permalink",
            "#"
        )


        imagem = produto.get(
            "thumbnail",
            ""
        )


        categoria = produto.get(
            "category_id",
            "Não informada"
        )


        condicao = produto.get(
            "condition",
            ""
        )


        atualizado = produto.get(
            "last_updated",
            ""
        )


        preco_texto = formatar_preco(
            preco
        )


        preco_original_texto = ""


        if preco_original:

            preco_original_texto = f"""
            <div class="preco-original">
                De {formatar_preco(preco_original)}
            </div>
            """


        desconto = calcular_desconto(
            preco,
            preco_original
        )


        desconto_html = ""


        if desconto > 0:

            desconto_html = f"""
            <div class="desconto">
                🔥 {desconto}% OFF
            </div>
            """


        estoque_texto = (
            str(estoque)
            if estoque is not None
            else "Não informado"
        )


        html_page += f"""

        <div class="produto">

            <div class="ranking">
                🏆 #{posicao}
            </div>

            <img
                src="{escapar(imagem)}"
                alt="{escapar(titulo)}"
                loading="lazy"
            >

            <h2>
                {escapar(titulo)}
            </h2>

            {desconto_html}

            {preco_original_texto}

            <div class="preco">
                {preco_texto}
            </div>

            <div class="vendidos">

                🔥
                <strong>
                    {vendidos}
                </strong>

                vendidos

            </div>

            <div class="estoque">

                📦 Estoque:
                <strong>
                    {escapar(estoque_texto)}
                </strong>

            </div>

            <div>

                📂 Categoria:
                {escapar(categoria)}

            </div>

            <div>

                🏷️
                {escapar(condicao)}

            </div>

            <div class="atualizado">

                🕒 Última atualização:
                {escapar(atualizado)}

            </div>

            <div class="atualizado">

                ID:
                {escapar(item_id)}

            </div>

            <a
                class="botao"
                href="{escapar(link)}"
                target="_blank"
                rel="noopener"
            >
                🛒 Ver anúncio atual
            </a>

        </div>

        """


    # ========================================================
    # PAGINAÇÃO
    # ========================================================

    html_page += """
        <div class="paginas">
    """


    if offset > 0:

        anterior = max(
            0,
            offset - limit
        )


        html_page += f"""

        <a
            href="/buscar?q={escapar(termo)}&offset={anterior}"
        >
            ← Anterior
        </a>

        """

    else:

        html_page += "<span></span>"


    if offset + limit < total:

        proximo = offset + limit


        html_page += f"""

        <a
            href="/buscar?q={escapar(termo)}&offset={proximo}"
        >
            Próximos 50 →
        </a>

        """


    html_page += """

        </div>

    </div>

    </body>

    </html>
    """


    return html_page


# ============================================================
# MAIS VENDIDOS
# ============================================================

@app.route("/mais-vendidos")
def mais_vendidos():

    access_token = session.get(
        "access_token"
    )


    if not access_token:

        return redirect("/")


    # ========================================================
    # CATEGORIAS / HIGHLIGHTS
    #
    # A API oficial disponibiliza o TOP 20 por categoria.
    # ========================================================

    response = api_get(

        f"/highlights/{SITE_ID}/category/MLB1055",

        access_token
    )


    # Se a categoria acima não estiver disponível,
    # mostramos uma busca geral como fallback.

    if (
        not response
        or
        response.status_code != 200
    ):

        return redirect(
            "/buscar?q=ofertas"
        )


    data = response.json()


    produtos = data.get(
        "content",
        []
    )


    html_page = """

    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width,
                     initial-scale=1.0"
        >

        <title>
            Mais vendidos
        </title>

        <style>

            body {
                font-family: Arial;
                background: #f5f5f5;
                padding: 15px;
            }

            .container {
                max-width: 900px;
                margin: auto;
            }

            .box {
                background: white;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 15px;
            }

            .botao {
                display: inline-block;
                background: #3483fa;
                color: white;
                padding: 12px 18px;
                border-radius: 8px;
                text-decoration: none;
            }

        </style>

    </head>

    <body>

    <div class="container">

        <div class="box">

            <h1>
                🏆 Mais vendidos
            </h1>

            <p>
                Ranking atual disponibilizado pelo
                Mercado Livre.
            </p>

            <a
                class="botao"
                href="/"
            >
                ← Voltar
            </a>

        </div>

    """


    for posicao, produto in enumerate(
        produtos,
        start=1
    ):

        produto_id = (
            produto.get("id")
            if isinstance(
                produto,
                dict
            )
            else ""
        )


        html_page += f"""

        <div class="box">

            <h2>
                #{posicao}
            </h2>

            <p>
                Produto:
                <strong>
                    {escapar(produto_id)}
                </strong>
            </p>

        </div>

        """


    html_page += """

    </div>

    </body>

    </html>

    """


    return html_page


# ============================================================
# ERRO DA API
# ============================================================

def erro_api(
    mensagem,
    status=500
):

    return f"""

    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width,
                     initial-scale=1.0"
        >

        <title>
            Erro
        </title>

    </head>

    <body style="
        font-family:Arial;
        padding:30px;
        background:#f5f5f5;
    ">

        <div style="
            max-width:700px;
            margin:auto;
            background:white;
            padding:25px;
            border-radius:12px;
        ">

            <h1>
                ❌ Erro na busca
            </h1>

            <p>
                Status da API:
                <strong>
                    {status}
                </strong>
            </p>

            <pre>
{escapar(mensagem)}
            </pre>

            <a href="/">
                ← Voltar
            </a>

        </div>

    </body>

    </html>

    """, status


# ============================================================
# TESTE DE CONFIGURAÇÃO
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
            {escapar(REDIRECT_URI)
             if REDIRECT_URI
             else "FALTANDO"}
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
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


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
