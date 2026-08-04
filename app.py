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

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


API_BASE = "https://api.mercadolibre.com"

SITE_ID = "MLB"


# ============================================================
# CATEGORIAS DE BUSCA
# ============================================================

CATEGORIAS = {

    "celulares":
    "MLB1055",

    "roupas":
    "MLB1430",

    "relogios":
    "MLB3937",

    "eletronicos":
    "MLB1000",

    "informatica":
    "MLB1648",

    "beleza":
    "MLB1246"

}


# ============================================================
# CONFIGURAÇÃO DA REVENDA
# ============================================================

MARGEM_PADRAO = 10

LUCRO_MINIMO_PADRAO = 20


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================


def escapar(valor):

    return html.escape(
        str(valor or "")
    )


def numero(valor):

    try:

        return float(valor)

    except:

        return 0.0



def formatar_preco(valor):

    try:

        valor = float(valor)

        return (
            f"R$ {valor:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    except:

        return "R$ 0,00"



# ============================================================
# HEADERS API
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
# REQUEST MERCADO LIVRE
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

    except Exception as erro:

        print(
            erro
        )

        return None



# ============================================================
# LOGIN INICIAL
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

        return "CLIENT_ID faltando",500


    if code:


        saved_state = session.get(
            "state"
        )


        if state != saved_state:

            return "State inválido",400


        code_verifier = session.get(
            "code_verifier"
        )


        resposta = requests.post(

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


        if resposta.status_code != 200:

            return resposta.text,400


        dados = resposta.json()


        session["access_token"] = (
            dados["access_token"]
        )


        return painel()



    code_verifier = (
        secrets.token_urlsafe(64)
    )


    challenge = (

        base64.urlsafe_b64encode(

            hashlib.sha256(

                code_verifier.encode()

            ).digest()

        )

        .rstrip(b"=")

        .decode()

    )


    state = secrets.token_urlsafe(32)


    session["state"] = state

    session["code_verifier"] = (
        code_verifier
    )


    url = (

        "https://auth.mercadolivre.com.br/authorization?"

        + urlencode({

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

        })

    )


    return f"""

    <h1>🤖 Robô Ofertas ML</h1>

    <p>Conecte sua conta Mercado Livre</p>

    <a href="{url}">
    🔐 Conectar
    </a>

    """
    # ============================================================
# PAINEL PRINCIPAL
# ============================================================


def painel():

    return """

    <!DOCTYPE html>

    <html>

    <head>

    <meta charset="UTF-8">

    <meta name="viewport"
    content="width=device-width, initial-scale=1">

    <title>
    Robô Ofertas ML
    </title>

    </head>


    <body style="
    font-family:Arial;
    background:#f5f5f5;
    padding:20px;
    ">


    <div style="
    max-width:600px;
    margin:auto;
    background:white;
    padding:25px;
    border-radius:15px;
    ">


    <h1>
    🤖 Robô Ofertas ML
    </h1>


    <p>
    ✅ Mercado Livre conectado
    </p>


    <hr>


    <h2>
    🔎 Buscar ofertas
    </h2>


    <form action="/buscar"
    method="get">


    <input
    name="q"
    placeholder="Ex: iPhone, relógio, camiseta..."
    style="
    width:100%;
    padding:15px;
    font-size:16px;
    "
    required>


    <br><br>


    <label>
    Categoria
    </label>


    <select
    name="categoria"
    style="
    width:100%;
    padding:12px;
    ">


    <option value="todas">
    Todas
    </option>


    <option value="celulares">
    📱 Celulares
    </option>


    <option value="roupas">
    👕 Roupas
    </option>


    <option value="relogios">
    ⌚ Relógios
    </option>


    <option value="eletronicos">
    🎧 Eletrônicos
    </option>


    <option value="informatica">
    💻 Informática
    </option>


    <option value="beleza">
    💄 Beleza
    </option>


    </select>


    <br><br>


    <label>
    📈 Margem de lucro %
    </label>


    <input
    type="number"
    name="margem"
    value="10"
    style="
    width:100%;
    padding:12px;
    ">


    <br><br>


    <label>
    💰 Lucro mínimo
    </label>


    <input
    type="number"
    name="lucro_minimo"
    value="20"
    style="
    width:100%;
    padding:12px;
    ">


    <br><br>


    <button
    style="
    width:100%;
    padding:15px;
    background:#3483fa;
    color:white;
    border:0;
    border-radius:8px;
    font-size:18px;
    ">

    🔥 Encontrar ofertas

    </button>


    </form>


    </div>


    </body>

    </html>

    """



# ============================================================
# BUSCA DE PRODUTOS
# ============================================================


def buscar_produtos(
    termo,
    categoria="todas"
):


    params = {


        "site_id":
        SITE_ID,


        "q":
        termo,


        "limit":
        30,


        "sort":
        "relevance"

    }


    if categoria in CATEGORIAS:

        params["category"] = (
            CATEGORIAS[categoria]
        )


    resposta = requisicao_get(

        f"{API_BASE}/sites/{SITE_ID}/search",

        params

    )


    if resposta is None:

        return []


    if resposta.status_code != 200:

        return []


    try:

        dados = resposta.json()

        return dados.get(
            "results",
            []
        )


    except:

        return []
def montar_oferta(produto, margem):

    preco = numero(
        produto.get("price")
    )

    if preco <= 0:
        return None


    preco_venda = preco * (
        1 + margem / 100
    )


    lucro = preco_venda - preco


    return {

        "id": produto.get("id"),

        "titulo": produto.get(
            "title",
            "Produto"
        ),

        "imagem": produto.get(
            "thumbnail"
        ),

        "preco": preco,

        "venda": preco_venda,

        "lucro": lucro,

        "link": produto.get(
            "permalink",
            ""
        ),

        "vendidos": produto.get(
            "sold_quantity",
            0
        )

    


# ============================================================
# CALCULAR OFERTA
# ============================================================



    }# ============================================================
# PÁGINA DE RESULTADOS
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


    try:

        margem = float(
            request.args.get(
                "margem",
                10
            )
        )

    except:

        margem = 10



    try:

        lucro_minimo = float(
            request.args.get(
                "lucro_minimo",
                20
            )
        )

    except:

        lucro_minimo = 20



    produtos = buscar_produtos(
        termo,
        categoria
    )


    ofertas = []


    for produto in produtos:


        oferta = montar_oferta(
            produto,
            margem
        )


        if oferta is None:

            continue



        if oferta["lucro"] >= lucro_minimo:

            ofertas.append(
                oferta
            )



    # ordenar pelo mais vendido e maior lucro

    ofertas.sort(

        key=lambda x:

        (
            x["vendidos"],
            x["lucro"]
        ),

        reverse=True

    )



    pagina = f"""

    <!DOCTYPE html>

    <html>

    <head>

    <meta charset="UTF-8">

    <meta name="viewport"
    content="width=device-width, initial-scale=1">


    <title>
    Ofertas
    </title>


    <style>

    body {{

        font-family:Arial;
        background:#f5f5f5;
        padding:15px;

    }}


    .card {{

        background:white;
        border-radius:15px;
        padding:20px;
        margin-bottom:20px;

    }}


    img {{

        width:200px;
        max-height:200px;
        object-fit:contain;

    }}


    .preco {{

        font-size:18px;

    }}


    .venda {{

        color:green;
        font-size:26px;
        font-weight:bold;

    }}


    .lucro {{

        background:#d4edda;
        padding:10px;
        border-radius:8px;
        font-size:20px;

    }}


    .botao {{

        display:inline-block;
        padding:12px 18px;
        border-radius:8px;
        text-decoration:none;
        color:white;
        margin-top:10px;

    }}


    .mercado {{

        background:#3483fa;

    }}


    .zap {{

        background:#25D366;

    }}


    </style>


    </head>


    <body>


    <h1>
    🔥 Ofertas encontradas
    </h1>


    <p>
    Produto:
    <b>{escapar(termo)}</b>
    </p>


    <p>
    Oportunidades:
    <b>{len(ofertas)}</b>
    </p>


    """



    if not ofertas:


        pagina += """

        <div class="card">

        <h2>
        😕 Nenhum produto encontrado
        </h2>


        <p>
        Tente outro produto ou diminua
        o lucro mínimo.
        </p>


        </div>

        """



    for oferta in ofertas:



        mensagem = (

            f"🔥 Oferta encontrada!\n\n"

            f"📦 {oferta['titulo']}\n\n"

            f"💰 Por apenas: "

            f"{formatar_preco(oferta['venda'])}\n\n"

            f"🛒 Compre aqui:\n"

            f"{oferta['link']}"

        )



        whatsapp = (

            "https://wa.me/?text="

            + quote(
                mensagem
            )

        )



        pagina += f"""

        <div class="card">


        <img src="{escapar(oferta['imagem'])}">


        <h2>

        📦 {escapar(oferta['titulo'])}

        </h2>



        <p class="preco">

        💵 Compra:

        <b>
        {formatar_preco(oferta['preco'])}
        </b>

        </p>



        <p class="venda">

        🏷️ Venda:

        {formatar_preco(oferta['venda'])}

        </p>



        <div class="lucro">

        💰 Lucro:

        {formatar_preco(oferta['lucro'])}

        </div>



        <p>

        🔥 Vendidos:

        {oferta['vendidos']}

        </p>



        <a class="botao mercado"
        href="{escapar(oferta['link'])}"
        target="_blank">

        🛒 Abrir anúncio

        </a>



        <a class="botao zap"
        href="{escapar(whatsapp)}"
        target="_blank">

        📲 Enviar WhatsApp

        </a>



        </div>


        """



    pagina += """

    <br>

    <a href="/">
    ← Nova busca
    </a>


    </body>

    </html>

    """



    return pagina# ============================================================
# DIAGNÓSTICO
# ============================================================


@app.route("/diagnostico")
def diagnostico():


    if not session.get(
        "access_token"
    ):

        return """

        <h2>
        ❌ Mercado Livre não conectado
        </h2>

        <a href="/">
        Voltar
        </a>

        """



    resposta = requisicao_get(

        f"{API_BASE}/users/me"

    )


    if resposta is None:

        texto = "Erro de conexão"

    else:

        texto = resposta.text



    return f"""

    <!DOCTYPE html>

    <html>

    <head>

    <meta charset="UTF-8">

    <meta name="viewport"
    content="width=device-width, initial-scale=1">

    <title>
    Diagnóstico
    </title>

    </head>


    <body style="
    font-family:Arial;
    padding:20px;
    ">


    <h1>
    🧪 Diagnóstico Mercado Livre
    </h1>


    <p>
    Status:
    <b>
    {resposta.status_code if resposta else "ERRO"}
    </b>
    </p>


    <pre>

    {escapar(texto)}

    </pre>


    <a href="/">
    ← Voltar
    </a>


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


    <a href="/">
    Conectar novamente
    </a>

    """



# ============================================================
# TESTE CONFIGURAÇÃO
# ============================================================


@app.route("/teste-config")
def teste_config():


    return f"""

    <h1>
    🧪 Configuração
    </h1>


    <p>

    CLIENT_ID:

    <b>
    {"OK" if CLIENT_ID else "FALTANDO"}
    </b>

    </p>


    <p>

    CLIENT_SECRET:

    <b>
    {"OK" if CLIENT_SECRET else "FALTANDO"}
    </b>

    </p>



    <p>

    REDIRECT_URI:

    <b>
    {escapar(REDIRECT_URI)}
    </b>

    </p>



    <a href="/">
    Voltar
    </a>

    """



# ============================================================
# INICIAR SERVIDOR
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
