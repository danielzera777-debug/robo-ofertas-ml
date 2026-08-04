import os
import secrets
import hashlib
import base64
import requests
import html
import io

from urllib.parse import urlencode, quote
from flask import Flask, request, session, send_file

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except Exception:
    PIL_OK = False

app = Flask(__name__)

# ============================================================
# CONFIGURAÇÕES
# ============================================================

CLIENT_ID = os.getenv("ML_CLIENT_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ML_REDIRECT_URI")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))

app.secret_key = SECRET_KEY
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

API_BASE = "https://api.mercadolibre.com"
SITE_ID = "MLB"

# ============================================================
# CATEGORIAS / DOMÍNIOS
# O robô usa o catálogo do ML para descobrir os produtos.
# ============================================================

CATEGORIAS = {
    "celulares": {
        "nome": "📱 Celulares",
        "termos": ["iPhone", "Samsung Galaxy", "Motorola"],
        "domain": "MLB-CELLPHONES",
    },
    "roupas": {
        "nome": "👕 Roupas",
        "termos": ["camiseta masculina", "calça masculina", "vestido feminino"],
        "domain": None,
    },
    "relogios": {
        "nome": "⌚ Relógios",
        "termos": ["relógio masculino", "relógio feminino", "smartwatch"],
        "domain": None,
    },
    "tenis": {
        "nome": "👟 Tênis",
        "termos": ["tênis masculino", "tênis feminino", "tênis corrida"],
        "domain": None,
    },
    "eletronicos": {
        "nome": "🎧 Eletrônicos",
        "termos": ["fone bluetooth", "caixa de som bluetooth", "smartwatch"],
        "domain": None,
    },
    "casa": {
        "nome": "🏠 Casa",
        "termos": ["air fryer", "liquidificador", "jogo de panelas"],
        "domain": None,
    },
    "beleza": {
        "nome": "💄 Beleza",
        "termos": ["perfume feminino", "perfume masculino", "secador de cabelo"],
        "domain": None,
    },
}

MARGEM_PADRAO = 10
LUCRO_MINIMO_PADRAO = 20
RESULTADOS_POR_TERMO = 8
ITENS_POR_PRODUTO = 20
MAX_ANUNCIOS_ANALISADOS = 80


# ============================================================
# FUNÇÕES BÁSICAS
# ============================================================

def escapar(valor):
    return html.escape(str(valor or ""))


def numero(valor):
    try:
        return float(valor)
    except Exception:
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
    except Exception:
        return "R$ 0,00"


def headers_api():
    headers = {
        "Accept": "application/json",
        "User-Agent": "Robo-Ofertas-ML/2.0",
    }

    token = session.get("access_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    return headers


def requisicao_get(url, params=None):
    try:
        return requests.get(
            url,
            params=params,
            headers=headers_api(),
            timeout=30,
        )
    except requests.RequestException as erro:
        print("ERRO REQUEST:", erro)
        return None


# ============================================================
# DOMÍNIO / CATEGORIA
# ============================================================

def descobrir_categoria(termo):
    """
    O ML recomenda o domain discovery para prever domínio/categoria
    a partir do título do produto.
    """
    response = requisicao_get(
        f"{API_BASE}/sites/{SITE_ID}/domain_discovery/search",
        {
            "q": termo,
            "limit": 1,
        },
    )

    if response is None or response.status_code != 200:
        return None

    try:
        data = response.json()
        if not data:
            return None

        primeiro = data[0]
        return {
            "domain_id": primeiro.get("domain_id"),
            "category_id": primeiro.get("category_id"),
            "domain_name": primeiro.get("domain_name"),
            "category_name": primeiro.get("category_name"),
        }
    except Exception:
        return None


# ============================================================
# CATÁLOGO
# ============================================================

def buscar_produtos_catalogo(termo, domain_id=None, offset=0, limit=10):
    params = {
        "status": "active",
        "site_id": SITE_ID,
        "q": termo,
        "offset": offset,
        "limit": limit,
    }

    if domain_id:
        params["domain_id"] = domain_id

    return requisicao_get(
        f"{API_BASE}/products/search",
        params,
    )


def buscar_publicacoes(product_id):
    response = requisicao_get(
        f"{API_BASE}/products/{product_id}/items",
        {
            "offset": 0,
            "limit": ITENS_POR_PRODUTO,
        },
    )

    if response is None or response.status_code != 200:
        return []

    try:
        return response.json().get("results", [])
    except Exception:
        return []


def buscar_detalhes_itens(item_ids):
    if not item_ids:
        return []

    resultados = []
    item_ids = list(dict.fromkeys(str(x) for x in item_ids if x))

    for inicio in range(0, len(item_ids), 20):
        bloco = item_ids[inicio:inicio + 20]

        response = requisicao_get(
            f"{API_BASE}/items",
            {"ids": ",".join(bloco)},
        )

        if response is None or response.status_code != 200:
            continue

        try:
            data = response.json()
        except Exception:
            continue

        for resultado in data:
            if resultado.get("code") != 200:
                continue

            body = resultado.get("body")
            if body:
                resultados.append(body)

    return resultados


def buscar_vendedores(seller_ids):
    vendedores = {}

    seller_ids = list(
        dict.fromkeys(
            str(x) for x in seller_ids if x
        )
    )

    # Não precisamos consultar todos os vendedores.
    # O nickname pode vir do anúncio; se não vier, usamos o ID.
    for seller_id in seller_ids[:30]:
        response = requisicao_get(
            f"{API_BASE}/users/{seller_id}"
        )

        if response is None or response.status_code != 200:
            continue

        try:
            data = response.json()
            vendedores[seller_id] = data.get(
                "nickname",
                f"Vendedor {seller_id}",
            )
        except Exception:
            pass

    return vendedores


# ============================================================
# RANKING
# ============================================================

def calcular_score(anuncio):
    """
    Score para colocar primeiro:
    - mais vendidos = melhor
    - preço mais baixo = melhor
    - estoque disponível = bônus
    """
    vendidos = numero(anuncio.get("sold_quantity"))
    preco = numero(anuncio.get("price"))
    estoque = numero(anuncio.get("available_quantity"))

    # Logaritmo evita que um único anúncio com milhares de vendas
    # domine todos os demais.
    import math

    score_vendas = math.log1p(max(vendidos, 0)) * 70
    score_preco = 0

    if preco > 0:
        score_preco = 100000 / preco

    score_estoque = min(estoque, 50) * 0.15

    return score_vendas + score_preco + score_estoque


def preparar_anuncio(detalhe, produto, margem):
    if not detalhe:
        return None

    item_id = detalhe.get("id")
    custo = numero(detalhe.get("price"))

    if not item_id or custo <= 0:
        return None

    preco_venda = custo * (1 + margem / 100)
    lucro = preco_venda - custo

    imagens = detalhe.get("pictures") or []
    imagem = ""

    if imagens:
        imagem = (
            imagens[0].get("secure_url")
            or imagens[0].get("url")
            or ""
        )

    if not imagem:
        imagem = detalhe.get("thumbnail", "")

    permalink = detalhe.get("permalink") or (
        f"https://www.mercadolivre.com.br/{item_id}"
    )

    return {
        "product_id": produto.get("id", ""),
        "product_name": produto.get("name", "Produto"),
        "domain_id": produto.get("domain_id", ""),
        "item_id": item_id,
        "title": detalhe.get(
            "title",
            produto.get("name", "Produto"),
        ),
        "price": custo,
        "preco_venda": preco_venda,
        "lucro": lucro,
        "seller_id": detalhe.get("seller_id"),
        "seller_nickname": detalhe.get("seller_nickname"),
        "condition": detalhe.get(
            "condition",
            "Não informado",
        ),
        "category_id": detalhe.get("category_id", ""),
        "sold_quantity": detalhe.get(
            "sold_quantity",
            0,
        ),
        "available_quantity": detalhe.get(
            "available_quantity",
            0,
        ),
        "permalink": permalink,
        "thumbnail": imagem,
        "pictures": imagens,
    }


def coletar_oportunidades(
    termos,
    margem,
    lucro_minimo,
    domain_forcado=None,
):
    """
    Procura vários produtos, pega suas publicações e depois
    calcula o ranking por vendas + preço.
    """
    anuncios = []
    produtos_vistos = set()
    itens_vistos = set()

    for termo in termos:
        domain = domain_forcado

        if not domain:
            descoberta = descobrir_categoria(termo)
            if descoberta:
                domain = descoberta.get("domain_id")

        response = buscar_produtos_catalogo(
            termo,
            domain_id=domain,
            offset=0,
            limit=RESULTADOS_POR_TERMO,
        )

        if response is None or response.status_code != 200:
            print(
                "Falha catálogo:",
                termo,
                getattr(response, "status_code", None),
            )
            continue

        try:
            produtos = response.json().get("results", [])
        except Exception:
            continue

        for produto in produtos:
            product_id = produto.get("id")

            if not product_id or product_id in produtos_vistos:
                continue

            produtos_vistos.add(product_id)

            itens = buscar_publicacoes(product_id)

            for item in itens:
                item_id = item.get("item_id") or item.get("id")

                if not item_id or item_id in itens_vistos:
                    continue

                itens_vistos.add(item_id)

                # O endpoint de publicações pode retornar apenas
                # referências; usamos o multiget para detalhes reais.
                anuncios.append({
                    "product_id": product_id,
                    "product": produto,
                    "item_id": item_id,
                })

                if len(anuncios) >= MAX_ANUNCIOS_ANALISADOS:
                    break

            if len(anuncios) >= MAX_ANUNCIOS_ANALISADOS:
                break

        if len(anuncios) >= MAX_ANUNCIOS_ANALISADOS:
            break

    if not anuncios:
        return []

    ids = [x["item_id"] for x in anuncios]
    detalhes = buscar_detalhes_itens(ids)
    detalhe_map = {x.get("id"): x for x in detalhes if x.get("id")}

    finais = []

    for base in anuncios:
        detalhe = detalhe_map.get(base["item_id"])
        if not detalhe:
            continue

        anuncio = preparar_anuncio(
            detalhe,
            base["product"],
            margem,
        )

        if not anuncio:
            continue

        if anuncio["lucro"] < lucro_minimo:
            continue

        anuncio["score"] = calcular_score(anuncio)
        finais.append(anuncio)

    # Um produto pode aparecer com vários vendedores.
    # Mantemos as melhores oportunidades sem duplicar o mesmo item.
    unicos = {}
    for anuncio in finais:
        item_id = anuncio["item_id"]

        atual = unicos.get(item_id)
        if not atual or anuncio["score"] > atual["score"]:
            unicos[item_id] = anuncio

    finais = list(unicos.values())

    # Primeiro: vendas e preço, via score.
    finais.sort(
        key=lambda x: (
            x.get("score", 0),
            x.get("sold_quantity", 0),
            -x.get("price", 0),
        ),
        reverse=True,
    )

    return finais


# ============================================================
# IMAGEM DA OFERTA
# ============================================================

def baixar_imagem(url):
    if not url:
        return None

    try:
        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": "Robo-Ofertas-ML/2.0",
            },
        )

        if response.status_code != 200:
            return None

        return Image.open(
            io.BytesIO(response.content)
        ).convert("RGB")
    except Exception as erro:
        print("ERRO IMAGEM:", erro)
        return None


def fonte_tamanho(tamanho, negrito=False):
    if not PIL_OK:
        return None

    caminhos = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if negrito
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if negrito
        else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]

    for caminho in caminhos:
        if os.path.exists(caminho):
            return ImageFont.truetype(caminho, tamanho)

    return ImageFont.load_default()


def gerar_imagem_oferta(anuncio):
    """
    Cria uma arte PNG simples com a foto real do anúncio.
    A imagem é gerada no momento em que a rota é acessada.
    """
    if not PIL_OK:
        return None

    largura, altura = 1080, 1350

    canvas = Image.new(
        "RGB",
        (largura, altura),
        "white",
    )

    draw = ImageDraw.Draw(canvas)

    fonte_titulo = fonte_tamanho(48, True)
    fonte_preco = fonte_tamanho(72, True)
    fonte_normal = fonte_tamanho(36, False)
    fonte_pequena = fonte_tamanho(28, False)

    # Cabeçalho
    draw.rectangle(
        (0, 0, largura, 180),
        fill="#3483fa",
    )

    draw.text(
        (50, 45),
        "🔥 OFERTA ESPECIAL",
        fill="white",
        font=fonte_titulo,
    )

    # Foto
    imagem = baixar_imagem(
        anuncio.get("thumbnail", "")
    )

    if imagem:
        imagem.thumbnail((850, 650))

        x = (largura - imagem.width) // 2
        y = 220 + (650 - imagem.height) // 2

        canvas.paste(
            imagem,
            (x, y),
        )
    else:
        draw.text(
            (270, 480),
            "📦 Produto",
            fill="#555555",
            font=fonte_titulo,
        )

    titulo = anuncio.get(
        "title",
        "Produto",
    )

    # Quebra simples do título
    if len(titulo) > 55:
        titulo = titulo[:52] + "..."

    draw.text(
        (50, 900),
        titulo,
        fill="#222222",
        font=fonte_normal,
    )

    draw.text(
        (50, 975),
        "💰 Preço da oferta",
        fill="#555555",
        font=fonte_normal,
    )

    draw.text(
        (50, 1020),
        formatar_preco(
            anuncio.get("preco_venda", 0)
        ),
        fill="#008000",
        font=fonte_preco,
    )

    vendidos = anuncio.get(
        "sold_quantity",
        0,
    )

    draw.text(
        (50, 1135),
        f"🔥 Já vendidos: {vendidos}",
        fill="#222222",
        font=fonte_normal,
    )

    draw.text(
        (50, 1200),
        "🛒 Compre pelo link abaixo",
        fill="#555555",
        font=fonte_pequena,
    )

    # Link curto dentro da arte
    draw.text(
        (50, 1240),
        anuncio.get("permalink", "")[:75],
        fill="#3483fa",
        font=fonte_pequena,
    )

    output = io.BytesIO()

    canvas.save(
        output,
        format="PNG",
        optimize=True,
    )

    output.seek(0)
    return output


# ============================================================
# LOGIN
# ============================================================

@app.route("/")
def home():
    code = request.args.get("code")
    state = request.args.get("state")

    if not CLIENT_ID:
        return "ML_CLIENT_ID não configurado.", 500

    if not CLIENT_SECRET:
        return "ML_CLIENT_SECRET não configurado.", 500

    if not REDIRECT_URI:
        return "ML_REDIRECT_URI não configurado.", 500

    if code:
        saved_state = session.get("state")

        if not saved_state:
            return """
            <h2>❌ Sessão expirada.</h2>
            <a href="/">Voltar</a>
            """, 400

        if state != saved_state:
            return """
            <h2>❌ State inválido.</h2>
            <a href="/">Voltar</a>
            """, 400

        code_verifier = session.get("code_verifier")

        if not code_verifier:
            return """
            <h2>❌ Code verifier não encontrado.</h2>
            """, 400

        try:
            response = requests.post(
                f"{API_BASE}/oauth/token",
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
        except requests.RequestException as erro:
            return f"""
            <h1>❌ Erro de conexão</h1>
            <pre>{escapar(erro)}</pre>
            <a href="/">Voltar</a>
            """, 500

        if response.status_code != 200:
            return f"""
            <h1>❌ Erro ao obter token</h1>
            <p>Status: {response.status_code}</p>
            <pre>{escapar(response.text)}</pre>
            <a href="/">Voltar</a>
            """, 400

        try:
            token_data = response.json()
        except Exception:
            return "<h2>❌ Resposta inválida.</h2>", 400

        access_token = token_data.get("access_token")

        if not access_token:
            return "<h2>❌ Access Token não recebido.</h2>", 400

        session["access_token"] = access_token
        session["refresh_token"] = token_data.get("refresh_token")

        session.pop("code_verifier", None)
        session.pop("state", None)

        user_response = requisicao_get(
            f"{API_BASE}/users/me"
        )

        if user_response is None:
            return "<h1>❌ Erro ao consultar usuário.</h1>", 500

        if user_response.status_code != 200:
            return f"""
            <h1>❌ Erro ao consultar conta.</h1>
            <pre>{escapar(user_response.text)}</pre>
            <a href="/">Voltar</a>
            """, 400

        user_data = user_response.json()

        nickname = user_data.get(
            "nickname",
            "usuário",
        )

        user_id = user_data.get(
            "id",
            "",
        )

        session["user_id"] = user_id

        return pagina_principal(
            nickname,
            user_id,
        )

    # PKCE
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
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
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
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Robô Ofertas ML</title>
    </head>
    <body style="font-family:Arial;background:#f5f5f5;padding:30px;text-align:center">
    <h1>🤖 Robô Ofertas ML</h1>
    <p>Conecte sua conta do Mercado Livre</p>
    <a href="{escapar(auth_url)}">
    <button style="padding:15px 25px;font-size:18px;border:0;border-radius:8px;background:#3483fa;color:white">
    🔐 Conectar Mercado Livre
    </button>
    </a>
    </body>
    </html>
    """


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

def pagina_principal(nickname, user_id):
    botoes = ""

    for chave, info in CATEGORIAS.items():
        botoes += f"""
        <a class="categoria" href="/melhores?categoria={quote(chave)}">
            {escapar(info["nome"])}
        </a>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Robô Ofertas ML</title>
    <style>
    body {{
        font-family:Arial;
        background:#f5f5f5;
        margin:0;
        padding:15px;
    }}
    .container {{
        max-width:850px;
        margin:auto;
        background:white;
        padding:22px;
        border-radius:15px;
    }}
    input {{
        width:100%;
        box-sizing:border-box;
        padding:14px;
        font-size:17px;
        border:1px solid #ccc;
        border-radius:8px;
        margin:7px 0 12px;
    }}
    button {{
        width:100%;
        padding:15px;
        font-size:17px;
        border:0;
        border-radius:8px;
        background:#3483fa;
        color:white;
    }}
    .categorias {{
        display:grid;
        grid-template-columns:repeat(2,1fr);
        gap:10px;
        margin-top:15px;
    }}
    .categoria {{
        display:block;
        padding:15px;
        background:#f2f5f9;
        border-radius:10px;
        text-decoration:none;
        color:#222;
        text-align:center;
        font-weight:bold;
    }}
    .info {{
        background:#f5f5f5;
        padding:15px;
        border-radius:10px;
        margin-top:15px;
    }}
    </style>
    </head>
    <body>
    <div class="container">
    <h1>🤖 Robô Ofertas ML</h1>
    <p>✅ Mercado Livre conectado!</p>
    <p>Usuário: <strong>{escapar(nickname)}</strong></p>
    <p>ID: <strong>{escapar(user_id)}</strong></p>

    <hr>

    <h2>🔥 Encontrar oportunidades</h2>

    <p>
    O robô procura produtos, analisa preço e vendas e coloca
    as melhores oportunidades primeiro.
    </p>

    <form action="/buscar" method="get">
        <input
            type="text"
            name="q"
            placeholder="Ex: iPhone 13, relógio, tênis..."
            required
        >

        <label>📈 Margem de revenda (%)</label>
        <input
            type="number"
            name="margem"
            value="{MARGEM_PADRAO}"
            min="0"
            max="100"
            step="1"
        >

        <label>💰 Lucro mínimo</label>
        <input
            type="number"
            name="lucro_minimo"
            value="{LUCRO_MINIMO_PADRAO}"
            min="0"
            step="1"
        >

        <button type="submit">
            🔎 Buscar produto
        </button>
    </form>

    <div class="info">
        <h3>🚀 Busca automática</h3>
        <p>Escolha uma categoria:</p>
        <div class="categorias">
            {botoes}
        </div>
    </div>

    <div class="info">
        <strong>📲 WhatsApp</strong>
        <p>
        Cada oportunidade terá uma oferta pronta com imagem,
        preço, lucro, vendas e link de compra.
        </p>
        <p>
        O botão do WhatsApp abre a mensagem já preenchida.
        O envio automático de imagem exige a API oficial
        do WhatsApp Business.
        </p>
    </div>

    <br>
    <a href="/diagnostico">🧪 Diagnóstico</a>
    <br><br>
    <a href="/logout">🔓 Desconectar</a>
    </div>
    </body>
    </html>
    """


# ============================================================
# BUSCA MANUAL
# ============================================================

@app.route("/buscar")
def buscar():
    termo = request.args.get("q", "").strip()

    if not termo:
        return """
        <h2>❌ Digite um produto.</h2>
        <a href="/">← Voltar</a>
        """, 400

    if not session.get("access_token"):
        return """
        <h1>❌ Mercado Livre não conectado</h1>
        <a href="/">🔐 Conectar</a>
        """, 401

    try:
        margem = float(
            request.args.get(
                "margem",
                MARGEM_PADRAO,
            )
        )
    except Exception:
        margem = MARGEM_PADRAO

    try:
        lucro_minimo = float(
            request.args.get(
                "lucro_minimo",
                LUCRO_MINIMO_PADRAO,
            )
        )
    except Exception:
        lucro_minimo = LUCRO_MINIMO_PADRAO

    margem = max(0, min(margem, 100))
    lucro_minimo = max(0, lucro_minimo)

    anuncios = coletar_oportunidades(
        [termo],
        margem,
        lucro_minimo,
    )

    return render_resultados(
        anuncios,
        titulo=f"🔎 {termo}",
        margem=margem,
        lucro_minimo=lucro_minimo,
    )


# ============================================================
# MELHORES PRODUTOS POR CATEGORIA
# ============================================================

@app.route("/melhores")
def melhores():
    if not session.get("access_token"):
        return """
        <h1>❌ Mercado Livre não conectado</h1>
        <a href="/">🔐 Conectar</a>
        """, 401

    chave = request.args.get("categoria", "celulares")

    info = CATEGORIAS.get(chave)

    if not info:
        return """
        <h2>❌ Categoria não encontrada.</h2>
        <a href="/">← Voltar</a>
        """, 404

    try:
        margem = float(
            request.args.get(
                "margem",
                MARGEM_PADRAO,
            )
        )
    except Exception:
        margem = MARGEM_PADRAO

    try:
        lucro_minimo = float(
            request.args.get(
                "lucro_minimo",
                LUCRO_MINIMO_PADRAO,
            )
        )
    except Exception:
        lucro_minimo = LUCRO_MINIMO_PADRAO

    margem = max(0, min(margem, 100))
    lucro_minimo = max(0, lucro_minimo)

    anuncios = coletar_oportunidades(
        info["termos"],
        margem,
        lucro_minimo,
        info.get("domain"),
    )

    return render_resultados(
        anuncios,
        titulo=f'{info["nome"]} — 🔥 melhores oportunidades',
        margem=margem,
        lucro_minimo=lucro_minimo,
    )


# ============================================================
# RESULTADOS
# ============================================================

def render_resultados(
    anuncios,
    titulo,
    margem,
    lucro_minimo,
):
    seller_ids = [
        x.get("seller_id")
        for x in anuncios
    ]

    vendedores = buscar_vendedores(
        seller_ids
    )

    cards = ""

    for indice, anuncio in enumerate(anuncios[:30]):
        item_id = anuncio["item_id"]
        title = anuncio["title"]
        custo = anuncio["price"]
        venda = anuncio["preco_venda"]
        lucro = anuncio["lucro"]
        vendidos = anuncio["sold_quantity"]
        estoque = anuncio["available_quantity"]
        imagem = anuncio["thumbnail"]
        link = anuncio["permalink"]

        seller_id = anuncio.get("seller_id")
        seller_nome = (
            anuncio.get("seller_nickname")
            or vendedores.get(
                str(seller_id),
                f"Vendedor {seller_id}",
            )
        )

        mensagem = (
            f"🔥 OFERTA ESPECIAL\\n\\n"
            f"📦 {title}\\n\\n"
            f"💰 Por apenas: {formatar_preco(venda)}\\n\\n"
            f"🚚 Compra pelo Mercado Livre\\n"
            f"🛒 {link}"
        )

        whatsapp_url = (
            "https://wa.me/?text="
            + quote(mensagem)
        )

        imagem_url = (
            f"/oferta/{quote(item_id)}"
        )

        # O link para a arte é gerado pelo próprio robô.
        cards += f"""
        <div class="card">

        {"<div class='melhor'>🏆 MELHOR OPORTUNIDADE</div>" if indice == 0 else ""}

        <img
            class="produto"
            src="{escapar(imagem)}"
            alt="{escapar(title)}"
            loading="lazy"
            onerror="this.style.display='none'"
        >

        <h2>{escapar(title)}</h2>

        <div class="preco_compra">
            💵 Preço encontrado:
            <strong>{formatar_preco(custo)}</strong>
        </div>

        <div class="preco_venda">
            🏷️ Preço sugerido:
            {formatar_preco(venda)}
        </div>

        <div class="lucro">
            💰 Lucro estimado:
            {formatar_preco(lucro)}
        </div>

        <div class="dados">
            🔥 Vendidos:
            <strong>{escapar(vendidos)}</strong>
        </div>

        <div class="dados">
            📦 Estoque informado:
            <strong>{escapar(estoque)}</strong>
        </div>

        <div class="dados">
            👤 Vendedor:
            <strong>{escapar(seller_nome)}</strong>
        </div>

        <div class="dados">
            🆔 Anúncio:
            <strong>{escapar(item_id)}</strong>
        </div>

        <a class="botao" href="{escapar(link)}" target="_blank">
            🛒 Ver anúncio
        </a>

        <a class="whatsapp" href="{escapar(whatsapp_url)}" target="_blank">
            📲 Enviar oferta no WhatsApp
        </a>

        <a class="arte" href="{escapar(imagem_url)}" target="_blank">
            🖼️ Abrir imagem da oferta
        </a>

        </div>
        """

    if not cards:
        cards = """
        <div class="nenhum">
        <h2>😕 Nenhuma oportunidade encontrada</h2>
        <p>
        Tente diminuir o lucro mínimo ou usar outra categoria.
        </p>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Oportunidades</title>
    <style>
    body {{
        font-family:Arial;
        background:#f5f5f5;
        margin:0;
        padding:15px;
    }}
    .container {{
        max-width:950px;
        margin:auto;
    }}
    .top {{
        background:white;
        padding:20px;
        border-radius:12px;
        margin-bottom:15px;
    }}
    .card {{
        background:white;
        padding:18px;
        border-radius:12px;
        margin-bottom:15px;
        box-shadow:0 2px 8px rgba(0,0,0,.08);
    }}
    .produto {{
        width:100%;
        max-width:300px;
        max-height:300px;
        object-fit:contain;
        display:block;
        margin:0 auto 15px;
    }}
    .preco_compra {{
        font-size:18px;
        color:#555;
        margin:8px 0;
    }}
    .preco_venda {{
        font-size:27px;
        font-weight:bold;
        color:#008000;
        margin:12px 0;
    }}
    .lucro {{
        background:#d4edda;
        color:#155724;
        padding:13px;
        border-radius:8px;
        font-size:21px;
        font-weight:bold;
        margin:10px 0;
    }}
    .dados {{
        margin:8px 0;
        color:#444;
    }}
    .melhor {{
        background:#fff3cd;
        padding:10px;
        border-radius:8px;
        display:inline-block;
        font-weight:bold;
        margin-bottom:10px;
    }}
    .botao,.whatsapp,.arte {{
        display:block;
        color:white;
        padding:14px;
        border-radius:8px;
        text-decoration:none;
        text-align:center;
        margin-top:10px;
    }}
    .botao {{ background:#3483fa; }}
    .whatsapp {{ background:#25D366; }}
    .arte {{ background:#673ab7; }}
    .nenhum {{
        background:white;
        padding:20px;
        border-radius:12px;
    }}
    </style>
    </head>
    <body>
    <div class="container">

    <div class="top">
        <h1>{escapar(titulo)}</h1>
        <p>📊 Resultados analisados: <strong>{len(anuncios)}</strong></p>
        <p>📈 Margem: <strong>{margem:.0f}%</strong></p>
        <p>💰 Lucro mínimo: <strong>{formatar_preco(lucro_minimo)}</strong></p>
        <p>
        🏆 O ranking considera vendas, preço e disponibilidade
        informada pelo Mercado Livre.
        </p>
    </div>

    {cards}

    <br>
    <a href="/">← Nova pesquisa</a>
    <br><br>
    <a href="/diagnostico">🧪 Diagnóstico</a>

    </div>
    </body>
    </html>
    """


# ============================================================
# GERAR ARTE
# ============================================================

@app.route("/oferta/<item_id>")
def oferta(item_id):
    if not session.get("access_token"):
        return "Mercado Livre não conectado.", 401

    detalhes = buscar_detalhes_itens([item_id])

    if not detalhes:
        return """
        <h2>❌ Anúncio não encontrado.</h2>
        <a href="/">Voltar</a>
        """, 404

    detalhe = detalhes[0]

    # Para gerar a arte, usamos a margem padrão.
    anuncio = preparar_anuncio(
        detalhe,
        {
            "id": detalhe.get("catalog_product_id", ""),
            "name": detalhe.get("title", "Produto"),
            "domain_id": "",
        },
        MARGEM_PADRAO,
    )

    if not anuncio:
        return """
        <h2>❌ Não foi possível montar a oferta.</h2>
        """, 400

    imagem = gerar_imagem_oferta(anuncio)

    if imagem is None:
        return """
        <h2>❌ Biblioteca de imagem não instalada.</h2>
        <p>Adicione Pillow ao requirements.txt.</p>
        """, 500

    return send_file(
        imagem,
        mimetype="image/png",
        download_name=f"oferta-{item_id}.png",
    )


# ============================================================
# DIAGNÓSTICO
# ============================================================

@app.route("/diagnostico")
def diagnostico():
    if not session.get("access_token"):
        return """
        <h1>❌ Conta não conectada</h1>
        <a href="/">← Voltar</a>
        """, 401

    testes = [
        (
            "1️⃣ /users/me",
            f"{API_BASE}/users/me",
            None,
        ),
        (
            "2️⃣ Busca de catálogo",
            f"{API_BASE}/products/search",
            {
                "status": "active",
                "site_id": "MLB",
                "q": "iPhone 13",
                "domain_id": "MLB-CELLPHONES",
                "limit": 5,
            },
        ),
        (
            "3️⃣ Domain Discovery",
            f"{API_BASE}/sites/MLB/domain_discovery/search",
            {
                "q": "relógio masculino",
                "limit": 1,
            },
        ),
    ]

    blocos = []

    for nome, url, params in testes:
        response = requisicao_get(
            url,
            params,
        )

        if response is None:
            blocos.append(f"""
            <div style="background:#f8d7da;padding:15px;margin-bottom:15px;border-radius:10px">
            <h2>{escapar(nome)}</h2>
            <p>❌ Falha de conexão</p>
            </div>
            """)
            continue

        texto = response.text

        if len(texto) > 10000:
            texto = texto[:10000] + "\n\n... cortado ..."

        blocos.append(f"""
        <div style="background:#f8f8f8;padding:15px;margin-bottom:15px;border-radius:10px;overflow:auto">
        <h2>{escapar(nome)}</h2>
        <p>Status: <strong>{response.status_code}</strong></p>
        <pre>{escapar(texto)}</pre>
        </div>
        """)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Diagnóstico</title>
    </head>
    <body style="font-family:Arial;background:#f5f5f5;padding:20px">
    <div style="max-width:950px;margin:auto;background:white;padding:20px;border-radius:12px">
    <h1>🧪 Diagnóstico Mercado Livre</h1>
    {"".join(blocos)}
    <a href="/">← Voltar</a>
    </div>
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
    <h1>🔓 Desconectado</h1>
    <p>Sessão encerrada.</p>
    <a href="/">🔐 Conectar novamente</a>
    """


# ============================================================
# TESTE CONFIG
# ============================================================

@app.route("/teste-config")
def teste_config():
    return f"""
    <h1>🧪 Configuração</h1>

    <p>CLIENT_ID:
    <strong>{"OK" if CLIENT_ID else "FALTANDO"}</strong></p>

    <p>CLIENT_SECRET:
    <strong>{"OK" if CLIENT_SECRET else "FALTANDO"}</strong></p>

    <p>REDIRECT_URI:
    <strong>
    {escapar(REDIRECT_URI) if REDIRECT_URI else "FALTANDO"}
    </strong></p>

    <p>SECRET_KEY:
    <strong>{"OK" if SECRET_KEY else "FALTANDO"}</strong></p>

    <p>Pillow:
    <strong>{"OK" if PIL_OK else "FALTANDO"}</strong></p>

    <hr>
    <a href="/">← Voltar</a>
    """


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 10000)),
    )
