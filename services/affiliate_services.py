import os
import requests


class AffiliateService:

    API_BASE = "https://api.mercadolibre.com"

    def __init__(self, access_token=None):

        self.access_token = (
            access_token
            or os.getenv("ML_ACCESS_TOKEN")
        )

        self.session = requests.Session()

        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "Robo-Ofertas-ML/2.0"
        })

        if self.access_token:
            self.session.headers.update({
                "Authorization":
                    f"Bearer {self.access_token}"
            })

    def definir_token(self, access_token):

        self.access_token = access_token

        if access_token:

            self.session.headers.update({
                "Authorization":
                    f"Bearer {access_token}"
            })

    def gerar_link_afiliado(
        self,
        item_id,
        url_produto=None
    ):

        if not item_id and not url_produto:
            return None

        if url_produto:
            return url_produto

        return (
            "https://www.mercadolivre.com.br/"
            f"item/{item_id}"
        )

    def preparar_oferta(
        self,
        produto,
        margem=10,
        lucro_minimo=20
    ):

        if not isinstance(produto, dict):
            return None

        item_id = produto.get("id")

        titulo = (
            produto.get("title")
            or produto.get("name")
            or "Produto"
        )

        preco = self._numero(
            produto.get("price")
        )

        preco_original = self._numero(
            produto.get("original_price")
        )

        if preco <= 0:
            return None

        if preco_original <= 0:
            preco_original = preco

        desconto = 0

        if preco_original > preco:

            desconto = (
                (preco_original - preco)
                / preco_original
            ) * 100

        valor_margem = (
            preco * float(margem) / 100
        )

        lucro_estimado = valor_margem

        link = self.gerar_link_afiliado(
            item_id=item_id,
            url_produto=produto.get(
                "permalink"
            )
        )

        return {
            "id": item_id,
            "titulo": titulo,
            "preco": preco,
            "preco_original": preco_original,
            "desconto": round(
                desconto,
                2
            ),
            "margem": float(margem),
            "lucro_estimado": round(
                lucro_estimado,
                2
            ),
            "lucro_minimo": float(
                lucro_minimo
            ),
            "link": link,
            "imagem": produto.get(
                "thumbnail"
            ),
            "categoria": produto.get(
                "category_id"
            ),
            "vendedor": produto.get(
                "seller",
                {}
            )
        }

    def filtrar_ofertas(
        self,
        produtos,
        margem=10,
        lucro_minimo=20,
        desconto_minimo=0
    ):

        ofertas = []

        if not isinstance(
            produtos,
            list
        ):
            return ofertas

        for produto in produtos:

            oferta = self.preparar_oferta(
                produto,
                margem=margem,
                lucro_minimo=lucro_minimo
            )

            if not oferta:
                continue

            if (
                oferta["lucro_estimado"]
                < float(lucro_minimo)
            ):
                continue

            if (
                oferta["desconto"]
                < float(desconto_minimo)
            ):
                continue

            ofertas.append(oferta)

        return ofertas

    def ordenar_por_desconto(
        self,
        ofertas
    ):

        if not isinstance(
            ofertas,
            list
        ):
            return []

        return sorted(
            ofertas,
            key=lambda oferta:
                oferta.get(
                    "desconto",
                    0
                ),
            reverse=True
        )

    def melhores_ofertas(
        self,
        produtos,
        limite=20,
        margem=10,
        lucro_minimo=20,
        desconto_minimo=0
    ):

        ofertas = self.filtrar_ofertas(
            produtos=produtos,
            margem=margem,
            lucro_minimo=lucro_minimo,
            desconto_minimo=desconto_minimo
        )

        ofertas = self.ordenar_por_desconto(
            ofertas
        )

        return ofertas[:int(limite)]

    @staticmethod
    def _numero(valor):

        try:

            if valor is None:
                return 0.0

            if isinstance(
                valor,
                str
            ):

                valor = (
                    valor
                    .replace(
                        "R$",
                        ""
                    )
                    .replace(
                        ".",
                        ""
                    )
                    .replace(
                        ",",
                        "."
                    )
                    .strip()
                )

            return float(valor)

        except (
            ValueError,
            TypeError
        ):

            return 0.0
