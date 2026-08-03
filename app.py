
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "Robô Ofertas ML está online!"

@app.route("/oferta")
def oferta():
    return jsonify({
        "produto": "Oferta de teste",
        "preco": "R$ 99,90",
        "desconto": "30%",
        "link": "https://mercadolivre.com.br"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
