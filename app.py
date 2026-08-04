import os
import secrets
import base64
import hashlib

import requests

from urllib.parse import urlencode

from flask import (
    Flask,
    request,
    session
)


app = Flask(__name__)

# =========================================================
# CONFIGURAÇÕES
# =========================================================

CLIENT_ID = os.environ.get("ML_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET")

REDIRECT_URI = os.environ.get(
    "ML_REDIRECT_URI",
    "https://robo-ofertas-ml.onrender.com/"
)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "troque-esta-chave-por-uma-chave-segura"
)


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

@app.route("/")
def home():

    code = request.args.get("code")
    state = request.args.get("state")

    # =====================================================
    # RETORNO DO MERCADO LIVRE
    # =====================================================

    if code:

        # Verifica o state
        if state != session.get("state"):

            return """
            <h1>❌ Erro</h1>
            <p>State inválido.</p>
            <a href="/">Voltar</a>
            """, 400

        # Recupera o code_verifier
        code_verifier = session.get("code_verifier")

        if not code_verifier:

            return """
            <h1>❌ Erro</h1>
            <p>Code verifier não encontrado.</p>
            <a href="/">Voltar</a>
            """, 400

        # =================================================
        # TROCA O CODE PELO ACCESS TOKEN
        # =================================================

        response = requests.post(

            "https://api.mercadolibre.com/oauth/token",

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

        if response.status_code != 200:

            return f"""
            <h1>❌ Erro ao obter Access Token</h1>

            <p>
                Status:
                {response.status_code}
            </p>

            <pre>
{response.text}
            </pre>

            <a href="/">Voltar</a>
            """, 400

        token_data = response.json()

        access_token = token_data.get(
            "access_token"
        )

        refresh_token = token_data.get(
            "refresh_token"
        )

        if not access_token:

            return """
            <h1>❌ Access Token não recebido</h1>
            <a href="/">Voltar</a>
            """, 400

        # =================================================
        # TESTA O ACCESS TOKEN
        # =================================================

        user_response = requests.get(

            "https://api.mercadolibre.com/users/me",

            headers={

                "Authorization":
                    f"Bearer {access_token}"

            },

            timeout=30
        )

        if user_response.status_code != 200:

            return f"""
            <h1>❌ Erro ao consultar conta</h1>

            <p>
                Status:
                {user_response.status_code}
            </p>

            <pre>
{user_response.text}
            </pre>

            <a href="/">Voltar</a>
            """, 400

        user_data = user_response.json()

        nickname = user_data.get(
            "nickname",
            "Usuário"
        )

        user_id = user_data.get(
            "id",
            "Não informado"
        )

        # =================================================
        # GUARDA OS TOKENS NA SESSÃO
        # =================================================

        session["access_token"] = access_token

        if refresh_token:

            session["refresh_token"] = refresh_token

        session["user_id"] = user_id

        # Remove dados temporários do OAuth

        session.pop(
            "code_verifier",
            None
        )

        session.pop(
            "state",
            None
        )

        # =================================================
        # PÁGINA APÓS CONEXÃO
        # =================================================

        return f"""

        <!DOCTYPE html>

        <html>

        <head>

            <meta charset="UTF-8">

            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >

            <title>
                Robô Ofertas ML
            </title>

            <style>

                body {{

                    font-family:
                        Arial,
                        sans-serif;

                    background:
                        #f5f5f5;

                    padding:
                        20px;

                }}

                .box {{

                    max-width:
                        600px;

                    margin:
                        auto;

                    background:
                        white;

                    padding:
                        25px;

                    border-radius:
                        12px;

                    box-shadow:
                        0 2px 10px
                        rgba(0,0,0,0.1);

                }}

                input {{

                    width:
                        100%;

                    box-sizing:
                        border-box;

                    padding:
                        12px;

                    font-size:
                        16px;

                    margin-top:
                        10px;

                }}

                button {{

                    width:
                        100%;

                    padding:
                        12px;

                    margin-top:
                        10px;

                    font-size:
                        16px;

                    background:
                        #3483fa;

                    color:
                        white;

                    border:
                        none;

                    border-radius:
                        8px;

                }}

            </style>

        </head>

        <body>

            <div class="box">

                <h1>
                    ✅ Mercado Livre conectado!
                </h1>

                <p>
                    Usuário:
                    <strong>
                        {nickname}
                    </strong>
                </p>

                <p>
                    ID:
                    <strong>
                        {user_id}
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

                    <input
                        type="text"
                        name="q"
                        placeholder="Digite um produto"
                        required
                    >

                    <button
                        type="submit"
                    >
                        Buscar
                    </button>

                </form>

            </div>

        </body>

        </html>

        """

    # =====================================================
    # VERIFICA CONFIGURAÇÕES
    # =====================================================

    if not CLIENT_ID:

        return """
        <h1>❌ Erro de configuração</h1>

        <p>
            ML_CLIENT_ID não configurado no Render.
        </p>
        """, 500

    if not CLIENT_SECRET:

        return """
        <h1>❌ Erro de configuração</h1>

        <p>
            ML_CLIENT_SECRET não configurado no Render.
        </p>
        """, 500

    # =====================================================
    # PKCE
    # =====================================================

    code_verifier = secrets.token_urlsafe(64)

    code_challenge = (

        base64.urlsafe_b64encode(

            hashlib.sha256(

                code_verifier.encode()

            ).digest()

        )

        .rstrip(b"=")

        .decode()

    )

    state = secrets.token_urlsafe(32)

    # Guarda na sessão

    session["code_verifier"] = (
        code_verifier
    )

    session["state"] = state

    # =====================================================
    # URL DE AUTORIZAÇÃO
    # =====================================================

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

        "https://auth.mercadolivre.com.br/authorization?"

        + urlencode(params)

    )

    # =====================================================
    # TELA DE LOGIN
    # =====================================================

    return f"""

    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>
            Robô Ofertas ML
        </title>

        <style>

            body {{

                font-family:
                    Arial,
                    sans-serif;

                background:
                    #f5f5f5;

                padding:
                    20px;

                text-align:
                    center;

            }}

            .box {{

                max-width:
                    500px;

                margin:
                    50px auto;

                background:
                    white;

                padding:
                    30px;

                border-radius:
                    12px;

                box-shadow:
                    0 2px 10px
                    rgba(0,0,0,0.1);

            }}

            .btn {{

                display:
                    inline-block;

                padding:
                    15px 25px;

                background:
                    #3483fa;

                color:
                    white;

                text-decoration:
                    none;

                border-radius:
                    8px;

                font-size:
                    17px;

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
                para começar.
            </p>

            <br>

            <a
                href="{auth_url}"
                class="btn"
            >
                Conectar Mercado Livre
            </a>

        </div>

    </body>

    </html>

    """


# =========================================================
# BUSCAR PRODUTOS
# =========================================================

@app.route("/buscar")
def buscar():

    termo = request.args.get(
        "q",
        ""
    ).strip()

    if not termo:

        return """

        <h1>
            ❌ Digite um produto
        </h1>

        <a href="/">
            ← Voltar
        </a>

        """, 400

    # =====================================================
    # RECUPERA ACCESS TOKEN
    # =====================================================

    access_token = session.get(
        "access_token"
    )

    if not access_token:

        return """

        <h1>
            ❌ Mercado Livre não conectado
        </h1>

        <p>
            Conecte sua conta primeiro.
        </p>

        <a href="/">
            Conectar Mercado Livre
        </a>

        """, 401

    # =====================================================
    # NOVA API DE PRODUTOS
    # =====================================================

    response = requests.get(

        "https://api.mercadolibre.com/products/search",

        headers={

            "Authorization":
                f"Bearer {access_token}"

        },

        params={

            "status":
                "active",

            "site_id":
                "MLB",

            "q":
                termo,

            "limit":
                10

        },

        timeout=30

    )

    # =====================================================
    # TRATA ERROS
    # =====================================================

    if response.status_code != 200:

        return f"""

        <!DOCTYPE html>

        <html>

        <head>

            <meta charset="UTF-8">

            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >

            <title>
                Erro na busca
            </title>

        </head>

        <body>

            <h1>
                ❌ Erro na busca
            </h1>

            <p>
                <strong>
                    Status da API:
                </strong>

                {response.status_code}
            </p>

            <pre>
{response.text}
            </pre>

            <br>

            <a href="/">
                ← Voltar
            </a>

        </body>

        </html>

        """, response.status_code

    # =====================================================
    # CONVERTE RESPOSTA
    # =====================================================

    data = response.json()

    produtos = data.get(
        "results",
        []
    )

    total = data.get(
        "paging",
        {}
    ).get(
        "total",
        0
    )

    # =====================================================
    # HTML DOS RESULTADOS
    # =====================================================

    html = f"""

    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>
            Busca - {termo}
        </title>

        <style>

            body {{

                font-family:
                    Arial,
                    sans-serif;

                background:
                    #f5f5f5;

                margin:
                    0;

                padding:
                    20px;

            }}

            .container {{

                max-width:
                    800px;

                margin:
                    auto;

            }}

            .produto {{

                background:
                    white;

                border-radius:
                    12px;

                padding:
                    15px;

                margin:
                    15px 0;

                box-shadow:
                    0 2px 8px
                    rgba(0,0,0,0.1);

            }}

            .produto img {{

                width:
                    180px;

                height:
                    180px;

                object-fit:
                    contain;

                display:
                    block;

                margin-bottom:
                    10px;

            }}

            .produto h3 {{

                margin:
                    10px 0;

                color:
                    #333;

            }}

            .id {{

                color:
                    #777;

                font-size:
                    13px;

            }}

            .status {{

                color:
                    #008000;

                font-weight:
                    bold;

            }}

            .voltar {{

                display:
                    inline-block;

                margin:
                    10px 0;

                text-decoration:
                    none;

            }}

        </style>

    </head>

    <body>

        <div class="container">

            <h1>
                🔎 Busca de produtos
            </h1>

            <p>
                <strong>
                    Termo:
                </strong>

                {termo}
            </p>

            <p>
                <strong>
                    Total encontrado:
                </strong>

                {total}
            </p>

            <a
                href="/"
                class="voltar"
            >
                ← Voltar
            </a>

            <hr>

    """

    # =====================================================
    # NENHUM PRODUTO
    # =====================================================

    if not produtos:

        html += """

        <h2>
            Nenhum produto encontrado.
        </h2>

        """

    # =====================================================
    # PRODUTOS
    # =====================================================

    for produto in produtos:

        produto_id = produto.get(
            "id",
            ""
        )

        nome = produto.get(
            "name",
            "Produto sem nome"
        )

        status = produto.get(
            "status",
            ""
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

        html += f"""

        <div class="produto">

            <img
                src="{imagem}"
                alt="{nome}"
            >

            <h3>
                {nome}
            </h3>

            <p class="id">
                ID:
                {produto_id}
            </p>

            <p class="status">
                Status:
                {status}
            </p>

        </div>

        """

    html += """

        </div>

    </body>

    </html>

    """

    return html


# =========================================================
# EXECUÇÃO
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(

        host="0.0.0.0",

        port=port

    )
