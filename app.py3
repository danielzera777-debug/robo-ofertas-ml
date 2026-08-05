import os
import secrets
import requests

from flask import (
    Flask,
    request,
    jsonify,
    session,
    redirect,
    render_template
)

from urllib.parse import urlencode


app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    secrets.token_hex(32)
)


# ===============================
# CONFIGURAÇÕES MERCADO LIVRE
# ===============================

CLIENT_ID = os.getenv(
    "ML_CLIENT_ID"
)

CLIENT_SECRET = os.getenv(
    "ML_CLIENT_SECRET"
)

REDIRECT_URI = os.getenv(
    "ML_REDIRECT_URI"
)


API = "https://api.mercadolibre.com"



# ===============================
# BUSCA DE PRODUTOS
# ===============================

def buscar_produtos(termo, limite=20):


    url = f"{API}/sites/MLB/search"


    parametros = {

        "q": termo,

        "limit": limite,

        "sort": "relevance"

    }


    try:

        resposta = requests.get(

            url,

            params=parametros,

            timeout=15

        )


        if resposta.status_code != 200:

            return []


        dados = resposta.json()


        produtos = []


        for item in dados.get(
            "results",
            []
        ):

            preco = item.get(
                "price",
                0
            )


            produtos.append({

                "titulo":
                    item.get(
                        "title"
                    ),

                "imagem":
                    item.get(
                        "thumbnail"
                    ),

                "preco":
                    preco,

                "link":
                    item.get(
                        "permalink"
                    ),

                "revenda":
                    round(
                        float(preco) * 1.10,
                        2
                    )

            })


        return produtos


    except Exception as erro:

        print(
            "Erro busca:",
            erro
        )

        return []




# ===============================
# TELA PRINCIPAL DO APP
# ===============================


@app.route("/")
def inicio():


    return render_template(
        "index.html"
    )




# ===============================
# API DO APP
# ===============================


@app.route(
    "/api/buscar"
)

def api_buscar():


    produto = request.args.get(
        "produto"
    )


    if not produto:

        return jsonify([])


    resultado = buscar_produtos(
        produto
    )


    return jsonify(
        resultado
    )



# ===============================
# LOGIN MERCADO LIVRE
# ===============================


@app.route("/login")
def login():


    parametros = {

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

        urlencode(parametros)

    )


    return redirect(url)



# ===============================


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
