import os
import uuid
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont


class ImageService:

    def __init__(self):

        self.output_dir = os.path.join(
            "static",
            "generated"
        )

        os.makedirs(
            self.output_dir,
            exist_ok=True
        )

    def baixar_imagem(
        self,
        url
    ):

        if not url:
            return None

        try:

            resposta = requests.get(
                url,
                timeout=20,
                headers={
                    "User-Agent":
                        "Robo-Ofertas-ML/2.0"
                }
            )

            resposta.raise_for_status()

            imagem = Image.open(
                BytesIO(
                    resposta.content
                )
            )

            return imagem.convert(
                "RGB"
            )

        except (
            requests.RequestException,
            OSError,
            ValueError
        ):

            return None

    def fonte(
        self,
        tamanho,
        negrito=False
    ):

        caminhos = []

        if negrito:

            caminhos.extend([
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
            ])

        else:

            caminhos.extend([
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
            ])

        for caminho in caminhos:

            if os.path.exists(caminho):

                try:

                    return ImageFont.truetype(
                        caminho,
                        tamanho
                    )

                except OSError:

                    pass

        return ImageFont.load_default()

    def quebrar_texto(
        self,
        draw,
        texto,
        fonte,
        largura
    ):

        palavras = str(
            texto or ""
        ).split()

        linhas = []
        atual = ""

        for palavra in palavras:

            teste = (
                f"{atual} {palavra}"
                .strip()
            )

            caixa = draw.textbbox(
                (0, 0),
                teste,
                font=fonte
            )

            if (
                caixa[2] - caixa[0]
                <= largura
            ):

                atual = teste

            else:

                if atual:

                    linhas.append(
                        atual
                    )

                atual = palavra

        if atual:

            linhas.append(
                atual
            )

        return linhas

    def criar_imagem(
        self,
        oferta
    ):

        if not isinstance(
            oferta,
            dict
        ):

            return None

        titulo = str(
            oferta.get(
                "titulo",
                "Oferta"
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
            "desconto",
            0
        )

        imagem_url = (
            oferta.get(
                "imagem"
            )
            or oferta.get(
                "thumbnail"
            )
        )

        produto = self.baixar_imagem(
            imagem_url
        )

        largura = 1080
        altura = 1350

        canvas = Image.new(
            "RGB",
            (
                largura,
                altura
            ),
            "white"
        )

        draw = ImageDraw.Draw(
            canvas
        )

        titulo_fonte = self.fonte(
            48,
            negrito=True
        )

        preco_fonte = self.fonte(
            64,
            negrito=True
        )

        pequeno_fonte = self.fonte(
            32,
            negrito=False
        )

        destaque_fonte = self.fonte(
            38,
            negrito=True
        )

        if produto:

            produto.thumbnail(
                (
                    760,
                    620
                )
            )

            x = (
                largura
                - produto.width
            ) // 2

            y = 100

            canvas.paste(
                produto,
                (
                    x,
                    y
                )
            )

        else:

            draw.rectangle(
                (
                    80,
                    100,
                    1000,
                    650
                ),
                outline="black",
                width=3
            )

            draw.text(
                (
                    390,
                    350
                ),
                "Produto",
                font=titulo_fonte
            )

        titulo_y = 700

        linhas = self.quebrar_texto(
            draw,
            titulo,
            titulo_fonte,
            900
        )

        for linha in linhas[:3]:

            draw.text(
                (
                    90,
                    titulo_y
                ),
                linha,
                font=titulo_fonte,
                fill="black"
            )

            titulo_y += 60

        if (
            preco_original
            and float(preco_original) > float(preco)
        ):

            original = self.formatar_preco(
                preco_original
            )

            draw.text(
                (
                    90,
                    titulo_y + 15
                ),
                f"De: {original}",
                font=pequeno_fonte,
                fill="black"
            )

            titulo_y += 55

        preco_formatado = (
            self.formatar_preco(
                preco
            )
        )

        draw.text(
            (
                90,
                titulo_y + 10
            ),
            f"Por: {preco_formatado}",
            font=preco_fonte,
            fill="black"
        )

        titulo_y += 90

        try:

            desconto_numero = float(
                desconto or 0
            )

        except (
            ValueError,
            TypeError
        ):

            desconto_numero = 0

        if desconto_numero > 0:

            draw.text(
                (
                    90,
                    titulo_y
                ),
                (
                    f"{desconto_numero:.0f}% OFF"
                ),
                font=destaque_fonte,
                fill="black"
            )

        draw.text(
            (
                90,
                1210
            ),
            "OFERTA NO MERCADO LIVRE",
            font=pequeno_fonte,
            fill="black"
        )

        nome = (
            f"oferta_{uuid.uuid4().hex}.jpg"
        )

        caminho = os.path.join(
            self.output_dir,
            nome
        )

        canvas.save(
            caminho,
            "JPEG",
            quality=92,
            optimize=True
        )

        return caminho

    def gerar_para_ofertas(
        self,
        ofertas
    ):

        if not isinstance(
            ofertas,
            list
        ):

            return []

        imagens = []

        for oferta in ofertas:

            caminho = self.criar_imagem(
                oferta
            )

            if caminho:

                imagens.append(
                    caminho
                )

        return imagens

    def formatar_preco(
        self,
        valor
    ):

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
