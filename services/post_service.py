import html
import re


class PostService:

    def __init__(self):

        self.nome_robo = "Robo de Ofertas ML"

    def escapar(self, valor):

        return html.escape(
            str(valor or "")
        )

    def formatar_preco(self, valor):

        try:

            valor = float(valor)

            return (
                f"R$ {valor:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

        except (
            ValueError,
            TypeError
        ):

            return "R$ 0,00"

    def limpar_titulo(self, titulo):

        titulo = str(
            titulo or "Produto"
        )

        titulo = re.sub(
            r"\s+",
            " ",
            titulo
        )

        return titulo.strip()

    def calcular_desconto(
        self,
        preco_original,
        preco
    ):

        try:

            original = float(
                preco_original
            )

            atual = float(
                preco
            )

            if original <= 0:
                return 0

            if atual >= original:
                return 0

            desconto = (
                (original - atual)
                / original
            ) * 100

            return round(
                desconto,
                2
            )

        except (
            ValueError,
            TypeError
        ):

            return 0

    def criar_post(
        self,
        oferta
    ):

        if not isinstance(
            oferta,
            dict
        ):

            return None

        titulo = self.limpar_titulo(
            oferta.get(
                "titulo"
            )
        )

        preco = oferta.get(
            "preco",
            0
        )

        preco_original = oferta.get(
            "preco_original",
            0
        )

        desconto = oferta.get(
            "desconto"
        )

        if desconto is None:

            desconto = self.calcular_desconto(
                preco_original,
                preco
            )

        link = (
            oferta.get("link")
            or oferta.get(
                "permalink"
            )
            or ""
        )

        imagem = (
            oferta.get("imagem")
            or oferta.get(
                "thumbnail"
            )
            or ""
        )

        texto = self.montar_texto(
            titulo=titulo,
            preco=preco,
            preco_original=preco_original,
            desconto=desconto,
            link=link
        )

        return {
            "titulo": titulo,
            "preco": float(
                preco or 0
            ),
            "preco_original": float(
                preco_original or 0
            ),
            "desconto": float(
                desconto or 0
            ),
            "link": link,
            "imagem": imagem,
            "texto": texto
        }

    def montar_texto(
        self,
        titulo,
        preco,
        preco_original,
        desconto,
        link
    ):

        titulo = self.limpar_titulo(
            titulo
        )

        preco_formatado = (
            self.formatar_preco(
                preco
            )
        )

        original_formatado = (
            self.formatar_preco(
                preco_original
            )
        )

        try:

            desconto = float(
                desconto or 0
            )

        except (
            ValueError,
            TypeError
        ):

            desconto = 0

        linhas = []

        linhas.append(
            "🔥 OFERTA ENCONTRADA!"
        )

        linhas.append("")

        linhas.append(
            f"🛍️ {titulo}"
        )

        linhas.append("")

        if (
            preco_original > 0
            and preco_original > preco
        ):

            linhas.append(
                f"❌ De: {original_formatado}"
            )

        linhas.append(
            f"💰 Por: {preco_formatado}"
        )

        if desconto > 0:

            linhas.append(
                f"🔥 Desconto: "
                f"{desconto:.0f}%"
            )

        if link:

            linhas.append("")

            linhas.append(
                "👉 COMPRAR AGORA:"
            )

            linhas.append(
                link
            )

        linhas.append("")

        linhas.append(
            "⚠️ Preço sujeito a alteração "
            "pelo Mercado Livre."
        )

        return "\n".join(
            linhas
        )

    def criar_posts(
        self,
        ofertas
    ):

        if not isinstance(
            ofertas,
            list
        ):

            return []

        posts = []

        for oferta in ofertas:

            post = self.criar_post(
                oferta
            )

            if post:

                posts.append(
                    post
                )

        return posts

    def preparar_whatsapp(
        self,
        oferta
    ):

        post = self.criar_post(
            oferta
        )

        if not post:
            return None

        return post["texto"]

    def preparar_instagram(
        self,
        oferta
    ):

        post = self.criar_post(
            oferta
        )

        if not post:
            return None

        titulo = post["titulo"]
        preco = self.formatar_preco(
            post["preco"]
        )
        desconto = post["desconto"]
        link = post["link"]

        texto = (
            f"🔥 OFERTA DO DIA!\n\n"
            f"🛍️ {titulo}\n\n"
            f"💰 {preco}\n"
        )

        if desconto > 0:

            texto += (
                f"🔥 {desconto:.0f}% OFF\n"
            )

        if link:

            texto += (
                f"\n🔗 Link da oferta:\n"
                f"{link}\n"
            )

        texto += (
            "\n⚠️ Oferta sujeita a "
            "alteração de preço.\n"
        )

        return texto
