# services/offer_service.py

import logging
from typing import Any, Dict, Iterable, List, Optional

from .product_service import product_service


logger = logging.getLogger("robo-ofertas.offers")


class OfferService:
    """
    Serviço central de ofertas.

    Responsabilidades:
    - receber produtos do Mercado Livre;
    - validar e organizar produtos;
    - remover duplicados;
    - aplicar filtros;
    - calcular indicadores simples;
    - preparar ofertas para o aplicativo;
    - gerar texto para compartilhamento.
    """

    def __init__(self):
        self.products = product_service

    # ========================================================
    # NÚMEROS
    # ========================================================

    @staticmethod
    def number(
        value: Any,
        default: float = 0.0,
    ) -> float:

        try:
            return float(value)

        except (
            TypeError,
            ValueError,
        ):

            return default

    @staticmethod
    def integer(
        value: Any,
        default: int = 0,
    ) -> int:

        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ):

            return default

    # ========================================================
    # FORMATAÇÃO DE PREÇO
    # ========================================================

    @staticmethod
    def money(
        value: Any,
    ) -> str:

        try:

            value = float(value)

        except (
            TypeError,
            ValueError,
        ):

            value = 0.0

        return (
            f"R$ {value:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    # ========================================================
    # MARGEM
    # ========================================================

    def calculate_price_with_margin(
        self,
        price: float,
        margin_percent: float,
    ) -> float:

        price = self.number(
            price
        )

        margin_percent = self.number(
            margin_percent
        )

        if price <= 0:

            return 0.0

        if margin_percent < 0:

            margin_percent = 0

        return price * (
            1
            +
            margin_percent / 100
        )

    # ========================================================
    # TEXTO WHATSAPP
    # ========================================================

    def whatsapp_text(
        self,
        product: Dict[str, Any],
    ) -> str:

        title = str(
            product.get(
                "titulo"
            )
            or "Oferta"
        ).strip()

        price = self.number(
            product.get(
                "preco"
            )
        )

        link = str(
            product.get(
                "link"
            )
            or ""
        ).strip()

        category = str(
            product.get(
                "categoria"
            )
            or ""
        ).strip()

        if category == "suplementos":

            header = (
                "🥤 OFERTA DE SUPLEMENTO"
            )

            icon = "💪"

        elif category == "fitness_feminino":

            header = (
                "👩 OFERTA FITNESS FEMININA"
            )

            icon = "👟"

        elif category == "fitness_masculino":

            header = (
                "👨 OFERTA FITNESS MASCULINA"
            )

            icon = "🏋️"

        else:

            header = (
                "🔥 OFERTA ESPECIAL"
            )

            icon = "🛒"

        lines = [
            f"🔥 {header} 🔥",
            "",
            f"{icon} {title}",
            "",
            f"💰 Por apenas: {self.money(price)}",
            "",
            "🛒 COMPRAR AGORA 👇",
            link,
            "",
            "⚠️ Preço e disponibilidade podem mudar no Mercado Livre.",
        ]

        return "\n".join(lines)

    # ========================================================
    # PREPARAR OFERTA
    # ========================================================

    def prepare_offer(
        self,
        product: Dict[str, Any],
        margin_percent: float = 0,
    ) -> Optional[Dict[str, Any]]:

        if not isinstance(
            product,
            dict,
        ):

            return None

        normalized = self.products.transform(
            product,
            product.get(
                "categoria"
            ),
        )

        if not normalized:

            return None

        price = self.number(
            normalized.get(
                "preco"
            )
        )

        resale_price = (
            self.calculate_price_with_margin(
                price,
                margin_percent,
            )
            if margin_percent > 0
            else price
        )

        normalized[
            "preco_formatado"
        ] = self.money(
            price
        )

        normalized[
            "preco_revenda"
        ] = resale_price

        normalized[
            "preco_revenda_formatado"
        ] = self.money(
            resale_price
        )

        normalized[
            "margem_percentual"
        ] = self.number(
            margin_percent
        )

        normalized[
            "whatsapp"
        ] = self.whatsapp_text(
            normalized
        )

        return normalized

    # ========================================================
    # PREPARAR VÁRIAS OFERTAS
    # ========================================================

    def prepare_offers(
        self,
        products: Iterable[Dict[str, Any]],
        margin_percent: float = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:

        prepared = []

        for product in products:

            offer = self.prepare_offer(
                product,
                margin_percent,
            )

            if not offer:

                continue

            prepared.append(
                offer
            )

        prepared = self.products.remove_duplicates(
            prepared
        )

        prepared = self.products.sort_products(
            prepared
        )

        try:

            limit = int(
                limit
            )

        except (
            TypeError,
            ValueError,
        ):

            limit = 100

        limit = max(
            1,
            min(
                limit,
                100,
            ),
        )

        return prepared[
            :limit
        ]

    # ========================================================
    # FILTRO POR PREÇO
    # ========================================================

    def filter_price(
        self,
        products: Iterable[Dict[str, Any]],
        minimum: float = 0,
        maximum: Optional[float] = None,
    ) -> List[Dict[str, Any]]:

        minimum = self.number(
            minimum
        )

        if maximum is not None:

            maximum = self.number(
                maximum
            )

        result = []

        for product in products:

            price = self.number(
                product.get(
                    "preco"
                )
            )

            if price < minimum:

                continue

            if (
                maximum is not None
                and
                price > maximum
            ):

                continue

            result.append(
                product
            )

        return result

    # ========================================================
    # FILTRO FRETE GRÁTIS
    # ========================================================

    def filter_free_shipping(
        self,
        products: Iterable[Dict[str, Any]],
        enabled: bool = False,
    ) -> List[Dict[str, Any]]:

        if not enabled:

            return list(
                products
            )

        return [
            product
            for product in products
            if bool(
                product.get(
                    "frete_gratis"
                )
            )
        ]

    # ========================================================
    # FILTRO POR VENDAS
    # ========================================================

    def filter_sold_quantity(
        self,
        products: Iterable[Dict[str, Any]],
        minimum: int = 0,
    ) -> List[Dict[str, Any]]:

        minimum = self.integer(
            minimum
        )

        return [
            product
            for product in products
            if self.integer(
                product.get(
                    "vendidos"
                ),
                0,
            ) >= minimum
        ]

    # ========================================================
    # FILTRO COMPLETO
    # ========================================================

    def filter_offers(
        self,
        products: Iterable[Dict[str, Any]],
        minimum_price: float = 0,
        maximum_price: Optional[float] = None,
        free_shipping: bool = False,
        minimum_sold: int = 0,
    ) -> List[Dict[str, Any]]:

        result = self.filter_price(
            products,
            minimum_price,
            maximum_price,
        )

        result = self.filter_free_shipping(
            result,
            free_shipping,
        )

        result = self.filter_sold_quantity(
            result,
            minimum_sold,
        )

        return self.products.sort_products(
            result
        )

    # ========================================================
    # ESTATÍSTICAS
    # ========================================================

    def statistics(
        self,
        products: Iterable[Dict[str, Any]],
    ) -> Dict[str, Any]:

        products = list(
            products
        )

        if not products:

            return {
                "quantidade": 0,
                "preco_minimo": 0,
                "preco_maximo": 0,
                "preco_medio": 0,
                "vendidos_total": 0,
                "frete_gratis": 0,
            }

        prices = [
            self.number(
                product.get(
                    "preco"
                )
            )
            for product in products
        ]

        sold = [
            self.integer(
                product.get(
                    "vendidos"
                ),
                0,
            )
            for product in products
        ]

        free_shipping = sum(
            1
            for product in products
            if product.get(
                "frete_gratis"
            )
        )

        return {
            "quantidade": len(
                products
            ),

            "preco_minimo": min(
                prices
            ),

            "preco_maximo": max(
                prices
            ),

            "preco_medio": (
                sum(prices)
                /
                len(prices)
            ),

            "vendidos_total": sum(
                sold
            ),

            "frete_gratis": (
                free_shipping
            ),
        }

    # ========================================================
    # DASHBOARD
    # ========================================================

    def dashboard(
        self,
        products: Iterable[Dict[str, Any]],
    ) -> Dict[str, Any]:

        products = list(
            products
        )

        stats = self.statistics(
            products
        )

        categories = {}

        for product in products:

            category = str(
                product.get(
                    "categoria"
                )
                or "outros"
            )

            categories[
                category
            ] = categories.get(
                category,
                0,
            ) + 1

        return {
            "ok": True,

            "total_ofertas": len(
                products
            ),

            "estatisticas": stats,

            "categorias": categories,

            "melhor_oferta": (
                products[0]
                if products
                else None
            ),
        }

    # ========================================================
    # DIAGNÓSTICO
    # ========================================================

    def diagnostic(
        self,
    ) -> Dict[str, Any]:

        return {
            "ok": True,
            "servico": "OfferService",
            "product_service": (
                self.products.diagnostic()
            ),
        }


# ============================================================
# INSTÂNCIA GLOBAL
# ============================================================

offer_service = OfferService()
