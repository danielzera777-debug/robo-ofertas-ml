import os
import secrets
import html
import requests

from flask import (
    Flask,
    request,
    session,
    redirect,
    url_for,
    jsonify,
    render_template_string
)

from urllib.parse import urlencode


# ============================================================
# CONFIGURAÇÃO
# ============================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    secrets.token_hex(32)
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# Mercado Livre

CLIENT_ID = os.getenv("ML_CLIENT_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ML_REDIRECT_URI")


API_BASE = "https://api.mercadolibre.com"


# ============================================================
# CONFIGURAÇÕES DO ROBÔ
# ============================================================

SITE_ID = "MLB"


MARGEM_PADRAO = 10


CATEGORIAS = {

    "celulares":
        "MLB1055",

    "informatica":
        "MLB1648",

    "eletronicos":
        "MLB1000",

    "roupas":
        "MLB1430",

    "relogios":
        "MLB3937",

    "beleza":
        "MLB1246"

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



def calcular_preco_venda(custo):

    custo = numero(custo)

    return custo + (
        custo * MARGEM_PADRAO / 100
    )



# ============================================================
# MERCADO LIVRE API
# ============================================================


def headers_api():

    headers = {

        "Accept":
            "application/json",

        "User-Agent":
            "Robo-Ofertas-Instagram-WhatsApp/1.0"

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
# LOGIN MERCADO LIVRE
# ============================================================


@app.route("/login")

def login():

    params = {

        "response_type":
            "code",

        "client_id":
            CLIENT_ID,

        "redirect_uri":
            REDIRECT_URI

    }


    url = (
        "https://auth.mercadolivre.com.br/authorization?"
        +
        urlencode(params)
    )


    return redirect(url)




@app.route("/callback")

def callback():

    code = request.args.get(
        "code"
    )


    if not code:

        return "Código não recebido"



    dados = {

        "grant_type":
            "authorization_code",

        "client_id":
            CLIENT_ID,

        "client_secret":
            CLIENT_SECRET,

        "code":
            code,

        "redirect_uri":
            REDIRECT_URI

    }



    resposta = requests.post(

        f"{API_BASE}/oauth/token",

        data=dados

    )



    if resposta.status_code != 200:

        return resposta.text



    token = resposta.json()



    session["access_token"] = (
        token["access_token"]
    )


    return redirect("/")



# ============================================================
# BUSCA DE PRODUTOS
# ============================================================


def buscar_produtos(
        categoria,
        limite=10
):

    url = (

        f"{API_BASE}/sites/{SITE_ID}"
        "/search"

    )


    params = {

        "category":
            CATEGORIAS.get(
                categoria,
                ""
            ),

        "limit":
            limite

    }



    resposta = requests.get(

        url,

        params=params,

        headers=headers_api()

    )



    if resposta.status_code != 200:

        return []



    return resposta.json().get(

        "results",

        []

    )
    # ============================================================
# FILTRO DE OFERTAS
# ============================================================


def analisar_oferta(produto):

    preco = numero(
        produto.get("price")
    )


    titulo = produto.get(
        "title",
        "Produto"
    )


    link = produto.get(
        "permalink",
        ""
    )


    imagem = produto.get(
        "thumbnail",
        ""
    )


    if preco <= 0:

        return None



    preco_sugerido = calcular_preco_venda(
        preco
    )


    return {

        "titulo":
            titulo,

        "preco":
            preco,

        "preco_venda":
            preco_sugerido,

        "link":
            link,

        "imagem":
            imagem

    }



def gerar_ofertas(categoria):

    produtos = buscar_produtos(
        categoria
    )


    ofertas = []


    for produto in produtos:


        oferta = analisar_oferta(
            produto
        )


        if oferta:

            ofertas.append(
                oferta
            )


    return ofertas



# ============================================================
# MENSAGEM PARA WHATSAPP
# ============================================================


def criar_mensagem_whatsapp(
        oferta
):


    mensagem = f"""

🔥 ACHADINHO DO DIA 🔥


📦 {oferta['titulo']}


💰 Preço encontrado:
{formatar_preco(oferta['preco'])}


🚀 Confira aqui:
{oferta['link']}


⚡ Oferta por tempo limitado!

"""


    return mensagem.strip()



# ============================================================
# CONTEÚDO PARA INSTAGRAM
# ============================================================


def criar_anuncio_instagram():

    texto = """

🔥 GRUPO VIP DE OFERTAS 🔥


Quer receber promoções todos os dias?


✅ Produtos baratos
✅ Ofertas relâmpago
✅ Achadinhos da internet


Entre no nosso grupo gratuito do WhatsApp.


👇 Link na bio

"""


    return texto.strip()



# ============================================================
# ROTAS PRINCIPAIS
# ============================================================


@app.route("/")

def inicio():

    conectado = (
        "Sim"
        if session.get("access_token")
        else
        "Não"
    )


    pagina = """

    <h1>
    🤖 Robô de Ofertas
    </h1>


    <p>
    Mercado Livre conectado:
    {{conectado}}
    </p>


    <a href="/login">
    Conectar Mercado Livre
    </a>


    <br><br>


    <a href="/ofertas/celulares">
    Buscar celulares
    </a>


    """


    return render_template_string(

        pagina,

        conectado=conectado

    )





@app.route(
    "/ofertas/<categoria>"
)

def ofertas(categoria):


    lista = gerar_ofertas(
        categoria
    )


    return jsonify(
        lista
    )





@app.route(
    "/whatsapp/<categoria>"
)

def whatsapp(categoria):


    ofertas = gerar_ofertas(
        categoria
    )


    mensagens = []


    for oferta in ofertas:

        mensagens.append(

            criar_mensagem_whatsapp(
                oferta
            )

        )


    return jsonify(

        mensagens

    )





@app.route(
    "/instagram"
)

def instagram():

    return jsonify({

        "anuncio":
            criar_anuncio_instagram()

    })





# ============================================================
# INICIALIZAÇÃO
# ============================================================


if __name__ == "__main__":


    app.run(

        host="0.0.0.0",

        port=int(

            os.getenv(
                "PORT",
                5000
            )

        ),

        debug=True

    )
