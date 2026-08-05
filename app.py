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
# CONFIGURAÇÃO
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


API_BASE = "https://api.mercadolibre.com"


# ============================================================
# CATEGORIAS
# ============================================================

CATEGORIAS = {

    "celulares": "MLB1055",

    "informatica": "MLB1648",

    "eletronicos": "MLB1000",

    "roupas": "MLB1430",

    "relogios": "MLB3937",

    "beleza": "MLB1246"

}


MARGEM_PADRAO = 10



# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================


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



def headers_api():

    headers = {

        "Accept": "application/json",

        "Content-Type": "application/json",

        "User-Agent": "Robo-Ofertas-ML/1.0"

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
# LOGIN MERCADO LIVRE PKCE
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

        "response_type": "code",

        "client_id": CLIENT_ID,

        "redirect_uri": REDIRECT_URI,

        "code_challenge": code_challenge,

        "code_challenge_method": "S256"

    }


    url = (

        "https://auth.mercadolivre.com.br/authorization?"

        +

        urlencode(params)

    )


    return redirect(url)



# ============================================================
# CALLBACK
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


    try:

        resposta = requests.post(

            f"{API_BASE}/oauth/token",

            data=dados,

            timeout=20

        )


    except Exception as erro:

        return str(erro)



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


def buscar_produtos(
        categoria,
        limite=10
):


    url = (
        f"{API_BASE}/sites/MLB/search"
    )


    params = {

        "q": categoria,

        "limit": limite

    }


    try:

        resposta = requests.get(

            url,

            params=params,

            headers=headers_api(),

            timeout=15

        )


    except requests.exceptions.RequestException as erro:


        print(
            "Erro API:",
            erro
        )


        return []



    print(
        "STATUS API:",
        resposta.status_code
    )


    if resposta.status_code != 200:

        print(
            resposta.text
        )

        return []



    return resposta.json().get(

        "results",

        []

    )
    # ============================================================
# TRATAMENTO DAS OFERTAS
# ============================================================


def calcular_venda(preco):

    preco = numero(preco)

    return preco + (
        preco * MARGEM_PADRAO / 100
    )



def analisar_produto(produto):


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

        "preco_revenda":
            calcular_venda(
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


    lista = []


    for produto in produtos:


        item = analisar_produto(
            produto
        )


        if item:

            lista.append(
                item
            )


    return lista



# ============================================================
# WHATSAPP
# ============================================================


def mensagem_whatsapp(
        produto
):


    return f"""

🔥 OFERTA ENCONTRADA 🔥


📦 {produto['titulo']}


💰 Preço:
{formatar_preco(produto['preco'])}


🛒 Link:
{produto['link']}


⚡ Aproveite!

""".strip()



# ============================================================
# INSTAGRAM
# ============================================================


def anuncio_instagram():


    return """

🔥 GRUPO VIP DE OFERTAS 🔥


Quer receber produtos com desconto?


✅ Promoções todos os dias
✅ Achadinhos
✅ Ofertas relâmpago


Entre no nosso grupo do WhatsApp.

👇 Link na bio

"""



# ============================================================
# TELAS
# ============================================================


@app.route("/")
def inicio():


    conectado = bool(

        session.get(
            "access_token"
        )

    )


    pagina = """

<h1>🤖 Robô de Ofertas</h1>


<p>
Mercado Livre conectado:
<b>{{status}}</b>
</p>


<a href="/login">
Conectar Mercado Livre
</a>


<br><br>


<a href="/ofertas/celulares">
Buscar celulares
</a>


<br><br>


<a href="/instagram">
Anúncio Instagram
</a>

"""


    return render_template_string(

        pagina,

        status=
        "Sim"
        if conectado
        else
        "Não"

    )



# ============================================================
# ROTAS DE OFERTAS
# ============================================================


@app.route(
    "/ofertas/<categoria>"
)

def ofertas(
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

def whatsapp(
        categoria
):


    ofertas = gerar_ofertas(
        categoria
    )


    mensagens = []


    for produto in ofertas:


        mensagens.append(

            mensagem_whatsapp(
                produto
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
            anuncio_instagram()

    })



# ============================================================
# TESTE DE CONEXÃO MERCADO LIVRE
# ============================================================


@app.route("/me")
def me():


    try:

        resposta = requests.get(

            f"{API_BASE}/users/me",

            headers=headers_api(),

            timeout=15

        )


        return resposta.text


    except Exception as erro:

        return str(erro)



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

        )

    )
