import os
import time
import secrets
import hashlib
import base64
import logging
from urllib.parse import urlencode, quote

import requests
from flask import Flask, request, session, redirect, jsonify, render_template_string

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("robo-ofertas")

CLIENT_ID = os.getenv("ML_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("ML_REDIRECT_URI", "")
API_BASE = "https://api.mercadolibre.com"
AUTH_URL = "https://auth.mercadolivre.com.br/authorization"
SITE_ID = "MLB"
VERSION = "7.0"

ACCESS_TOKEN = None
REFRESH_TOKEN = None
TOKEN_EXPIRES_AT = 0

NICHOS = {
    "suplementos": {
        "nome": "🥤 Suplementos",
        "termos": [
            "whey protein", "whey", "creatina", "creatina monohidratada",
            "pre treino", "pré treino", "hipercalorico", "hipercalórico",
            "bcaa", "glutamina", "multivitaminico", "multivitamínico",
            "barra proteica", "proteina", "proteína", "shaker"
        ],
    },
    "fitness_feminino": {
        "nome": "👩 Fitness Feminino",
        "termos": [
            "legging feminina academia", "top fitness feminino",
            "conjunto fitness feminino", "conjunto academia feminino",
            "short fitness feminino", "short feminino academia",
            "cropped fitness feminino", "macacao fitness feminino",
            "macacão fitness feminino", "calca fitness feminina",
            "calça fitness feminina", "camiseta fitness feminina"
        ],
    },
    "fitness_masculino": {
        "nome": "👨 Fitness Masculino",
        "termos": [
            "camiseta dry fit masculina", "camiseta academia masculina",
            "regata academia masculina", "bermuda fitness masculina",
            "short academia masculino", "calca fitness masculina",
            "calça fitness masculina", "conjunto fitness masculino",
            "camiseta compressao masculina", "camiseta compressão masculina",
            "blusa academia masculina", "jaqueta fitness masculina"
        ],
    },
}

def num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default

def integer(v, default=20):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default

def money(v):
    return f"R$ {num(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def token():
    global ACCESS_TOKEN
    if ACCESS_TOKEN:
        return ACCESS_TOKEN
    ACCESS_TOKEN = session.get("access_token")
    return ACCESS_TOKEN

def save_tokens(data):
    global ACCESS_TOKEN, REFRESH_TOKEN, TOKEN_EXPIRES_AT
    ACCESS_TOKEN = data.get("access_token")
    REFRESH_TOKEN = data.get("refresh_token") or session.get("refresh_token")
    expires = integer(data.get("expires_in", 21600), 21600)
    TOKEN_EXPIRES_AT = time.time() + max(60, expires - 120)
    if ACCESS_TOKEN:
        session["access_token"] = ACCESS_TOKEN
    if REFRESH_TOKEN:
        session["refresh_token"] = REFRESH_TOKEN
    session["token_expires_at"] = TOKEN_EXPIRES_AT
    session.modified = True

def refresh_token():
    refresh = REFRESH_TOKEN or session.get("refresh_token")
    if not refresh or not CLIENT_ID or not CLIENT_SECRET:
        return False
    try:
        r = requests.post(
            f"{API_BASE}/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": refresh,
            },
            timeout=25,
        )
    except requests.RequestException as e:
        logger.error("refresh: %s", e)
        return False
    if r.status_code != 200:
        logger.warning("refresh recusado %s: %s", r.status_code, r.text[:500])
        return False
    try:
        save_tokens(r.json())
        return True
    except Exception:
        return False

def valid_token():
    t = token()
    if not t:
        return None
    if TOKEN_EXPIRES_AT and time.time() >= TOKEN_EXPIRES_AT:
        if not refresh_token():
            return None
    return token()

def api_headers(auth=True):
    h = {"Accept": "application/json", "User-Agent": "Robo-Ofertas-ML/7.0"}
    if auth and valid_token():
        h["Authorization"] = f"Bearer {valid_token()}"
    return h

def oauth_login():
    if not CLIENT_ID or not REDIRECT_URI:
        return None, "Configure ML_CLIENT_ID e ML_REDIRECT_URI no Render."
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    session["oauth_state"] = state
    session["code_verifier"] = verifier
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return AUTH_URL + "?" + urlencode(params), None

def classify(title, fallback=None):
    s = (title or "").lower()
    supplement = [
        "whey", "creatina", "pré treino", "pre treino", "hipercalórico",
        "hipercalorico", "bcaa", "glutamina", "multivitamínico",
        "multivitaminico", "proteína", "proteina", "barra proteica"
    ]
    female = [
        "legging feminina", "top fitness", "conjunto fitness feminino",
        "conjunto academia feminino", "short feminino", "cropped fitness",
        "macacão fitness", "macacao fitness", "calça fitness feminina",
        "calca fitness feminina"
    ]
    male = [
        "camiseta masculina", "dry fit masculina", "regata masculina",
        "bermuda masculina", "short masculino", "calça fitness masculina",
        "calca fitness masculina", "conjunto fitness masculino",
        "compressão masculina", "compressao masculina"
    ]
    if any(x in s for x in supplement):
        return "suplementos"
    if any(x in s for x in female):
        return "fitness_feminino"
    if any(x in s for x in male):
        return "fitness_masculino"
    return fallback

def whatsapp_text(title, price, link, category):
    if category == "suplementos":
        head = "🥤 OFERTA DE SUPLEMENTO"
        icon = "💪"
    elif category == "fitness_feminino":
        head = "👩 OFERTA FITNESS FEMININA"
        icon = "👟"
    else:
        head = "👨 OFERTA FITNESS MASCULINA"
        icon = "🏋️"
    return (
        f"🔥 {head} 🔥\n\n"
        f"{icon} {title}\n\n"
        f"💰 Por apenas: {money(price)}\n\n"
        f"🛒 COMPRAR AGORA 👇\n{link}\n\n"
        "⚠️ Preço e disponibilidade podem mudar no Mercado Livre."
    )

def transform(item, fallback=None):
    if not isinstance(item, dict):
        return None
    title = str(item.get("title") or "").strip()
    price = num(item.get("price"))
    link = item.get("permalink") or ""
    if not title or price <= 0:
        return None
    category = classify(title, fallback)
    if not category:
        return None
    shipping = item.get("shipping") or {}
    seller = item.get("seller") or {}
    return {
        "id": item.get("id"),
        "titulo": title,
        "preco": price,
        "preco_formatado": money(price),
        "imagem": item.get("thumbnail") or "",
        "link": link,
        "categoria": category,
        "vendidos": integer(item.get("sold_quantity"), 0),
        "condicao": item.get("condition") or "",
        "frete_gratis": bool(shipping.get("free_shipping")),
        "vendedor_id": seller.get("id"),
        "whatsapp": whatsapp_text(title, price, link, category),
    }

def search_ml(term, limit=20):
    term = str(term or "").strip()
    if not term:
        return []
    limit = max(1, min(integer(limit, 20), 50))
    url = f"{API_BASE}/sites/{SITE_ID}/search"
    params = {"q": term, "limit": limit, "offset": 0}
    last_error = None

    # Primeiro tenta autenticado, depois tenta público.
    for authenticated in (True, False):
        try:
            r = requests.get(
                url, params=params, headers=api_headers(authenticated), timeout=25
            )
        except requests.RequestException as e:
            last_error = str(e)
            continue

        if r.status_code == 200:
            try:
                return r.json().get("results", [])
            except ValueError:
                return []

        if r.status_code in (401, 403) and authenticated:
            if refresh_token():
                try:
                    r2 = requests.get(
                        url, params=params, headers=api_headers(True), timeout=25
                    )
                    if r2.status_code == 200:
                        return r2.json().get("results", [])
                except requests.RequestException as e:
                    last_error = str(e)
            continue

        last_error = f"HTTP {r.status_code}: {r.text[:500]}"

    logger.warning("Busca '%s' falhou: %s", term, last_error)
    return []

def search_term(term, category=None, limit=20):
    results = search_ml(term, limit)
    out, seen = [], set()
    for item in results:
        p = transform(item, category)
        if p and p["id"] not in seen:
            seen.add(p["id"])
            out.append(p)
    return out

def search_category(category, limit=30):
    if category not in NICHOS:
        return []
    limit = max(1, min(integer(limit, 30), 100))
    terms = NICHOS[category]["termos"]
    out, seen = [], set()
    per_term = min(20, max(5, limit))
    for term in terms:
        for p in search_term(term, category, per_term):
            if p["id"] in seen:
                continue
            seen.add(p["id"])
            out.append(p)
            if len(out) >= limit:
                return sort_products(out)
    return sort_products(out)

def search_all(limit=30):
    limit = max(1, min(integer(limit, 30), 100))
    out, seen = [], set()
    each = max(5, limit // 3)
    for category in NICHOS:
        for p in search_category(category, each):
            if p["id"] in seen:
                continue
            seen.add(p["id"])
            out.append(p)
            if len(out) >= limit:
                return sort_products(out)
    return sort_products(out)

def sort_products(products):
    return sorted(
        products,
        key=lambda x: (integer(x.get("vendidos"), 0), -num(x.get("preco"))),
        reverse=True,
    )

@app.route("/")
def home():
    connected = bool(valid_token())
    return render_template_string(INDEX_HTML, connected=connected, version=VERSION, niches=NICHOS)

@app.route("/login")
def login():
    url, error = oauth_login()
    if error:
        return error, 500
    return redirect(url)

@app.route("/callback")
def callback():
    if request.args.get("error"):
        return (
            f"<h2>Erro no Mercado Livre</h2><p>{request.args.get('error_description', request.args.get('error'))}</p>",
            400,
        )
    code = request.args.get("code")
    state = request.args.get("state")
    if not code:
        return "Código OAuth não recebido.", 400
    if state != session.get("oauth_state"):
        return "Sessão OAuth inválida ou expirada. Tente conectar novamente.", 400
    verifier = session.get("code_verifier")
    if not verifier:
        return "code_verifier não encontrado. Tente conectar novamente.", 400
    if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
        return "Configuração OAuth incompleta no Render.", 500
    try:
        r = requests.post(
            f"{API_BASE}/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": verifier,
            },
            timeout=25,
        )
    except requests.RequestException as e:
        return f"Erro de conexão com Mercado Livre: {e}", 502
    if r.status_code != 200:
        return f"<h2>Mercado Livre recusou o login</h2><pre>{r.text[:2000]}</pre>", 400
    try:
        save_tokens(r.json())
    except Exception as e:
        return f"Erro salvando token: {e}", 500
    session.pop("oauth_state", None)
    session.pop("code_verifier", None)
    return redirect("/")

@app.route("/logout")
def logout():
    global ACCESS_TOKEN, REFRESH_TOKEN, TOKEN_EXPIRES_AT
    ACCESS_TOKEN = None
    REFRESH_TOKEN = None
    TOKEN_EXPIRES_AT = 0
    session.clear()
    return redirect("/")

@app.route("/health")
def health():
    return jsonify(ok=True, app="Robo de Ofertas", versao=VERSION)

@app.route("/diagnostico")
def diagnostico():
    return jsonify(
        ok=True,
        app="Robo de Ofertas",
        versao=VERSION,
        mercado_livre=bool(valid_token()),
        ml_client_id=bool(CLIENT_ID),
        ml_client_secret=bool(CLIENT_SECRET),
        ml_redirect_uri=bool(REDIRECT_URI),
        categorias=list(NICHOS.keys()),
    )

@app.route("/api/status")
def status():
    return jsonify(
        ok=True,
        app="Robo de Ofertas",
        versao=VERSION,
        mercado_livre=bool(valid_token()),
        categorias=list(NICHOS.keys()),
    )

@app.route("/api/buscar")
def api_buscar():
    term = request.args.get("q", "").strip()
    category = request.args.get("categoria", "todos").strip().lower()
    limit = integer(request.args.get("limite", 30), 30)

    if not term:
        return jsonify(ok=False, mensagem="Informe o produto para buscar.", produtos=[]), 400

    if category not in ("todos", "todas", "") and category not in NICHOS:
        return jsonify(ok=False, mensagem="Categoria inválida.", produtos=[]), 400

    products = search_term(term, None if category in ("todos", "todas", "") else category, limit)
    return jsonify(ok=True, quantidade=len(products), produtos=products)

@app.route("/ofertas/<category>")
def offers(category):
    category = category.lower().strip()
    if category not in NICHOS:
        return jsonify(ok=False, mensagem="Categoria não encontrada.", produtos=[]), 404
    limit = integer(request.args.get("limite", 30), 30)
    products = search_category(category, limit)
    return jsonify(
        ok=True,
        categoria=category,
        nome_categoria=NICHOS[category]["nome"],
        quantidade=len(products),
        produtos=products,
    )

@app.route("/melhores")
def melhores():
    category = request.args.get("categoria", "todos").lower().strip()
    limit = integer(request.args.get("limite", 30), 30)
    if category in ("todos", "todas", ""):
        products = search_all(limit)
    elif category in NICHOS:
        products = search_category(category, limit)
    else:
        return jsonify(ok=False, mensagem="Categoria inválida.", produtos=[]), 400
    return jsonify(ok=True, categoria=category, quantidade=len(products), produtos=products)

@app.route("/api/whatsapp")
def whatsapp_api():
    title = request.args.get("titulo", "Oferta Fitness")
    price = num(request.args.get("preco"))
    link = request.args.get("link", "")
    category = request.args.get("categoria", "suplementos")
    if not link:
        return jsonify(ok=False, mensagem="Link não informado."), 400
    text = whatsapp_text(title, price, link, category)
    return jsonify(
        ok=True,
        mensagem=text,
        whatsapp_url="https://wa.me/?text=" + quote(text),
    )

@app.route("/api/me")
def me():
    t = valid_token()
    if not t:
        return jsonify(ok=False, mercado_livre=False, mensagem="Mercado Livre não conectado."), 401
    try:
        r = requests.get(f"{API_BASE}/users/me", headers=api_headers(True), timeout=25)
    except requests.RequestException as e:
        return jsonify(ok=False, mensagem=str(e)), 502
    if r.status_code != 200:
        return jsonify(
            ok=False,
            mercado_livre=True,
            status=r.status_code,
            mensagem="Mercado Livre recusou a consulta.",
            resposta=r.text[:1000],
        ), r.status_code
    try:
        data = r.json()
    except ValueError:
        data = {}
    return jsonify(ok=True, mercado_livre=True, dados=data)

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/") or request.path.startswith("/ofertas/"):
        return jsonify(ok=False, mensagem="Rota não encontrada.", rota=request.path), 404
    return "<h2>Rota não encontrada</h2><a href='/'>Voltar</a>", 404

@app.errorhandler(500)
def server_error(e):
    logger.exception("Erro interno")
    if request.path.startswith("/api/") or request.path.startswith("/ofertas/"):
        return jsonify(ok=False, mensagem="Erro interno do servidor.", erro=str(e)), 500
    return "<h2>Erro interno</h2><a href='/'>Voltar</a>", 500

INDEX_HTML = r"""
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#111827">
<title>Robo de Ofertas Fitness</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#f4f6f8;font-family:Arial,sans-serif;color:#111827}
header{background:#111827;color:white;padding:22px 16px;text-align:center}
main{max-width:1000px;margin:auto;padding:16px}
.card{background:white;border-radius:16px;padding:16px;margin-bottom:16px;box-shadow:0 2px 10px #00000010}
h1{margin:0 0 6px;font-size:25px}
h2{font-size:19px}
button,a.btn{border:0;border-radius:10px;padding:12px 15px;font-weight:bold;text-decoration:none;display:inline-block;cursor:pointer}
.connect{background:#22c55e;color:white}
.logout{background:#ef4444;color:white}
.search{display:flex;gap:8px;flex-wrap:wrap}
input,select{padding:12px;border:1px solid #ddd;border-radius:10px;flex:1;min-width:180px}
.search button{background:#111827;color:white}
.categories{display:flex;gap:8px;flex-wrap:wrap}
.categories button{background:#e5e7eb}
#status{margin-top:10px;font-weight:bold}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}
.product{border:1px solid #e5e7eb;border-radius:14px;overflow:hidden;background:white}
.product img{width:100%;height:210px;object-fit:contain;background:#f8fafc}
.product .body{padding:13px}
.price{font-size:20px;font-weight:bold;margin:8px 0}
.whats{background:#25d366;color:white;width:100%;margin-top:8px;text-align:center}
.small{font-size:13px;color:#6b7280}
#loading{display:none;padding:15px;text-align:center}
</style>
</head>
<body>
<header>
<h1>🔥 Robo de Ofertas Fitness</h1>
<div>Suplementos • Fitness Feminino • Fitness Masculino</div>
</header>
<main>
<div class="card">
{% if connected %}
<div>🟢 <b>Mercado Livre conectado</b></div>
<a class="btn logout" href="/logout" style="margin-top:10px">Desconectar</a>
{% else %}
<div>🔴 <b>Mercado Livre não conectado</b></div>
<a class="btn connect" href="/login" style="margin-top:10px">🔗 Conectar Mercado Livre</a>
{% endif %}
<div id="status"></div>
</div>

<div class="card">
<h2>🔎 Procurar produto</h2>
<div class="search">
<input id="query" placeholder="Ex.: Whey, Creatina, Legging..." value="Whey">
<select id="category">
<option value="todos">Todos</option>
<option value="suplementos">🥤 Suplementos</option>
<option value="fitness_feminino">👩 Fitness Feminino</option>
<option value="fitness_masculino">👨 Fitness Masculino</option>
</select>
<button onclick="buscar()">Buscar</button>
</div>
</div>

<div class="card">
<h2>📂 Categorias</h2>
<div class="categories">
<button onclick="categoria('suplementos')">🥤 Suplementos</button>
<button onclick="categoria('fitness_feminino')">👩 Feminino</button>
<button onclick="categoria('fitness_masculino')">👨 Masculino</button>
<button onclick="categoria('todos')">🔥 Todas</button>
</div>
</div>

<div id="loading">🔎 Procurando ofertas...</div>
<div id="results" class="grid"></div>
</main>

<script>
function esc(s){
 return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
}
function categoria(c){
 document.getElementById('category').value=c;
 if(c==='todos'){
   buscar();
   return;
 }
 const q = c==='suplementos' ? 'whey protein' :
           c==='fitness_feminino' ? 'legging feminina academia' :
           'camiseta dry fit masculina';
 document.getElementById('query').value=q;
 buscar();
}
async function buscar(){
 const q=document.getElementById('query').value.trim();
 const c=document.getElementById('category').value;
 if(!q){document.getElementById('status').textContent='Digite um produto.';return;}
 document.getElementById('loading').style.display='block';
 document.getElementById('results').innerHTML='';
 document.getElementById('status').textContent='';
 try{
   const r=await fetch('/api/buscar?q='+encodeURIComponent(q)+'&categoria='+encodeURIComponent(c)+'&limite=30');
   const data=await r.json();
   if(!r.ok || !data.ok){
     document.getElementById('status').textContent='❌ '+(data.mensagem||'Erro na busca.');
     return;
   }
   if(!data.produtos || !data.produtos.length){
     document.getElementById('status').textContent='❌ Nenhuma oferta encontrada. Tente outro termo.';
     return;
   }
   document.getElementById('status').textContent='✅ '+data.quantidade+' ofertas encontradas.';
   render(data.produtos);
 }catch(e){
   document.getElementById('status').textContent='❌ Erro de conexão com o robô.';
 }finally{
   document.getElementById('loading').style.display='none';
 }
}
function render(products){
 const box=document.getElementById('results');
 box.innerHTML=products.map(p=>`
 <article class="product">
   ${p.imagem?`<img src="${esc(p.imagem)}" alt="">`:''}
   <div class="body">
     <b>${esc(p.titulo)}</b>
     <div class="price">${esc(p.preco_formatado)}</div>
     ${p.vendidos?`<div class="small">🛒 ${esc(p.vendidos)} vendidos</div>`:''}
     ${p.frete_gratis?`<div class="small">🚚 Frete grátis</div>`:''}
     <a class="btn whats" target="_blank" href="/api/whatsapp?titulo=${encodeURIComponent(p.titulo)}&preco=${encodeURIComponent(p.preco)}&link=${encodeURIComponent(p.link)}&categoria=${encodeURIComponent(p.categoria)}">📲 Compartilhar no WhatsApp</a>
     <a class="btn" target="_blank" href="${esc(p.link)}" style="background:#e5e7eb;width:100%;margin-top:7px;text-align:center">🛒 Ver produto</a>
   </div>
 </article>`).join('');
}
</script>
</body>
</html>
"""

if __name__ == "__main__":
    port = integer(os.getenv("PORT", 5000), 5000)
    app.run(host="0.0.0.0", port=port, debug=False)
