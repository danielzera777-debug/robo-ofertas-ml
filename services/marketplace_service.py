import requests


class MarketplaceService:

    BASE_URL = "https://api.mercadolibre.com"

    def __init__(self):
        self.session = requests.Session()

        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "Robo-Ofertas-ML/2.0"
        })

    def buscar_ofertas(self, termo="ofertas", limite=20):

        url = f"{self.BASE_URL}/sites/MLB/search"

        params = {
            "q": termo,
            "limit": limite
        }

        try:

            resposta = self.session.get(
                url,
                params=params,
                timeout=20
            )

            resposta.raise_for_status()

            dados = resposta.json()

            return dados

        except requests.exceptions.RequestException as erro:

            return {
                "sucesso": False,
                "erro": str(erro),
                "resultados": []
            }

        except ValueError:

            return {
                "sucesso": False,
                "erro": "Resposta inválida da API.",
                "resultados": []
            }

    def buscar_produtos(
        self,
        termo,
        limite=20
    ):

        dados = self.buscar_ofertas(
            termo=termo,
            limite=limite
        )

        if not isinstance(dados, dict):

            return []

        resultados = dados.get(
            "results",
            []
        )

        if not isinstance(
            resultados,
            list
        ):

            return []

        return resultados

    def obter_produto(
        self,
        item_id
    ):

        if not item_id:

            return None

        url = (
            f"{self.BASE_URL}"
            f"/items/{item_id}"
        )

        try:

            resposta = self.session.get(
                url,
                timeout=20
            )

            resposta.raise_for_status()

            return resposta.json()

        except requests.exceptions.RequestException:

            return None

        except ValueError:

            return None

    def testar_conexao(self):

        url = (
            f"{self.BASE_URL}"
            f"/sites/MLB"
        )

        try:

            resposta = self.session.get(
                url,
                timeout=15
            )

            return {
                "sucesso":
                    resposta.ok,

                "status":
                    resposta.status_code,

                "dados":
                    resposta.json()
                    if resposta.ok
                    else None
            }

        except requests.exceptions.RequestException as erro:

            return {
                "sucesso": False,
                "status": 0,
                "erro": str(erro)
            }
