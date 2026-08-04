import os
import secrets
import hashlib
import base64
import requests

from urllib.parse import urlencode
from flask import Flask, request, session

app = Flask(__name__)

# ============================================================
# CONFIGURAÇÕES
# ============================================================

CLIENT_ID = os.getenv("ML_CLIENT_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ML_REDIRECT_URI")

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
app.secret_key = SECRET_KEY


# ============================================================
# PÁGINA INICIAL / LOGIN MERCADO LIVRE
# ============================================================

@app.route("/")
def home():

    code = request.args.get("code")
    state = request.args.get("state")

    if not CLIENT_ID:
        return "ML_CLIENT_ID não configurado no Render.", 500

    if not CLIENT_SECRET:
        return "ML_CLIENT_SECRET não configurado no Render.", 500

    if not REDIRECT_URI:
        return "ML_REDIRECT_URI não configurado no Render.", 500

    # ========================================================
    # RETORNO DO MERCADO LIVRE
    # ========================================================

    if code:

        if state != session.get("state"):
            return "Erro: state inválido.", 400

        code_verifier = session.get("code_verifier")

        if not code_verifier:
            return "Erro: code_verifier não encontrado.", 400

        # Troca authorization code por access token
        response = requests.post(
            "https://api.mercadolibre.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": code_verifier,
            },
            timeout=30,
        )

        if response.status_code != 200:
            return f"""
            <h1>Erro ao obter token</h1>
            <pre>{response.text}</pre>
            """, 400

        token_data = response.json()

        access_token = token_data.get("access_token")

        if not access_token:
            return "Erro: Access Token não recebido.", 400

        # ====================================================
        # TESTA A CONTA
        # ====================================================

        user_response = requests.get(
            "https://api.mercadolibre.com/users/me",
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            timeout=30,
        )

        if user_response.status_code != 200:
            return f"""
            <h1>Erro ao consultar conta</h1>
            <pre>{user_response.text}</pre>
            """, 400

        user_data = user_response.json()

        nickname = user_data.get("nickname", "usuário")
        user_id = user_data.get("id", "não informado")

        # Guarda token
        session["access_token"] = access_token

        return f"""
        <!DOCTYPE html>
        <html>

        <head>
            <meta charset="UTF-8">

            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">

            <title>Robô Ofertas ML</title>

            <style>

                body {{
                    font-family: Arial, sans-serif;
                    background: #f5f5f5;
                    padding: 20px;
                    margin: 0;
                }}

                .container {{
                    max-width: 700px;
                    margin: auto;
                    background: white;
                    padding: 25px;
                    border-radius: 15px;
                    box-shadow: 0 2px 10px rgba(0,0,0,.08);
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
                }}

            </style>

        </head>

        <body>

        <div class="container">

            <h1>🤖 Robô Ofertas ML</h1>

            <p>
                ✅ Mercado Livre conectado!
            </p>

            <p>
                Usuário:
                <strong>{nickname}</strong>
            </p>

            <p>
                ID:
                <strong>{user_id}</strong>
            </p>

            <hr>

            <h2>🔎 Buscar produtos</h2>

            <form action="/buscar" method="get">

                <input
                    type="text"
                    name="q"
                    placeholder="Digite um produto"
                    required
                >

                <button type="submit">
                    Buscar produtos
                </button>

            </form>

        </div>

        </body>

        </html>
        """


    # ========================================================
    # PKCE
    # ========================================================

    code_verifier = secrets.token_urlsafe(64)

    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(
            code_verifier.encode()
        ).digest()
    ).rstrip(b"=").decode()

    state = secrets.token_urlsafe(32)

    session["code_verifier"] = code_verifier
    session["state"] = state

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    auth_url = (
        "https://auth.mercadolivre.com.br/authorization?"
        + urlencode(params)
    )

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>Robô Ofertas ML</title>

    </head>

    <body style="
        font-family:Arial;
        background:#f5f5f5;
        padding:30px;
        text-align:center;
    ">

        <h1>🤖 Robô Ofertas ML</h1>

        <p>
            Conecte sua conta do Mercado Livre:
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
# BUSCA DE PRODUTOS
# ============================================================

@app.route("/buscar")
def buscar():

    termo = request.args.get("q", "").strip()

    if not termo:
        return "Digite um produto para pesquisar.", 400

    access_token = session.get("access_token")

    if not access_token:
        return """
        <h1>Conta não conectada</h1>
        <a href="/">Voltar e conectar</a>
        """, 401

    # --------------------------------------------------------
    # PAGINAÇÃO
    # --------------------------------------------------------

    try:
        offset = int(request.args.get("offset", 0))
    except:
        offset = 0

    limit = 50

    # --------------------------------------------------------
    # BUSCA DE PRODUTOS
    # --------------------------------------------------------

    response = requests.get(
        "https://api.mercadolibre.com/products/search",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        params={
            "site_id": "MLB",
            "status": "active",
            "q": termo,
            "limit": limit,
            "offset": offset,
        },
        timeout=30,
    )

    if response.status_code != 200:

        return f"""
        <h1>Erro na busca</h1>

        <p>
            Status da API:
            <strong>{response.status_code}</strong>
        </p>

        <pre>{response.text}</pre>

        <a href="/">
            ← Voltar
        </a>
        """, response.status_code

    data = response.json()

    produtos = data.get("results", [])

    total = data.get(
        "paging",
        {}
    ).get(
        "total",
        0
    )

    # ========================================================
    # HTML
    # ========================================================

    html = f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>Busca - {termo}</title>

        <style>

            body {{
                font-family: Arial, sans-serif;
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
                box-shadow: 0 2px 8px rgba(0,0,0,.08);
            }}

            .produto img {{
                width: 180px;
                height: 180px;
                object-fit: contain;
                display: block;
                margin-bottom: 10px;
            }}

            .preco {{
                font-size: 24px;
                font-weight: bold;
                color: #008000;
            }}

            .vendidos {{
                color: #555;
                margin-top: 5px;
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

            .paginas {{
                display: flex;
                justify-content: space-between;
                margin: 20px 0;
            }}

            .paginas a {{
                background: #3483fa;
                color: white;
                padding: 12px 18px;
                border-radius: 8px;
                text-decoration: none;
            }}

        </style>

    </head>

    <body>

    <div class="container">

    <div class="top">

        <h1>🔎 {termo}</h1>

        <p>
            Produtos encontrados:
            <strong>{total}</strong>
        </p>

        <p>
            Mostrando:
            <strong>{offset + 1}</strong>
            até
            <strong>
                {min(offset + len(produtos), total)}
            </strong>
        </p>

        <a href="/">
            ← Nova pesquisa
        </a>

    </div>
    """

    if not produtos:

        html += """
        <div class="produto">

            <h2>
                Nenhum produto encontrado.
            </h2>

        </div>
        """

    # ========================================================
    # PRODUTOS
    # ========================================================

    for produto in produtos:

        produto_id = produto.get("id")

        titulo = produto.get(
            "name",
            "Produto sem nome"
        )

        imagens = produto.get(
            "pictures",
            []
        )

        imagem = ""

        if imagens:

            imagem = imagens[0].get(
                "url",
                ""
            )

        # ----------------------------------------------------
        # TENTA PEGAR ANÚNCIOS RELACIONADOS
        # ----------------------------------------------------

        preco = None
        vendidos = None
        link = None

        try:

            related_response = requests.get(
                f"https://api.mercadolibre.com/products/{produto_id}/items",
                headers={
                    "Authorization":
                    f"Bearer {access_token}"
                },
                params={
                    "site_id": "MLB"
                },
                timeout=15,
            )

            if related_response.status_code == 200:

                related_data = (
                    related_response.json()
                )

                items = related_data.get(
                    "results",
                    []
                )

                if items:

                    item = items[0]

                    item_id = item.get(
                        "item_id"
                    )

                    if item_id:

                        item_response = requests.get(
                            f"https://api.mercadolibre.com/items/{item_id}",
                            headers={
                                "Authorization":
                                f"Bearer {access_token}"
                            },
                            timeout=15,
                        )

                        if item_response.status_code == 200:

                            item_data = (
                                item_response.json()
                            )

                            preco = item_data.get(
                                "price"
                            )

                            vendidos = item_data.get(
                                "sold_quantity"
                            )

                            link = item_data.get(
                                "permalink"
                            )

        except Exception:
            pass

        if preco is None:
            preco_texto = "Preço indisponível"
        else:
            preco_texto = (
                f"R$ {float(preco):,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

        if vendidos is None:
            vendidos_texto = ""
        else:
            vendidos_texto = (
                f"🔥 {vendidos} vendidos"
            )

        if not link:
            link = (
                f"https://www.mercadolivre.com.br/"
                f"search?q={produto_id}"
            )

        html += f"""

        <div class="produto">

            <img
                src="{imagem}"
                alt="{titulo}"
            >

            <h2>
                {titulo}
            </h2>

            <div class="preco">
                {preco_texto}
            </div>

            <div class="vendidos">
                {vendidos_texto}
            </div>

            <a
                class="botao"
                href="{link}"
                target="_blank"
            >
                🛒 Ver anúncio
            </a>

        </div>

        """

    # ========================================================
    # PAGINAÇÃO
    # ========================================================

    html += """
    <div class="paginas">
    """

    if offset > 0:

        anterior = max(
            0,
            offset - limit
        )

        html += f"""
        <a href="/buscar?q={termo}&offset={anterior}">
            ← Anterior
        </a>
        """

    else:

        html += "<span></span>"

    if offset + limit < total:

        proximo = offset + limit

        html += f"""
        <a href="/buscar?q={termo}&offset={proximo}">
            Próximos →
        </a>
        """

    html += """
    </div>

    </div>

    </body>

    </html>
    """

    return html


# ============================================================
# TESTE DE CONFIGURAÇÃO
# ============================================================

@app.route("/teste-config")
def teste_config():

    return f"""
    <h1>🧪 Teste das configurações</h1>

    <p>
        CLIENT_ID:
        {"OK" if CLIENT_ID else "FALTANDO"}
    </p>

    <p>
        CLIENT_SECRET:
        {"OK" if CLIENT_SECRET else "FALTANDO"}
    </p>

    <p>
        REDIRECT_URI:
        {REDIRECT_URI if REDIRECT_URI else "FALTANDO"}
    </p>

    <p>
        SECRET_KEY:
        {"OK" if SECRET_KEY else "FALTANDO"}
    </p>

    <hr>

    <a href="/">
        ← Voltar
    </a>
    """


# ============================================================
# INICIAR
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
