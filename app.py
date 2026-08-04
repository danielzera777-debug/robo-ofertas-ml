from flask import Flask, request, session
import requests
import secrets
import hashlib
import base64
from urllib.parse import urlencode
import os
import html

app = Flask(__name__)

# ==================================================
# CONFIGURAÇÕES
# ==================================================

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "chave-temporaria"
)

CLIENT_ID = os.environ.get("ML_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET")

# URL cadastrada no Mercado Livre
REDIRECT_URI = "https://robo-ofertas-ml.onrender.com/"


# ==================================================
# PÁGINA INICIAL
# ==================================================

@app.route("/")
def home():

    code = request.args.get("code")
    state = request.args.get("state")

    if not CLIENT_ID:
        return "ML_CLIENT_ID não configurado no Render.", 500

    if not CLIENT_SECRET:
        return "ML_CLIENT_SECRET não configurado no Render.", 500


    # ==================================================
    # RETORNO DO MERCADO LIVRE
    # ==================================================

    if code:

        if state != session.get("state"):
            return "Erro: state inválido.", 400

        code_verifier = session.get("code_verifier")

        if not code_verifier:
            return "Erro: code_verifier não encontrado.", 400


        # ==================================================
        # TROCA CODE POR ACCESS TOKEN
        # ==================================================

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
            <h1>❌ Erro ao obter token</h1>

            <pre>{html.escape(response.text)}</pre>

            <a href="/">
                ← Voltar
            </a>
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
            <h1>❌ Access Token não recebido.</h1>
            """, 400


        # ==================================================
        # CONSULTA /users/me
        # ==================================================

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
            <h1>❌ Erro ao consultar conta</h1>

            <p>
                Status:
                {user_response.status_code}
            </p>

            <pre>
            {html.escape(user_response.text)}
            </pre>

            <a href="/">
                ← Voltar
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


        # ==================================================
        # SALVAR DADOS NA SESSÃO
        # ==================================================

        session["access_token"] = access_token

        session["user_id"] = user_id

        session["nickname"] = nickname


        if refresh_token:

            session["refresh_token"] = refresh_token


        # ==================================================
        # TELA PRINCIPAL
        # ==================================================

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

        <body>

            <h1>
                ✅ Mercado Livre conectado!
            </h1>


            <p>
                Usuário:
                <strong>
                    {html.escape(str(nickname))}
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

                    style="
                        padding:10px;
                        width:250px;
                        font-size:16px;
                    "
                >


                <button
                    type="submit"

                    style="
                        padding:10px 20px;
                        font-size:16px;
                    "
                >
                    Buscar
                </button>

            </form>


            <hr>


            <h2>
                🧪 Testes
            </h2>


            <p>
                <a href="/teste">
                    Testar conexão /users/me
                </a>
            </p>


            <p>
                <a href="/teste-busca">
                    Testar busca de produtos
                </a>
            </p>

        </body>

        </html>
        """


    # ==================================================
    # INICIAR OAUTH + PKCE
    # ==================================================

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


    session["code_verifier"] = code_verifier

    session["state"] = state


    params = {

        "response_type": "code",

        "client_id": CLIENT_ID,

        "redirect_uri": REDIRECT_URI,

        "state": state,

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

    <body>

        <h1>
            🤖 Robô Ofertas ML
        </h1>


        <p>
            Conecte sua conta do Mercado Livre:
        </p>


        <a href="{auth_url}">

            <button
                style="
                    padding:15px 25px;
                    font-size:18px;
                "
            >
                Conectar Mercado Livre
            </button>

        </a>

    </body>

    </html>
    """


# ==================================================
# TESTE /users/me
# ==================================================

@app.route("/teste")
def teste():

    access_token = session.get(
        "access_token"
    )


    if not access_token:

        return """
        <h1>
            ❌ Token não encontrado
        </h1>

        <p>
            Primeiro conecte sua conta.
        </p>

        <a href="/">
            ← Voltar
        </a>
        """, 401


    response = requests.get(

        "https://api.mercadolibre.com/users/me",

        headers={
            "Authorization":
            f"Bearer {access_token}"
        },

        timeout=30,
    )


    print("==============================")
    print("TESTE /users/me")
    print("STATUS:", response.status_code)
    print("RESPOSTA:", response.text)
    print("==============================")


    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <title>
            Teste API
        </title>

    </head>

    <body>

        <h1>
            🧪 Teste /users/me
        </h1>


        <p>
            Status da API:
            <strong>
                {response.status_code}
            </strong>
        </p>


        <pre
            style="
                white-space:pre-wrap;
                word-wrap:break-word;
            "
        >
{html.escape(response.text)}
        </pre>


        <a href="/">
            ← Voltar
        </a>

    </body>

    </html>
    """, response.status_code


# ==================================================
# TESTE NOVO /products/search
# ==================================================

@app.route("/teste-busca")
def teste_busca():

    termo = request.args.get(
        "q",
        "Celular"
    ).strip()


    if not termo:

        termo = "Celular"


    access_token = session.get(
        "access_token"
    )


    if not access_token:

        return """
        <h1>
            ❌ Token não encontrado
        </h1>

        <p>
            Primeiro conecte sua conta.
        </p>

        <a href="/">
            ← Voltar
        </a>
        """, 401


    # ==================================================
    # NOVO ENDPOINT
    # ==================================================

    response = requests.get(

        "https://api.mercadolibre.com/products/search",

        headers={
            "Authorization":
            f"Bearer {access_token}"
        },

        params={

            "status": "active",

            "site_id": "MLB",

            "q": termo,

            "limit": 10,

        },

        timeout=30,
    )


    print("==============================")
    print("TESTE /products/search")
    print("TERMO:", termo)
    print("STATUS:", response.status_code)
    print("RESPOSTA:", response.text)
    print("==============================")


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
            Teste de produtos
        </title>

    </head>


    <body>

        <h1>
            🔎 Busca de produtos
        </h1>


        <p>
            Termo:
            <strong>
                {html.escape(termo)}
            </strong>
        </p>


        <p>
            Endpoint:
            <strong>
                /products/search
            </strong>
        </p>


        <p>
            Status da API:
            <strong>
                {response.status_code}
            </strong>
        </p>


        <hr>


        <h3>
            Resposta:
        </h3>


        <pre
            style="
                white-space:pre-wrap;
                word-wrap:break-word;
            "
        >
{html.escape(response.text)}
        </pre>


        <hr>


        <form
            action="/teste-busca"
            method="get"
        >

            <input
                type="text"
                name="q"
                value="{html.escape(termo)}"
                placeholder="Digite um produto"

                style="
                    padding:10px;
                    width:250px;
                    font-size:16px;
                "
            >


            <button
                type="submit"

                style="
                    padding:10px 20px;
                    font-size:16px;
                "
            >
                Pesquisar
            </button>

        </form>


        <br>


        <a href="/">
            ← Voltar
        </a>

    </body>

    </html>
    """, response.status_code


# ==================================================
# BUSCA NORMAL
# ==================================================

@app.route("/buscar")
def buscar():

    termo = request.args.get(
        "q",
        ""
    ).strip()


    if not termo:

        return """
        <h1>
            Digite um produto para pesquisar.
        </h1>

        <a href="/">
            ← Voltar
        </a>
        """, 400


    access_token = session.get(
        "access_token"
    )


    if not access_token:

        return """
        <h1>
            ❌ Conta não conectada
        </h1>

        <a href="/">
            Conectar Mercado Livre
        </a>
        """, 401


    # ==================================================
    # BUSCA NO CATÁLOGO
    # ==================================================

    response = requests.get(

        "https://api.mercadolibre.com/products/search",

        headers={
            "Authorization":
            f"Bearer {access_token}"
        },

        params={

            "status": "active",

            "site_id": "MLB",

            "q": termo,

            "limit": 10,

        },

        timeout=30,
    )


    print("==============================")
    print("BUSCA NORMAL")
    print("ENDPOINT: /products/search")
    print("TERMO:", termo)
    print("STATUS:", response.status_code)
    print("RESPOSTA:", response.text)
    print("==============================")


    if response.status_code != 200:

        return f"""
        <h1>
            ❌ Erro na busca
        </h1>

        <p>
            Status da API:
            <strong>
                {response.status_code}
            </strong>
        </p>


        <pre
            style="
                white-space:pre-wrap;
                word-wrap:break-word;
            "
        >
{html.escape(response.text)}
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


    # ==================================================
    # MONTAR PÁGINA
    # ==================================================

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
            Busca - {html.escape(termo)}
        </title>

    </head>


    <body>

        <h1>
            🔎 Resultados para:
            {html.escape(termo)}
        </h1>


        <a href="/">
            ← Voltar
        </a>


        <hr>
    """


    if not produtos:

        html_page += """
        <h2>
            Nenhum produto de catálogo encontrado.
        </h2>
        """


    for produto in produtos:

        produto_id = produto.get(
            "id",
            ""
        )


        titulo = produto.get(
            "name",
            "Sem título"
        )


        status = produto.get(
            "status",
            ""
        )


        permalink = produto.get(
            "permalink",
            ""
        )


        pictures = produto.get(
            "pictures",
            []
        )


        imagem = ""


        if pictures:

            imagem = pictures[0].get(
                "url",
                ""
            )


        buy_box = produto.get(
            "buy_box_winner"
        )


        preco = "Não informado"


        link_anuncio = permalink


        if buy_box:

            preco_valor = buy_box.get(
                "price"
            )


            moeda = buy_box.get(
                "currency_id",
                "BRL"
            )


            item_id = buy_box.get(
                "item_id"
            )


            if preco_valor is not None:

                preco = (
                    f"{moeda} "
                    f"{preco_valor}"
                )


            if item_id:

                link_anuncio = (
                    "https://www.mercadolivre.com.br/"
                    f"p/{produto_id}"
                )


        html_page += f"""

        <div
            style="
                border:1px solid #ddd;
                border-radius:12px;
                padding:15px;
                margin:15px 0;
                max-width:600px;
            "
        >


            {
                f'''
                <img
                    src="{html.escape(imagem)}"
                    style="
                        width:180px;
                        height:180px;
                        object-fit:contain;
                    "
                >
                '''
                if imagem
                else
                "<p>Sem imagem disponível.</p>"
            }


            <h3>
                {html.escape(titulo)}
            </h3>


            <p>
                <strong>
                    Produto:
                </strong>

                {html.escape(produto_id)}
            </p>


            <p>
                <strong>
                    Status:
                </strong>

                {html.escape(status)}
            </p>


            <p>
                <strong>
                    Preço:
                </strong>

                {html.escape(str(preco))}
            </p>


            {
                f'''
                <p>
                    <a
                        href="{html.escape(link_anuncio)}"
                        target="_blank"
                    >
                        Ver produto
                    </a>
                </p>
                '''
                if link_anuncio
                else
                ""
            }


        </div>

        """


    html_page += """

    </body>

    </html>

    """


    return html_page


# ==================================================
# INICIAR SERVIDOR
# ==================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=10000

    )
