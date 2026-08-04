from flask import Flask, request, session
import requests
import secrets
import hashlib
import base64
from urllib.parse import urlencode
import os
import html


app = Flask(__name__)

# ============================================================
# CONFIGURAÇÕES
# ============================================================

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "chave-temporaria-troque-no-render"
)

CLIENT_ID = os.environ.get("ML_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET")

REDIRECT_URI = os.environ.get(
    "ML_REDIRECT_URI",
    "https://robo-ofertas-ml.onrender.com/"
)


# ============================================================
# PÁGINA PRINCIPAL / AUTENTICAÇÃO
# ============================================================

@app.route("/")
def home():

    code = request.args.get("code")
    state = request.args.get("state")

    # --------------------------------------------------------
    # RETORNO DO MERCADO LIVRE
    # --------------------------------------------------------

    if code:

        # Verifica o state
        if state != session.get("state"):
            return """
            <h1>❌ Erro</h1>
            <p>State inválido.</p>
            <a href="/">Voltar</a>
            """, 400

        code_verifier = session.get("code_verifier")

        if not code_verifier:
            return """
            <h1>❌ Erro</h1>
            <p>Code verifier não encontrado.</p>
            <a href="/">Voltar</a>
            """, 400

        # ----------------------------------------------------
        # TROCA CODE POR ACCESS TOKEN
        # ----------------------------------------------------

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
            <h1>❌ Erro ao obter Access Token</h1>

            <p>
                Status:
                {response.status_code}
            </p>

            <pre>
{html.escape(response.text)}
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

        # ----------------------------------------------------
        # SALVA OS TOKENS
        # ----------------------------------------------------

        session["access_token"] = access_token

        if refresh_token:

            session["refresh_token"] = refresh_token

        # ----------------------------------------------------
        # TESTA /users/me
        # ----------------------------------------------------

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
                Status da API:
                {user_response.status_code}
            </p>

            <pre>
{html.escape(user_response.text)}
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

        # ----------------------------------------------------
        # PÁGINA DO ROBÔ
        # ----------------------------------------------------

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
                }}

                .card {{
                    background: white;
                    padding: 20px;
                    border-radius: 15px;
                    margin-bottom: 20px;
                    box-shadow:
                        0 2px 10px
                        rgba(0,0,0,0.08);
                }}

                input {{
                    width: 100%;
                    box-sizing: border-box;
                    padding: 14px;
                    font-size: 16px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    margin-bottom: 10px;
                }}

                button {{
                    padding: 12px 18px;
                    border: none;
                    border-radius: 8px;
                    font-size: 16px;
                    cursor: pointer;
                }}

                .buscar {{
                    background: #3483fa;
                    color: white;
                    width: 100%;
                }}

            </style>

        </head>

        <body>

            <div class="container">

                <div class="card">

                    <h1>
                        🤖 Robô Ofertas ML
                    </h1>

                    <p>
                        ✅ Mercado Livre conectado!
                    </p>

                    <p>
                        Usuário:
                        <strong>
                            {html.escape(str(nickname))}
                        </strong>
                    </p>

                    <p>
                        ID:
                        <strong>
                            {html.escape(str(user_id))}
                        </strong>
                    </p>

                </div>


                <div class="card">

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
                            placeholder="Ex.: celular, relógio, tênis..."
                            required
                        >

                        <button
                            class="buscar"
                            type="submit"
                        >
                            🔎 Pesquisar
                        </button>

                    </form>

                </div>

            </div>

        </body>

        </html>

        """


    # ========================================================
    # VALIDA CONFIGURAÇÕES
    # ========================================================

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


    # ========================================================
    # PKCE
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


    session["code_verifier"] = code_verifier

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

        "https://auth.mercadolivre.com.br/authorization?"

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
                font-family: Arial, sans-serif;
                background: #f5f5f5;
                padding: 30px;
                text-align: center;
            }}

            .card {{
                background: white;
                max-width: 500px;
                margin: auto;
                padding: 30px;
                border-radius: 15px;
            }}

            .botao {{
                display: inline-block;
                background: #ffe600;
                color: #333;
                padding: 15px 25px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: bold;
            }}

        </style>

    </head>

    <body>

        <div class="card">

            <h1>
                🤖 Robô Ofertas ML
            </h1>

            <p>
                Conecte sua conta do Mercado Livre
                para começar.
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
# BUSCAR PRODUTOS
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
            🔎 Busca de produtos
        </h1>

        <p>
            Digite um produto para pesquisar.
        </p>

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
            ❌ Mercado Livre não conectado
        </h1>

        <p>
            Conecte sua conta antes de pesquisar.
        </p>

        <a href="/">
            🔗 Conectar Mercado Livre
        </a>

        """, 401


    # ========================================================
    # USER PRODUCTS
    # ========================================================

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
                20,

        },

        timeout=30,

    )


    if response.status_code != 200:

        return f"""

        <!DOCTYPE html>

        <html>

        <head>

            <meta charset="UTF-8">

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
{html.escape(response.text)}
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
            Ofertas - {html.escape(termo)}
        </title>

        <style>

            body {{
                font-family: Arial, sans-serif;
                background: #f5f5f5;
                margin: 0;
                padding: 15px;
            }}

            .container {{
                max-width: 800px;
                margin: auto;
            }}

            .topo {{
                background: white;
                padding: 20px;
                border-radius: 15px;
                margin-bottom: 15px;
            }}

            .produto {{
                background: white;
                border-radius: 15px;
                padding: 15px;
                margin-bottom: 15px;
                box-shadow:
                    0 2px 8px
                    rgba(0,0,0,0.08);
            }}

            .produto img {{
                width: 150px;
                height: 150px;
                object-fit: contain;
                display: block;
                margin-bottom: 10px;
            }}

            .titulo {{
                font-size: 17px;
                font-weight: bold;
                margin-bottom: 10px;
            }}

            .id {{
                color: #777;
                font-size: 13px;
                margin-bottom: 10px;
            }}

            .botao {{
                display: inline-block;
                padding: 11px 15px;
                border-radius: 8px;
                border: none;
                text-decoration: none;
                cursor: pointer;
                font-size: 14px;
                margin-top: 5px;
            }}

            .oferta {{
                background: #00a650;
                color: white;
            }}

            .selecionado {{
                background: #777;
                color: white;
            }}

            .lista {{
                background: white;
                padding: 20px;
                border-radius: 15px;
                margin-top: 20px;
            }}

            .item-oferta {{
                border-bottom: 1px solid #ddd;
                padding: 10px 0;
            }}

            .item-oferta:last-child {{
                border-bottom: none;
            }}

            .gerar {{
                width: 100%;
                background: #3483fa;
                color: white;
                font-size: 17px;
                padding: 15px;
                margin-top: 15px;
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
                Termo:
                <strong>
                    {html.escape(termo)}
                </strong>
            </p>

            <a href="/">
                ← Nova busca
            </a>

        </div>

    """


    if not produtos:

        html_page += """

        <div class="topo">

            <h2>
                😕 Nenhum produto encontrado.
            </h2>

        </div>

        """


    # ========================================================
    # PRODUTOS
    # ========================================================

    for produto in produtos:

        produto_id = produto.get(
            "id",
            ""
        )


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


        # User Products pode não trazer preço.
        preco = produto.get(
            "price"
        )


        if preco is not None:

            preco_html = (
                "R$ "
                + str(preco)
            )

        else:

            preco_html = (
                "Preço não informado"
            )


        # Escapa dados para JavaScript/HTML
        titulo_js = (
            titulo
            .replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("${", "\\${")
        )


        imagem_js = (
            imagem
            .replace("\\", "\\\\")
            .replace("`", "\\`")
        )


        preco_js = (
            preco_html
            .replace("\\", "\\\\")
            .replace("`", "\\`")
        )


        html_page += f"""

        <div
            class="produto"
        >

            <img
                src="{html.escape(imagem)}"
                alt="{html.escape(titulo)}"
            >

            <div class="titulo">

                {html.escape(titulo)}

            </div>

            <div class="id">

                ID:
                {html.escape(str(produto_id))}

            </div>

            <p>

                <strong>
                    {html.escape(preco_html)}
                </strong>

            </p>


            <button
                class="botao oferta"
                onclick="
                    adicionarOferta(
                        `{html.escape(str(produto_id))}`,
                        `{titulo_js}`,
                        `{imagem_js}`,
                        `{preco_js}`
                    )
                "
            >

                ⭐ Adicionar à oferta

            </button>

        </div>

        """


    # ========================================================
    # LISTA DE OFERTAS
    # ========================================================

    html_page += """

        <div class="lista">

            <h2>
                ⭐ Ofertas selecionadas
            </h2>

            <div id="ofertas">

                <p>
                    Nenhum produto selecionado.
                </p>

            </div>

            <button
                class="botao gerar"
                onclick="gerarOferta()"
            >

                📲 Gerar oferta

            </button>

        </div>


    </div>


    <script>

        let ofertas = [];


        function adicionarOferta(
            id,
            titulo,
            imagem,
            preco
        ) {

            const existe =
                ofertas.find(
                    produto =>
                        produto.id === id
                );


            if (existe) {

                alert(
                    "Esse produto já foi adicionado."
                );

                return;

            }


            ofertas.push({

                id: id,

                titulo: titulo,

                imagem: imagem,

                preco: preco

            });


            atualizarOfertas();

        }


        function removerOferta(id) {

            ofertas =
                ofertas.filter(
                    produto =>
                        produto.id !== id
                );


            atualizarOfertas();

        }


        function atualizarOfertas() {

            const area =
                document.getElementById(
                    "ofertas"
                );


            if (
                ofertas.length === 0
            ) {

                area.innerHTML =
                    "<p>Nenhum produto selecionado.</p>";

                return;

            }


            let html = "";


            ofertas.forEach(
                produto => {

                    html += `

                    <div
                        class="item-oferta"
                    >

                        <strong>
                            ${produto.titulo}
                        </strong>

                        <br>

                        ${produto.preco}

                        <br>

                        <button
                            class="botao"
                            style="
                                background:#e53935;
                                color:white;
                            "
                            onclick="
                                removerOferta(
                                    '${produto.id}'
                                )
                            "
                        >

                            🗑️ Remover

                        </button>

                    </div>

                    `;

                }
            );


            area.innerHTML = html;

        }


        function gerarOferta() {

            if (
                ofertas.length === 0
            ) {

                alert(
                    "Adicione pelo menos um produto."
                );

                return;

            }


            let mensagem =
                "🔥 OFERTAS DO DIA 🔥\\n\\n";


            ofertas.forEach(
                produto => {

                    mensagem +=
                        "🛍️ "
                        + produto.titulo
                        + "\\n";

                    mensagem +=
                        "💰 "
                        + produto.preco
                        + "\\n";

                    mensagem +=
                        "🆔 "
                        + produto.id
                        + "\\n\\n";

                }
            );


            // Mostra a oferta
            // por enquanto.
            // Depois vamos colocar
            // o link real do anúncio.

            alert(mensagem);

        }

    </script>


    </body>

    </html>

    """


    return html_page


# ============================================================
# SERVIDOR
# ============================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=int(
            os.environ.get(
                "PORT",
                10000
            )
        )

    )
