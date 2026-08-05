import os
import secrets
import hashlib
import base64
import html
import requests

from urllib.parse import urlencode

from flask import (
    Flask,
    request,
    session,
    redirect,
    jsonify,
    render_template_string
)


# ============================================================
# CONFIGURAÇÃO FLASK
# ============================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    secrets.token_hex(32)
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# ============================================================
# MERCADO LIVRE
# ============================================================

CLIENT_ID = os.getenv(
    "ML_CLIENT_ID"
)

CLIENT_SECRET = os.getenv(
    "ML_CLIENT_SECRET"
)

REDIRECT_URI = os.getenv(
    "ML_REDIRECT_URI"
)


API_BASE = (
    "https://api.mercadolibre.com"
)


SITE_ID = "MLB"



# ============================================================
# CATEGORIAS
# ============================================================

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



MARGEM_PADRAO = 10



# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================


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



def escapar(valor):

    return html.escape(
        str(valor or "")
    )



# ============================================================
# HEADERS API
# ============================================================


def headers_api():

    headers = {

        "Accept":
            "application/json",

        "User-Agent":
            "Robo-Ofertas-ML"

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
# LOGIN MERCADO LIVRE COM PKCE
# ============================================================


@app.route("/login")
def login():


    code_verifier = (
        secrets.token_urlsafe(64)
    )


    code_challenge = (

        base64.urlsafe_b64encode(

            hashlib.sha256(

                code_verifier.encode()

            ).digest()

        )

        .decode()

        .replace("=", "")

    )


    session["code_verifier"] = (
        code_verifier
    )


    params = {

        "response_type":
            "code",

        "client_id":
            CLIENT_ID,

        "redirect_uri":
            REDIRECT_URI,

        "code_challenge":
            code_challenge,

        "code_challenge_method":
            "S256"

    }


    url = (

        "https://auth.mercadolivre.com.br/authorization?"

        +

        urlencode(params)

    )


    return redirect(url)



# ============================================================
# CALLBACK TOKEN
# ============================================================


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
            REDIRECT_URI,

        "code_verifier":
            session.get(
                "code_verifier"
            )

    }



    resposta = requests.post(

        f"{API_BASE}/oauth/token",

        data=dados

    )



    if resposta.status_code != 200:

        return resposta.text



    token = resposta.json()



    session["access_token"] = (
        token.get(
            "access_token"
        )
    )


    return redirect("/")



# ============================================================
# BUSCA DE PRODUTOS
# ============================================================


def buscar_produtos(categoria, limite=10):

    url = "https://api.mercadolibre.com/sites/MLB/search"

    params = {
        "q": "celular",
        "limit": limite
    }

    resposta = requests.get(
        url,
        params=params,
        headers=headers_api()
    )

    print(resposta.text)

    if resposta.status_code != 200:
        return []

    return resposta.json().get(
        "results",
        []
    )
    # ============================================================
# PROCESSAMENTO DAS OFERTAS
# ============================================================


def calcular_preco_venda(custo):

    custo = numero(custo)

    return custo + (
        custo * MARGEM_PADRAO / 100
    )



def analisar_oferta(produto):


    preco = numero(
        produto.get("price")
    )


    if preco <= 0:

        return None



    return {

        "titulo":
            produto.get(
                "title",
                "Produto"
            ),


        "preco":
            preco,


        "preco_venda":
            calcular_preco_venda(
                preco
            ),


        "link":
            produto.get(
                "permalink",
                ""
            ),


        "imagem":
            produto.get(
                "thumbnail",
                ""
            )

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
# WHATSAPP
# ============================================================


def criar_mensagem_whatsapp(
        oferta
):


    texto = f"""

🔥 OFERTA ENCONTRADA 🔥


📦 {oferta['titulo']}


💰 Preço:
{formatar_preco(oferta['preco'])}


🛒 Comprar:
{oferta['link']}


⚡ Aproveite enquanto durar!

"""


    return texto.strip()




# ============================================================
# INSTAGRAM
# ============================================================


def criar_anuncio_instagram():


    return """

🔥 GRUPO VIP DE OFERTAS 🔥


Quer receber promoções todos os dias?


✅ Descontos
✅ Achadinhos
✅ Ofertas relâmpago


Entre no nosso grupo gratuito do WhatsApp.


👇 Link na bio

"""



# ============================================================
# ROTAS DO SISTEMA
# ============================================================


@app.route("/")
def inicio():


    conectado = bool(

        session.get(
            "access_token"
        )

    )


    pagina = """

    <h1>
    🤖 Robô de Ofertas
    </h1>


    <p>
    Mercado Livre conectado:
    {{status}}
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

        status="Sim"
        if conectado
        else
        "Não"

    )





@app.route(
    "/ofertas/<categoria>"
)

def rota_ofertas(
        categoria
):


    return jsonify(

        gerar_ofertas(
            categoria
        )

    )





@app.route(
    "/whatsapp/<categoria>"
)

def rota_whatsapp(
        categoria
):


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

def rota_instagram():


    return jsonify({

        "anuncio":
            criar_anuncio_instagram()

    })





# ============================================================
# EXECUÇÃO
# ============================================================

@app.route("/me")
def me():

    resposta = requests.get(
        "https://api.mercadolibre.com/users/me",
        headers=headers_api()
    )

    return resposta.text



if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                5000
            )
        )
    )
