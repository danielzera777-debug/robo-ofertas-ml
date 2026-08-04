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
# FORMATAÇÃO DE PREÇO
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

        return str(valor)


# ============================================================
# PÁGINA INICIAL
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

        saved_state = session.get("state")

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
            <h2>Erro: code_verifier não encontrado.</h2>

            <a href="/">
                Voltar
            </a>
            """, 400


        # ====================================================
        # TROCA CODE POR ACCESS TOKEN
        # ====================================================

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
{response.text}
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
            <h2>Access Token não recebido.</h2>

            <a href="/">
                Voltar
            </a>
            """, 400


        # ====================================================
        # LIMPA PKCE PARA NÃO REUTILIZAR O CODE
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

        user_response = requests.get(

            "https://api.mercadolibre.com/users/me",

            headers={
                "Authorization":
                    f"Bearer {access_token}"
            },

            timeout=30,
        )


        if user_response.status_code != 200:

            return f"""
            <h1>Erro ao consultar conta</h1>

            <pre>
{user_response.text}
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


        # Guarda token
        session["access_token"] = access_token

        session["user_id"] = user_id


        # ====================================================
        # TELA PRINCIPAL
        # ====================================================

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
                    font-family: Arial, sans-serif;
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
                    box-shadow:
                        0 2px 10px
                        rgba(0,0,0,.08);
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
                🔎 Buscar anúncios atuais
            </h2>

            <form
                action="/buscar"
                method="get"
            >

                <input
                    type="text"
                    name="q"
                    placeholder="Ex: celular, relógio, tênis..."
                    required
                >

                <button type="submit">
                    🔎 Buscar produtos atuais
                </button>

            </form>

        </div>

        </body>

        </html>
        """


    # ========================================================
    # CRIA PKCE
    # ========================================================

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
# BUSCA DE ANÚNCIOS ATUAIS
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
            Digite um produto para pesquisar.
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


    # ========================================================
    # PAGINAÇÃO
    # ========================================================

    try:

        offset = int(
            request.args.get(
                "offset",
                0
            )
        )

    except:

        offset = 0


    limit = 50


    # ========================================================
    # BUSCA DIRETA DE ANÚNCIOS
    # ========================================================

    response = requests.get(

        "https://api.mercadolibre.com/"
        "sites/MLB/search",

        headers={

            "Authorization":
                f"Bearer {access_token}"
        },

        params={

            "q":
                termo,

            "limit":
                limit,

            "offset":
                offset,

            # Somente anúncios ativos
            "status":
                "active",
        },

        timeout=30,
    )


    if response.status_code != 200:

        return f"""
        <h1>
            Erro na busca
        </h1>

        <p>
            Status da API:
            <strong>
                {response.status_code}
            </strong>
        </p>

        <pre>
{response.text}
        </pre>

        <a href="/">
            ← Voltar
        </a>

        """, response.status_code


    data = response.json()


    produtos = data.get(
        "results",
        []
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

    html = f"""

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
            Busca - {termo}
        </title>


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
            }}


            .preco {{
                font-size: 25px;
                font-weight: bold;
                color: #008000;
                margin: 8px 0;
            }}


            .vendidos {{
                color: #555;
                margin: 5px 0;
            }}


            .categoria {{
                color: #777;
                margin: 5px 0;
            }}


            .local {{
                color: #777;
                margin: 5px 0;
            }}


            .atualizado {{
                color: #777;
                font-size: 13px;
                margin-top: 8px;
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

        </style>

    </head>


    <body>

    <div class="container">

    <div class="top">

        <h1>
            🔎 {termo}
        </h1>

        <p>
            <strong>
                Anúncios atuais encontrados:
            </strong>

            {total}
        </p>

        <p>
            Mostrando:

            <strong>
                {offset + 1}
            </strong>

            até

            <strong>
                {min(
                    offset + len(produtos),
                    total
                )}
            </strong>
        </p>

        <p>
            🟢 Resultados de anúncios ativos
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
                Nenhum anúncio encontrado.
            </h2>

        </div>

        """


    # ========================================================
    # ITENS
    # ========================================================

    for produto in produtos:

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


        vendidos = produto.get(
            "sold_quantity",
            0
        )


        link = produto.get(
            "permalink",
            "#"
        )


        imagem = produto.get(
            "thumbnail",
            ""
        )


        categoria_id = produto.get(
            "category_id",
            "Não informada"
        )


        cidade = produto.get(
            "address",
            {}
        ).get(
            "city_name",
            ""
        )


        estado = produto.get(
            "address",
            {}
        ).get(
            "state_name",
            ""
        )


        localizacao = (
            f"{cidade} - {estado}"
            if cidade
            else "Localização não informada"
        )


        condicao = produto.get(
            "condition",
            ""
        )


        preco_texto = formatar_preco(
            preco
        )


        html += f"""

        <div class="produto">

            <img
                src="{imagem}"
                alt="{titulo}"
                loading="lazy"
            >


            <h2>
                {titulo}
            </h2>


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


            <div class="categoria">

                📂 Categoria:
                {categoria_id}

            </div>


            <div class="local">

                📍
                {localizacao}

            </div>


            <div>

                🏷️

                {condicao}

            </div>


            <div class="atualizado">

                ID do anúncio:
                {item_id}

            </div>


            <a
                class="botao"
                href="{link}"
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

    html += """

    <div class="paginas">

    """


    if offset > 0:

        anterior = max(
            0,
            offset - limit
        )


        html += f"""

        <a
            href="/buscar?q={termo}&offset={anterior}"
        >
            ← Anterior
        </a>

        """

    else:

        html += "<span></span>"


    if offset + limit < total:

        proximo = offset + limit


        html += f"""

        <a
            href="/buscar?q={termo}&offset={proximo}"
        >
            Próximos 50 →
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
            {REDIRECT_URI if REDIRECT_URI else "FALTANDO"}
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
