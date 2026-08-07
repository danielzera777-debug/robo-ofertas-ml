# services/product_service.py

import logging
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional


logger = logging.getLogger("robo-ofertas.products")


class ProductService:
    """
    Serviço responsável por:
    - normalizar títulos;
    - classificar produtos;
    - remover duplicados;
    - validar produtos;
    - ordenar ofertas;
    - preparar dados para a interface/app.
    """

    CATEGORIES = {
        "suplementos": {
            "nome": "🥤 Suplementos",
            "termos": [
                "whey",
                "creatina",
                "pre treino",
                "hipercalorico",
                "bcaa",
                "glutamina",
                "multivitaminico",
                "barra proteica",
                "albumina",
                "caseina",
                "colageno",
                "termogenico",
                "omega 3",
                "vitamina d",
                "vitamina c",
                "zinco",
                "magnesio",
                "proteina",
            ],
        },

        "fitness_feminino": {
            "nome": "👩 Fitness Feminino",
            "termos": [
                "legging feminina",
                "legging academia feminina",
                "top fitness feminino",
                "top academia feminino",
                "conjunto fitness feminino",
                "conjunto academia feminino",
                "short fitness feminino",
                "short academia feminino",
                "cropped fitness feminino",
                "macacao fitness feminino",
                "calca fitness feminina",
                "camiseta fitness feminina",
                "blusa fitness feminina",
                "jaqueta fitness feminina",
                "bermuda fitness feminina",
                "body fitness feminino",
                "roupa academia feminina",
            ],
        },

        "fitness_masculino": {
            "nome": "👨 Fitness Masculino",
            "termos": [
                "camiseta dry fit masculina",
                "camiseta academia masculina",
                "regata academia masculina",
                "bermuda fitness masculina",
                "short academia masculino",
                "calca fitness masculina",
                "conjunto fitness masculino",
                "camiseta compressao masculina",
                "blusa academia masculina",
                "jaqueta fitness masculina",
                "regata fitness masculina",
                "short fitness masculino",
                "bermuda academia masculina",
                "roupa academia masculina",
            ],
        },
    }

    # ========================================================
    # NORMALIZAÇÃO
    # ========================================================

    @staticmethod
    def normalize_text(value: Any) -> str:

        text = str(
            value or ""
        ).strip().lower()

        text = unicodedata.normalize(
            "NFKD",
            text,
        )

        text = "".join(
            char
            for char in text
            if not unicodedata.combining(char)
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    # ========================================================
    # NÚMEROS
    # ========================================================

    @staticmethod
    def number(
        value: Any,
        default: float = 0.0,
    ) -> float:

        try:
            return float(
                value
            )

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
            return int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return default

    # ========================================================
    # CATEGORIA
    # ========================================================

    def classify(
        self,
        title: str,
        fallback: Optional[str] = None,
    ) -> Optional[str]:

        text = self.normalize_text(
            title
        )

        if not text:
            return fallback

        # ----------------------------------------------------
        # SUPLEMENTOS
        # ----------------------------------------------------

        supplement_terms = (
            self.CATEGORIES[
                "suplementos"
            ]["termos"]
        )

        for term in supplement_terms:

            if term in text:

                return "suplementos"

        # ----------------------------------------------------
        # FITNESS FEMININO
        # ----------------------------------------------------

        female_terms = (
            self.CATEGORIES[
                "fitness_feminino"
            ]["termos"]
        )

        for term in female_terms:

            if term in text:

                return "fitness_feminino"

        # ----------------------------------------------------
        # FITNESS MASCULINO
        # ----------------------------------------------------

        male_terms = (
            self.CATEGORIES[
                "fitness_masculino"
            ]["termos"]
        )

        for term in male_terms:

            if term in text:

                return "fitness_masculino"

        return fallback

    # ========================================================
    # VALIDAÇÃO
    # ========================================================

    def validate_product(
        self,
        product: Dict[str, Any],
    ) -> bool:

        if not isinstance(
            product,
            dict,
        ):

            return False

        title = str(
            product.get(
                "titulo"
            )
            or product.get(
                "title"
            )
            or ""
        ).strip()

        price = self.number(
            product.get(
                "preco"
            )
            or product.get(
                "price"
            )
        )

        link = str(
            product.get(
                "link"
            )
            or product.get(
                "permalink"
            )
            or ""
        ).strip()

        if not title:
            return False

        if price <= 0:
            return False

        if not link:
            return False

        return True

    # ========================================================
    # PRODUTO PADRONIZADO
    # ========================================================

    def transform(
        self,
        item: Dict[str, Any],
        fallback_category: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:

        if not isinstance(
            item,
            dict,
        ):

            return None

        title = str(
            item.get(
                "titulo"
            )
            or item.get(
                "title"
            )
            or ""
        ).strip()

        price = self.number(
            item.get(
                "preco"
            )
            if item.get(
                "preco"
            ) is not None
            else item.get(
                "price"
            )
        )

        link = str(
            item.get(
                "link"
            )
            or item.get(
                "permalink"
            )
            or ""
        ).strip()

        if not title:
            return None

        if price <= 0:
            return None

        if not link:
            return None

        category = (
            item.get(
                "categoria"
            )
            or self.classify(
                title,
                fallback_category,
            )
        )

        if not category:
            return None

        shipping = (
            item.get(
                "shipping"
            )
            or {}
        )

        seller = (
            item.get(
                "seller"
            )
            or {}
        )

        image = (
            item.get(
                "imagem"
            )
            or item.get(
                "thumbnail"
            )
            or ""
        )

        sold = self.integer(
            item.get(
                "vendidos"
            )
            if item.get(
                "vendidos"
            ) is not None
            else item.get(
                "sold_quantity"
            ),
            0,
        )

        free_shipping = bool(
            item.get(
                "frete_gratis"
            )
            if "frete_gratis" in item
            else shipping.get(
                "free_shipping",
                False,
            )
        )

        return {
            "id": item.get(
                "id"
            ),

            "titulo": title,

            "preco": price,

            "imagem": image,

            "link": link,

            "categoria": category,

            "categoria_nome": self.category_name(
                category
            ),

            "vendidos": max(
                0,
                sold,
            ),

            "condicao": (
                item.get(
                    "condicao"
                )
                or item.get(
                    "condition"
                )
                or ""
            ),

            "frete_gratis": (
                free_shipping
            ),

            "vendedor_id": (
                item.get(
                    "vendedor_id"
                )
                or seller.get(
                    "id"
                )
            ),
        }

    # ========================================================
    # NOME DA CATEGORIA
    # ========================================================

    def category_name(
        self,
        category: str,
    ) -> str:

        category = self.normalize_text(
            category
        )

        data = self.CATEGORIES.get(
            category
        )

        if not data:

            return category

        return data.get(
            "nome",
            category,
        )

    # ========================================================
    # DUPLICADOS
    # ========================================================

    def remove_duplicates(
        self,
        products: Iterable[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        result = []

        seen_ids = set()

        seen_links = set()

        seen_titles = set()

        for product in products:

            if not isinstance(
                product,
                dict,
            ):

                continue

            product_id = str(
                product.get(
                    "id"
                )
                or ""
            ).strip()

            link = str(
                product.get(
                    "link"
                )
                or ""
            ).strip()

            title = self.normalize_text(
                product.get(
                    "titulo"
                )
            )

            duplicate = False

            if product_id:

                if product_id in seen_ids:

                    duplicate = True

                seen_ids.add(
                    product_id
                )

            if link:

                if link in seen_links:

                    duplicate = True

                seen_links.add(
                    link
                )

            if title:

                if title in seen_titles:

                    duplicate = True

                seen_titles.add(
                    title
                )

            if duplicate:

                continue

            result.append(
                product
            )

        return result

    # ========================================================
    # ORDENAÇÃO
    # ========================================================

    def sort_products(
        self,
        products: Iterable[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        products = list(
            products
        )

        return sorted(
            products,
            key=lambda product: (
                self.integer(
                    product.get(
                        "vendidos"
                    ),
                    0,
                ),

                1
                if product.get(
                    "frete_gratis"
                )
                else 0,

                -self.number(
                    product.get(
                        "preco"
                    ),
                    0,
                ),
            ),
            reverse=True,
        )

    # ========================================================
    # PROCESSAMENTO COMPLETO
    # ========================================================

    def process_products(
        self,
        products: Iterable[Dict[str, Any]],
        fallback_category: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:

        processed = []

        for item in products:

            product = self.transform(
                item,
                fallback_category,
            )

            if not product:

                continue

            if not self.validate_product(
                product
            ):

                continue

            processed.append(
                product
            )

        processed = self.remove_duplicates(
            processed
        )

        processed = self.sort_products(
            processed
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

        return processed[
            :limit
        ]

    # ========================================================
    # BUSCA DE TERMOS DE UM NICHO
    # ========================================================

    def category_terms(
        self,
        category: str,
    ) -> List[str]:

        category = self.normalize_text(
            category
        )

        data = self.CATEGORIES.get(
            category
        )

        if not data:

            return []

        return list(
            data.get(
                "termos",
                []
            )
        )

    # ========================================================
    # LISTA DE CATEGORIAS
    # ========================================================

    def categories(
        self,
    ) -> Dict[str, Dict[str, Any]]:

        return self.CATEGORIES.copy()

    # ========================================================
    # DIAGNÓSTICO
    # ========================================================

    def diagnostic(
        self,
    ) -> Dict[str, Any]:

        categories = {}

        for key, data in self.CATEGORIES.items():

            categories[key] = {
                "nome": data.get(
                    "nome"
                ),
                "quantidade_termos": len(
                    data.get(
                        "termos",
                        []
                    )
                ),
                "ativa": bool(
                    data.get(
                        "termos"
                    )
                ),
            }

        return {
            "ok": True,
            "servico": (
                "ProductService"
            ),
            "categorias": categories,
        }


# ============================================================
# INSTÂNCIA PADRÃO
# ============================================================

product_service = ProductService()
