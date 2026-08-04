@app.route("/buscar")
def buscar():

    termo = request.args.get("q", "").strip()

    if not termo:
        return "Digite um produto para pesquisar.", 400

    access_token = session.get("access_token")

    if not access_token:
        return """
        <h1>⚠️ Mercado Livre não conectado</h1>
        <a href="/">Conectar novamente</a>
        """, 401

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # =========================================================
    # 1. BUSCA OS PRODUTOS NO CATÁLOGO
    # =========================================================

    response = requests.get(
        "https://api.mercadolibre.com/products/search",
        headers=headers,
        params={
            "status": "active",
            "site_id": "MLB",
            "q": termo,
            "limit": 10,
        },
        timeout=30,
    )

    if response.status_code != 200:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Erro na busca</title>
        </head>

        <body>

            <h1>❌ Erro na busca</h1>

            <p>
                Status da API:
                <strong>{response.status_code}</strong>
            </p>

            <pre>{response.text}</pre>

            <br>

            <a href="/">← Voltar</a>

        </body>
        </html>
        """, response.status_code

    data = response.json()

    produtos = data.get("results", [])

    # =========================================================
    # 2. HTML
    # =========================================================

    html = f"""
    <!DOCTYPE html>
    <html>

    <head>

        <meta charset="UTF-8">

        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>Busca - {termo}</title>

        <style>

            body {{
                font-family: Arial, sans-serif;
                background: #f5f5f5;
                margin: 0;
                padding: 20px;
            }}

            .container {{
                max-width: 900px;
                margin: auto;
            }}

            .top {{
                background: white;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 20px;
            }}

            .produto {{
                background: white;
                border-radius: 12px;
                padding: 18px;
                margin-bottom: 18px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }}

            .produto img {{
                width: 180px;
                height: 180px;
                object-fit: contain;
                display: block;
                margin-bottom: 10px;
            }}

            .titulo {{
                font-size: 18px;
                font-weight: bold;
                margin: 10px 0;
            }}

            .preco {{
                font-size: 24px;
                font-weight: bold;
                color: #008000;
                margin: 10px 0;
            }}

            .info {{
                color: #555;
                margin: 5px 0;
            }}

            .botao {{
                display: inline-block;
                background: #3483fa;
                color: white;
                padding: 12px 18px;
                border-radius: 8px;
                text-decoration: none;
                margin-top: 10px;
            }}

            .botao:hover {{
                background: #2968c8;
            }}

            .catalogo {{
                color: #777;
                font-size: 13px;
            }}

            .sem-preco {{
                color: #999;
                font-size: 15px;
            }}

        </style>

    </head>

    <body>

    <div class="container">

        <div class="top">

            <h1>🔎 Busca de produtos</h1>

            <p>
                <strong>Termo:</strong> {termo}
            </p>

            <p>
                Produtos encontrados:
                <strong>{len(produtos)}</strong>
            </p>

            <a href="/">
                ← Voltar
            </a>

        </div>
    """

    if not produtos:

        html += """
        <div class="produto">
            <h2>Nenhum produto encontrado.</h2>
        </div>
        """

    # =========================================================
    # 3. PROCESSA CADA PRODUTO
    # =========================================================

    for produto in produtos:

        product_id = produto.get("id")

        nome = produto.get(
            "name",
            "Produto sem nome"
        )

        domain_id = produto.get(
            "domain_id",
            ""
        )

        pictures = produto.get(
            "pictures",
            []
        )

        imagem = ""

        if pictures:

            imagem = pictures[0].get(
                "url",
                ""
            )

        # -----------------------------------------------------
        # Dados atualizados do produto
        # -----------------------------------------------------

        detalhe = {}

        try:

            detalhe_response = requests.get(
                f"https://api.mercadolibre.com/products/{product_id}",
                headers=headers,
                timeout=20,
            )

            if detalhe_response.status_code == 200:

                detalhe = detalhe_response.json()

        except Exception:

            detalhe = {}

        # -----------------------------------------------------
        # Buy Box
        # -----------------------------------------------------

        buy_box = detalhe.get(
            "buy_box_winner",
            {}
        )

        item_id = buy_box.get(
            "item_id"
        )

        preco = buy_box.get(
            "price"
        )

        moeda = buy_box.get(
            "currency_id",
            "BRL"
        )

        vendedor_id = buy_box.get(
            "seller_id"
        )

        # -----------------------------------------------------
        # Link do produto
        # -----------------------------------------------------

        permalink = detalhe.get(
            "permalink"
        )

        if not permalink:

            permalink = (
                f"https://www.mercadolivre.com.br/"
                f"p/{product_id}"
            )

        # -----------------------------------------------------
        # Se encontrou uma publicação vencedora
        # -----------------------------------------------------

        if preco is not None:

            try:

                preco_formatado = (
                    f"R$ {float(preco):,.2f}"
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )

            except Exception:

                preco_formatado = str(preco)

        else:

            preco_formatado = (
                "Preço não disponível"
            )

        # -----------------------------------------------------
        # HTML DO PRODUTO
        # -----------------------------------------------------

        html += f"""

        <div class="produto">

            """

        if imagem:

            html += f"""
                <img
                    src="{imagem}"
                    alt="{nome}"
                >
            """

        html += f"""

            <div class="titulo">
                {nome}
            </div>

            <div class="preco">
                {preco_formatado}
            </div>

            <div class="info">
                📦 Produto: {product_id}
            </div>

            <div class="info">
                🏷️ Categoria:
                {domain_id}
            </div>
        """

        if item_id:

            html += f"""
            <div class="info">
                🛒 Item atualizado:
                {item_id}
            </div>
            """

        if vendedor_id:

            html += f"""
            <div class="info">
                👤 Vendedor:
                {vendedor_id}
            </div>
            """

        if item_id:

            link_anuncio = (
                f"https://www.mercadolivre.com.br/"
                f"MLB-{item_id.replace('MLB', '')}"
            )

            html += f"""
                <a
                    class="botao"
                    href="{link_anuncio}"
                    target="_blank"
                >
                    🛒 Ver anúncio
                </a>
            """

        elif permalink:

            html += f"""
                <a
                    class="botao"
                    href="{permalink}"
                    target="_blank"
                >
                    🔎 Ver produto
                </a>
            """

        else:

            html += """
                <p class="sem-preco">
                    Este produto ainda não possui
                    uma publicação disponível.
                </p>
            """

        html += """

        </div>

        """

    # =========================================================
    # FINAL
    # =========================================================

    html += """

    </div>

    </body>

    </html>

    """

    return html
