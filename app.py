import os
import secrets
import base64
import hashlib
import requests

from urllib.parse import urlencode

from flask import (
    Flask,
    request,
    session,
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "troque-esta-chave"
)

CLIENT_ID = os.environ.get(
    "ML_CLIENT_ID"
)

CLIENT_SECRET = os.environ.get(
    "ML_CLIENT_SECRET"
)

REDIRECT_URI = os.environ.get(
    "ML_REDIRECT_URI"
)


# ============================================================
# PÁGINA INICIAL / LOGIN MERCADO LIVRE
# ============================================================

@app.route("/")
def home():

    code = request.args.get("code")
    state = request.args.get("state")

    # --------------------------------------------------------
    # VERIFICA CONFIGURAÇÃO
    # --------------------------------------------------------

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

        # ----------------------------------------------------
        # VALIDA STATE
        # ----------------------------------------------------

        saved_state = session.get("state")

        if state != saved_state:

            return """
            <h1>❌ Erro</h1>
            <p>State inválido.</p>
            <a href="/">Voltar</a>
            """, 400


        # ----------------------------------------------------
        # PEGA CODE VERIFIER
        # ----------------------------------------------------

        code_verifier = session.get(
            "code_verifier"
        )

        if not code_verifier:

            return """
            <h1>❌ Erro</h1>
            <p>Code verifier não encontrado.</p>
            <a href="/">Voltar</a>
            """, 400


        # ====================================================
        # TROCA CODE POR ACCESS TOKEN
        # ====================================================

        token_response = requests.post(

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

            timeout=30
        )


        if token_response.status_code != 200:

            return f"""
            <h1>❌ Erro ao obter Access Token</h1>

            <p>
                Status:
                {token_response.status_code}
            </p>

            <pre>
{token_response.text}
            </pre>

            <a href="/">Voltar</a>
            """, 400


        token_data = token_response.json()

        access_token = token_data.get(
            "access_token"
        )


        if not access_token:

            return """
            <h1>❌ Access Token não recebido</h1>
            <a href="/">Voltar</a>
            """, 400


        # ====================================================
        # CONSULTA USUÁRIO
        # ====================================================

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
            "usuário"
        )

        user_id = user_data.get(
            "id",
            "não informado"
        )


        # ----------------------------------------------------
        # SALVA TOKEN NA SESSÃO
        # ----------------------------------------------------

        session["access_token"] = access_token

        # Limpa dados temporários
        session.pop("state", None)
        session.pop("code_verifier", None)


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

                    font-family:
                        Arial,
                        sans-serif;

                    background:
                        #f5f5f5;

                    padding:
                        20px;

                    margin:
                        0;
                }}

                .container {{

                    max-width:
                        700px;

                    margin:
                        auto;
                }}

                .card {{

                    background:
                        white;

                    padding:
                        25px;

                    border-radius:
                        15px;

                    box-shadow:
                        0 2px 10px
                        rgba(0,0,0,0.08);
                }}

                input {{

                    width:
                        100%;

                    box-sizing:
                        border-box;

                    padding:
                        14px;

                    font-size:
                        17px;

                    border:
                        1px solid #ddd;

                    border-radius:
                        8px;

                    margin-bottom:
                        12px;
                }}

                button {{

                    width:
                        100%;

                    padding:
                        14px;

                    background:
                        #3483fa;

                    color:
                        white;

                    border:
                        none;

                    border-radius:
                        8px;

                    font-size:
                        17px;

                    font-weight:
                        bold;
                }}

            </style>

        </head>


        <body>

        <div class="container">

            <div class="card">

                <h1>
                    🤖 Robô Ofertas ML
                </h1>

                <h2>
                    ✅ Mercado Livre conectado
                </h2>

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

                    <button type="submit">
                        🔎 Buscar
                    </button>

                </form>

            </div>

        </div>

        </body>

        </html>

        """


    # ========================================================
    # CRIA PKCE
    # ========================================================

    code_verifier = secrets.token_urlsafe(64)


    code_challenge = (
        base64
        .urlsafe_b64encode(
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


    # ========================================================
    # URL DE AUTORIZAÇÃO
    # ========================================================

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


    # ========================================================
    # TELA DE LOGIN
    # ========================================================

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

            .card {{

                max-width:
                    500px;

                margin:
                    80px auto;

                background:
                    white;

                padding:
                    30px;

                border-radius:
                    15px;

                box-shadow:
                    0 2px 10px
                    rgba(0,0,0,0.08);
            }}

            .botao {{

                display:
                    inline-block;

                background:
                    #ffe600;

                color:
                    #333;

                padding:
                    15px 25px;

                border-radius:
                    8px;

                text-decoration:
                    none;

                font-weight:
                    bold;

                font-size:
                    17px;
            }}

        </style>

    </head>

    <body>

        <div class="card">

            <h1>
                🤖 Robô Ofertas ML
            </h1>

            <p>
                Conecte sua conta do
                Mercado Livre para continuar.
            </p>

            <br>

            <a
                class="botao"
                href="{auth_url}"
            >
                🔗 Conectar Mercado Livre
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

        <h1>
            Digite um produto.
        </h1>

        <a href="/">
            ← Voltar
        </a>

        """, 400


    # ========================================================
    # TOKEN
    # ========================================================

    access_token = session.get(
        "access_token"
    )


    if not access_token:

        return """

        <h1>
            ⚠️ Mercado Livre não conectado
        </h1>

        <p>
            Conecte sua conta novamente.
        </p>

        <a href="/">
            Conectar Mercado Livre
        </a>

        """, 401


    headers = {

        "Authorization":
            f"Bearer {access_token}",

        "Accept":
            "application/json"
    }


    # ========================================================
    # BUSCA NO PRODUCTS/SEARCH
    # ========================================================

    response = requests.get(

        "https://api.mercadolibre.com/products/search",

        headers=headers,

        params={

            "status":
                "active",

            "site_id":
                "MLB",

            "q":
                termo,

            "limit":
                10,

            "offset":
                0,
        },

        timeout=30
    )


    if response.status_code != 200:

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
                Erro na busca
            </title>

        </head>

        <body>

            <h1>
                ❌ Erro na busca
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

            <br>

            <a href="/">
                ← Voltar
            </a>

        </body>

        </html>

        """, response.status_code


    data = response.json()

    produtos = data.get(
        "results",
        []
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

                font-family:
                    Arial,
                    sans-serif;

                background:
                    #f5f5f5;

                margin:
                    0;

                padding:
                    15px;
            }}

            .container {{

                max-width:
                    900px;

                margin:
                    auto;
            }}

            .topo {{

                background:
                    white;

                padding:
                    20px;

                border-radius:
                    12px;

                margin-bottom:
                    20px;
            }}

            .produto {{

                background:
                    white;

                padding:
                    18px;

                margin-bottom:
                    18px;

                border-radius:
                    12px;

                box-shadow:
                    0 2px 8px
                    rgba(0,0,0,0.08);
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
                    12px;
            }}

            .titulo {{

                font-size:
                    18px;

                font-weight:
                    bold;

                margin-bottom:
                    10px;
            }}

            .preco {{

                font-size:
                    26px;

                font-weight:
                    bold;

                color:
                    #00a650;

                margin:
                    10px 0;
            }}

            .info {{

                color:
                    #555;

                margin:
                    6px 0;
            }}

            .botao {{

                display:
                    inline-block;

                background:
                    #3483fa;

                color:
                    white;

                text-decoration:
                    none;

                padding:
                    12px 18px;

                border-radius:
                    8px;

                margin-top:
                    10px;

                font-weight:
                    bold;
            }}

            .aviso {{

                color:
                    #888;

                margin-top:
                    10px;
            }}

        </style>

    </head>

    <body>

    <div class="container">

        <div class="topo">

            <h1>
                🔎 Busca de produtos
            </h1>

            <p>
                Pesquisa:
                <strong>
                    {termo}
                </strong>
            </p>

            <p>
                Resultados:
                <strong>
                    {len(produtos)}
                </strong>
            </p>

            <a href="/">
                ← Voltar
            </a>

        </div>

    """


    # ========================================================
    # NENHUM RESULTADO
    # ========================================================

    if not produtos:

        html += """

        <div class="produto">

            <h2>
                Nenhum produto encontrado.
            </h2>

        </div>

        """


    # ========================================================
    # PROCESSA PRODUTOS
    # ========================================================

    for produto in produtos:

        product_id = produto.get(
            "id"
        )


        nome = produto.get(
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
        # VARIÁVEIS ATUALIZADAS
        # ----------------------------------------------------

        item_id = None

        seller_id = None

        preco = None

        preco_regular = None

        quantidade = None

        vendidos = None

        permalink = None

        titulo_atual = nome


        # ====================================================
        # PRODUTO DETALHADO
        # ====================================================

        try:

            detalhe_response = requests.get(

                f"https://api.mercadolibre.com/"
                f"products/{product_id}",

                headers=headers,

                timeout=30
            )


            if detalhe_response.status_code == 200:

                detalhe = (
                    detalhe_response.json()
                )


                buy_box = detalhe.get(
                    "buy_box_winner"
                )


                if buy_box:

                    item_id = buy_box.get(
                        "item_id"
                    )

                    seller_id = buy_box.get(
                        "seller_id"
                    )


        except Exception:

            pass


        # ====================================================
        # ITEM / ANÚNCIO ATUAL
        # ====================================================

        if item_id:

            try:

                item_response = requests.get(

                    f"https://api.mercadolibre.com/"
                    f"items/{item_id}",

                    headers=headers,

                    timeout=30
                )


                if item_response.status_code == 200:

                    item = (
                        item_response.json()
                    )


                    titulo_atual = item.get(
                        "title",
                        nome
                    )


                    seller_id = item.get(
                        "seller_id",
                        seller_id
                    )


                    quantidade = item.get(
                        "available_quantity"
                    )


                    vendidos = item.get(
                        "sold_quantity"
                    )


                    permalink = item.get(
                        "permalink"
                    )


                    item_price = item.get(
                        "price"
                    )


                    if item_price is not None:

                        preco = item_price


                    # ----------------------------------------
                    # FOTO ATUAL DO ANÚNCIO
                    # ----------------------------------------

                    fotos = item.get(
                        "pictures",
                        []
                    )


                    if fotos:

                        primeira_foto = (
                            fotos[0]
                        )


                        imagem = (
                            primeira_foto.get(
                                "secure_url"
                            )
                            or
                            primeira_foto.get(
                                "url",
                                imagem
                            )
                        )


            except Exception:

                pass


        # ====================================================
        # SALE PRICE
        # ====================================================

        if item_id:

            try:

                sale_response = requests.get(

                    f"https://api.mercadolibre.com/"
                    f"items/{item_id}/sale_price",

                    headers=headers,

                    params={
                        "quantity": 1
                    },

                    timeout=30
                )


                if sale_response.status_code == 200:

                    sale_data = (
                        sale_response.json()
                    )


                    sale_amount = (
                        sale_data.get(
                            "amount"
                        )
                    )


                    regular_amount = (
                        sale_data.get(
                            "regular_amount"
                        )
                    )


                    if sale_amount is not None:

                        preco = sale_amount


                    if regular_amount is not None:

                        preco_regular = (
                            regular_amount
                        )


            except Exception:

                pass


        # ====================================================
        # FALLBACK /PRICES
        # ====================================================

        if item_id and preco is None:

            try:

                prices_response = requests.get(

                    f"https://api.mercadolibre.com/"
                    f"items/{item_id}/prices",

                    headers=headers,

                    timeout=30
                )


                if prices_response.status_code == 200:

                    prices_data = (
                        prices_response.json()
                    )


                    prices = prices_data.get(
                        "prices",
                        []
                    )


                    # ----------------------------------------
                    # PRIMEIRO PROMOÇÃO
                    # ----------------------------------------

                    for price_data in prices:

                        if price_data.get(
                            "type"
                        ) == "promotion":

                            amount = (
                                price_data.get(
                                    "amount"
                                )
                            )


                            if amount is not None:

                                preco = amount


                                preco_regular = (
                                    price_data.get(
                                        "regular_amount"
                                    )
                                )


                                break


                    # ----------------------------------------
                    # DEPOIS STANDARD
                    # ----------------------------------------

                    if preco is None:

                        for price_data in prices:

                            if price_data.get(
                                "type"
                            ) == "standard":

                                amount = (
                                    price_data.get(
                                        "amount"
                                    )
                                )


                                if amount is not None:

                                    preco = amount

                                    break


            except Exception:

                pass


        # ====================================================
        # FORMATA PREÇO
        # ====================================================

        if preco is not None:

            try:

                preco_formatado = (
                    f"R$ {float(preco):,.2f}"
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )

            except Exception:

                preco_formatado = str(
                    preco
                )

        else:

            preco_formatado = (
                "Preço não disponível"
            )


        # ====================================================
        # HTML DO PRODUTO
        # ====================================================

        html += """

        <div class="produto">

        """


        if imagem:

            html += f"""

                <img
                    src="{imagem}"
                    alt="{titulo_atual}"
                >

            """


        html += f"""

            <div class="titulo">

                {titulo_atual}

            </div>

            <div class="preco">

                {preco_formatado}

            </div>

        """


        # ====================================================
        # PREÇO ORIGINAL
        # ====================================================

        if preco_regular:

            try:

                original = (
                    f"R$ {float(preco_regular):,.2f}"
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )


                html += f"""

                <div class="info">

                    Preço normal:
                    <s>{original}</s>

                </div>

                """


            except Exception:

                pass


        # ====================================================
        # INFORMAÇÕES
        # ====================================================

        html += f"""

            <div class="info">

                🆔 Produto:
                {product_id}

            </div>

        """


        if item_id:

            html += f"""

            <div class="info">

                🛒 Anúncio:
                {item_id}

            </div>

            """


        if seller_id:

            html += f"""

            <div class="info">

                👤 Vendedor:
                {seller_id}

            </div>

            """


        if quantidade is not None:

            html += f"""

            <div class="info">

                📦 Disponível:
                {quantidade}

            </div>

            """


        if vendidos is not None:

            html += f"""

            <div class="info">

                🔥 Vendidos:
                {vendidos}

            </div>

            """


        # ====================================================
        # BOTÃO ANÚNCIO
        # ====================================================

        if permalink:

            html += f"""

            <a
                class="botao"
                href="{permalink}"
                target="_blank"
            >

                🛒 Ver anúncio

            </a>

            """


        elif item_id:

            link = (
                "https://www.mercadolivre.com.br/"
                + item_id
            )


            html += f"""

            <a
                class="botao"
                href="{link}"
                target="_blank"
            >

                🛒 Ver anúncio

            </a>

            """


        else:

            html += """

            <p class="aviso">

                ⚠️ Produto de catálogo
                sem anúncio vencedor disponível.

            </p>

            """


        html += """

        </div>

        """


    # ========================================================
    # FINAL HTML
    # ========================================================

    html += """

    </div>

    </body>

    </html>

    """


    return html


# ============================================================
# EXECUÇÃO
# ============================================================

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
