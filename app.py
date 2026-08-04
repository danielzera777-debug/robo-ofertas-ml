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
# CONFIGURAÇÃO DE REVENDA
# ============================================================

MARGEM_PADRAO = 15

LUCRO_MINIMO = 10



# ============================================================
# CATEGORIAS DE PRODUTOS
# ============================================================

CATEGORIAS = {

    "celulares": {
        "nome": "📱 Celulares",
        "categoria": "MLB1055"
    },

    "roupas": {
        "nome": "👕 Roupas",
        "categoria": "MLB1430"
    },

    "relogios": {
        "nome": "⌚ Relógios",
        "categoria": "MLB3937"
    },

    "eletronicos": {
        "nome": "🎧 Eletrônicos",
        "categoria": "MLB1000"
    },

    "casa": {
        "nome": "🏠 Casa e decoração",
        "categoria": "MLB1574"
    },

    "ferramentas": {
        "nome": "🔧 Ferramentas",
        "categoria": "MLB263532"
    }

}



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

        return 0



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
# REQUISIÇÃO MERCADO LIVRE
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
# LOGIN MERCADO LIVRE
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

            }

        )



        if resposta.status_code != 200:

            return resposta.text,400



        dados = resposta.json()



        session["access_token"] = (
            dados["access_token"]
        )


        usuario = requisicao_get(

            f"{API_BASE}/users/me"

        ).json()



        return tela_inicial(
            usuario
        )



    verifier = (
        secrets.token_urlsafe(64)
    )


    challenge = (

        base64.urlsafe_b64encode(

            hashlib.sha256(

                verifier.encode()

            ).digest()

        )

        .rstrip(b"=")

        .decode()

    )



    state = secrets.token_urlsafe(32)



    session["state"] = state

    session["code_verifier"] = verifier



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

    <a href="{url}">

    <button>
    🔐 Conectar Mercado Livre
    </button>

    </a>

    """# ============================================================
# BUSCA INTELIGENTE DE PRODUTOS
# ============================================================


def buscar_produtos(

        termo,

        categoria="todas"

):


    produtos = []



    if categoria == "todas":

        categorias = list(
            CATEGORIAS.values()
        )


    else:

        categorias = [

            CATEGORIAS.get(
                categoria
            )

        ]



    for cat in categorias:


        if not cat:
            continue



        resposta = requisicao_get(


            f"{API_BASE}/sites/{SITE_ID}/search",


            {


                "q":
                termo,


                "category":
                cat["categoria"],


                "sort":
                "sold_quantity_desc",


                "limit":
                30


            }

        )



        if resposta is None:

            continue



        if resposta.status_code != 200:

            continue



        try:

            dados = resposta.json()


        except:

            continue



        for item in dados.get(
            "results",
            []
        ):



            item["categoria_nome"] = (
                cat["nome"]
            )


            produtos.append(
                item
            )



    return produtos




# ============================================================
# ORGANIZAR MELHORES OPORTUNIDADES
# ============================================================


def analisar_produtos(

        produtos,

        margem=15

):


    oportunidades = []



    vistos = set()



    for produto in produtos:



        item_id = produto.get(
            "id"
        )



        if not item_id:

            continue



        if item_id in vistos:

            continue



        vistos.add(
            item_id
        )



        preco = numero(

            produto.get(
                "price"
            )

        )



        vendidos = produto.get(

            "sold_quantity",

            0

        )



        if preco <= 0:

            continue




        preco_revenda = (

            preco *

            (

                1 +

                margem / 100

            )

        )



        lucro = (

            preco_revenda -

            preco

        )



        oportunidades.append({


            "id":

            item_id,



            "titulo":

            produto.get(

                "title",

                "Produto"

            ),



            "imagem":

            produto.get(

                "thumbnail",

                ""

            ),



            "link":

            produto.get(

                "permalink",

                ""

            ),



            "preco_compra":

            preco,



            "preco_venda":

            preco_revenda,



            "lucro":

            lucro,



            "vendidos":

            vendidos,



            "categoria":

            produto.get(

                "categoria_nome",

                ""

            ),



            "estoque":

            produto.get(

                "available_quantity",

                0

            )

        })




    # Primeiro os que vendem mais,
    # depois os mais baratos


    oportunidades.sort(

        key=lambda x:


        (

            x["vendidos"],

            -x["preco_compra"]

        ),


        reverse=True

    )



    return oportunidades[:50]




# ============================================================
# BUSCAR PRODUTOS EM DESTAQUE
# ============================================================


def buscar_ofertas_destaque(

        termo

):


    produtos = buscar_produtos(

        termo

    )



    ofertas = analisar_produtos(

        produtos,

        MARGEM_PADRAO

    )



    return ofertas# ============================================================
# TELA PRINCIPAL APÓS LOGIN
# ============================================================


def tela_inicial(usuario):


    nome = usuario.get(
        "nickname",
        "usuário"
    )


    return f"""

    <html>

    <head>

    <meta charset="UTF-8">

    <meta name="viewport"
    content="width=device-width, initial-scale=1">

    <title>
    Robô Ofertas ML
    </title>


    <style>

    body {{

        font-family: Arial;

        background:#f5f5f5;

        padding:20px;

    }}


    .box {{

        background:white;

        padding:20px;

        border-radius:15px;

        max-width:700px;

        margin:auto;

    }}


    input {{

        width:100%;

        padding:15px;

        font-size:18px;

        margin-bottom:10px;

    }}


    button {{

        width:100%;

        padding:15px;

        background:#3483fa;

        color:white;

        border:0;

        border-radius:8px;

        font-size:18px;

    }}


    </style>


    </head>


    <body>


    <div class="box">


    <h1>
    🤖 Robô Ofertas ML
    </h1>


    <p>
    Usuário conectado:
    <b>{escapar(nome)}</b>
    </p>



    <form action="/ofertas">


    <input

    name="produto"

    placeholder="Ex: iPhone, relógio, tênis"

    required

    >



    <button>

    🔎 Procurar ofertas

    </button>


    </form>


    </div>


    </body>

    </html>

    """





# ============================================================
# PÁGINA DE OFERTAS
# ============================================================


@app.route("/ofertas")
def ofertas():


    termo = request.args.get(

        "produto",

        ""

    )


    produtos = buscar_ofertas_destaque(

        termo

    )



    pagina = f"""

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

        padding:20px;

        border-radius:15px;

        margin-bottom:20px;

    }}



    img {{

        width:100%;

        max-width:300px;

        border-radius:10px;

    }}



    .preco {{

        font-size:22px;

        color:#555;

    }}



    .lucro {{

        background:#d4edda;

        padding:12px;

        border-radius:8px;

        font-size:20px;

        font-weight:bold;

    }}



    .botao {{

        display:block;

        text-align:center;

        padding:15px;

        margin-top:10px;

        border-radius:8px;

        color:white;

        text-decoration:none;

    }}



    .ml {{

        background:#3483fa;

    }}



    .zap {{

        background:#25d366;

    }}



    </style>


    </head>


    <body>


    <h1>

    🔥 Ofertas encontradas

    </h1>

    """




    if not produtos:


        pagina += """

        <h2>

        😕 Nenhum produto encontrado

        </h2>

        """



    for produto in produtos:



        mensagem = (


            f"🔥 Oferta encontrada!\n\n"

            f"{produto['titulo']}\n\n"

            f"💰 Preço:\n"

            f"{formatar_preco(produto['preco_venda'])}\n\n"

            f"🛒 Comprar:\n"

            f"{produto['link']}"

        )



        whatsapp = (

            "https://wa.me/?text="

            +

            quote(mensagem)

        )



        pagina += f"""

        <div class="card">


        <img src="{produto['imagem']}">


        <h2>

        {escapar(produto['titulo'])}

        </h2>



        <p>

        📂 Categoria:

        <b>
        {produto['categoria']}
        </b>

        </p>



        <p class="preco">

        💵 Compra:

        {formatar_preco(produto['preco_compra'])}

        </p>



        <p>

        🏷️ Revenda:

        <b>

        {formatar_preco(produto['preco_venda'])}

        </b>

        </p>



        <div class="lucro">

        💰 Lucro:

        {formatar_preco(produto['lucro'])}

        </div>



        <p>

        🔥 Vendidos:

        {produto['vendidos']}

        </p>



        <a class="botao ml"

        href="{produto['link']}"

        target="_blank">

        🛒 Abrir Mercado Livre

        </a>



        <a class="botao zap"

        href="{whatsapp}"

        target="_blank">

        📲 Enviar oferta WhatsApp

        </a>



        </div>


        """



    pagina += """

    </body>

    </html>

    """



    return pagina# ============================================================
# FILTRO POR CATEGORIA
# ============================================================


@app.route("/categoria")
def categoria():


    nome = request.args.get(

        "tipo",

        "todas"

    )


    produtos = buscar_produtos(

        "",

        nome

    )


    ofertas = analisar_produtos(

        produtos,

        MARGEM_PADRAO

    )



    pagina = """

    <html>

    <head>

    <meta charset="UTF-8">

    <meta name="viewport"
    content="width=device-width, initial-scale=1">

    <title>
    Categorias
    </title>

    </head>


    <body style="font-family:Arial;padding:20px">


    <h1>
    🔥 Produtos em alta
    </h1>


    """



    for produto in ofertas:


        mensagem = (

            "🔥 Oferta especial!\n\n"

            + produto["titulo"]

            + "\n\n💰 Apenas "

            + formatar_preco(

                produto["preco_venda"]

            )

            + "\n\n🛒 Garanta aqui:\n"

            + produto["link"]

        )



        link_zap = (

            "https://wa.me/?text="

            +

            quote(mensagem)

        )



        pagina += f"""

        <div style="
        background:white;
        padding:20px;
        margin-bottom:20px;
        border-radius:15px;
        ">


        <img src="{produto['imagem']}"
        width="200">


        <h2>

        {produto['titulo']}

        </h2>


        <p>
        💵 Compra:
        {formatar_preco(produto['preco_compra'])}
        </p>


        <p>
        🏷️ Venda:
        {formatar_preco(produto['preco_venda'])}
        </p>


        <p>
        💰 Lucro:
        {formatar_preco(produto['lucro'])}
        </p>


        <p>
        🔥 Vendidos:
        {produto['vendidos']}
        </p>


        <a href="{link_zap}"
        style="
        background:#25D366;
        color:white;
        padding:12px;
        border-radius:8px;
        text-decoration:none;
        ">

        📲 Mandar para cliente

        </a>


        </div>

        """



    pagina += """

    </body>

    </html>

    """



    return pagina





# ============================================================
# MENU DE CATEGORIAS
# ============================================================


@app.route("/menu")
def menu():


    html_menu = """

    <html>

    <body style="
    font-family:Arial;
    padding:20px">

    <h1>
    🛒 Escolha categoria
    </h1>

    """



    for chave, valor in CATEGORIAS.items():


        html_menu += f"""


        <p>

        <a href="/categoria?tipo={chave}">

        {valor['nome']}

        </a>

        </p>


        """



    html_menu += """

    <p>

    <a href="/categoria?tipo=todas">

    🔥 Todos os produtos

    </a>

    </p>


    </body>

    </html>

    """



    return html_menu





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
# TESTE
# ============================================================


@app.route("/teste")
def teste():


    return """

    <h1>
    ✅ Robô funcionando
    </h1>


    <p>
    Mercado Livre conectado.
    </p>


    <a href="/menu">

    Ver produtos

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
