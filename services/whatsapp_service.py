import os
import requests


class WhatsAppService:

    def __init__(self):

        self.access_token = os.getenv(
            "WHATSAPP_ACCESS_TOKEN"
        )

        self.phone_number_id = os.getenv(
            "WHATSAPP_PHONE_NUMBER_ID"
        )

        self.api_version = os.getenv(
            "WHATSAPP_API_VERSION",
            "v23.0"
        )

        self.base_url = (
            "https://graph.facebook.com/"
            f"{self.api_version}"
        )

    def configurado(self):

        return bool(
            self.access_token
            and self.phone_number_id
        )

    def _headers(self):

        return {
            "Authorization":
                f"Bearer {self.access_token}",
            "Content-Type":
                "application/json"
        }

    def _url(self):

        return (
            f"{self.base_url}/"
            f"{self.phone_number_id}/messages"
        )

    def enviar_texto(
        self,
        numero,
        mensagem
    ):

        if not self.configurado():

            return {
                "sucesso": False,
                "erro":
                    "WhatsApp não configurado."
            }

        if not numero:

            return {
                "sucesso": False,
                "erro":
                    "Número do destinatário não informado."
            }

        if not mensagem:

            return {
                "sucesso": False,
                "erro":
                    "Mensagem não informada."
            }

        payload = {
            "messaging_product":
                "whatsapp",
            "to":
                str(numero),
            "type":
                "text",
            "text": {
                "preview_url":
                    True,
                "body":
                    str(mensagem)
            }
        }

        try:

            resposta = requests.post(
                self._url(),
                headers=self._headers(),
                json=payload,
                timeout=30
            )

            try:

                dados = resposta.json()

            except ValueError:

                dados = {
                    "resposta":
                        resposta.text
                }

            if resposta.ok:

                return {
                    "sucesso": True,
                    "status":
                        resposta.status_code,
                    "dados":
                        dados
                }

            return {
                "sucesso": False,
                "status":
                    resposta.status_code,
                "erro":
                    dados
            }

        except requests.RequestException as erro:

            return {
                "sucesso": False,
                "erro":
                    str(erro)
            }

    def enviar_imagem(
        self,
        numero,
        imagem_url,
        legenda=None
    ):

        if not self.configurado():

            return {
                "sucesso": False,
                "erro":
                    "WhatsApp não configurado."
            }

        if not numero:

            return {
                "sucesso": False,
                "erro":
                    "Número do destinatário não informado."
            }

        if not imagem_url:

            return {
                "sucesso": False,
                "erro":
                    "URL da imagem não informada."
            }

        imagem = {
            "link":
                str(imagem_url)
        }

        if legenda:

            imagem["caption"] = str(
                legenda
            )

        payload = {
            "messaging_product":
                "whatsapp",
            "to":
                str(numero),
            "type":
                "image",
            "image":
                imagem
        }

        try:

            resposta = requests.post(
                self._url(),
                headers=self._headers(),
                json=payload,
                timeout=30
            )

            try:

                dados = resposta.json()

            except ValueError:

                dados = {
                    "resposta":
                        resposta.text
                }

            if resposta.ok:

                return {
                    "sucesso": True,
                    "status":
                        resposta.status_code,
                    "dados":
                        dados
                }

            return {
                "sucesso": False,
                "status":
                    resposta.status_code,
                "erro":
                    dados
            }

        except requests.RequestException as erro:

            return {
                "sucesso": False,
                "erro":
                    str(erro)
            }

    def enviar_oferta(
        self,
        numero,
        oferta
    ):

        if not isinstance(
            oferta,
            dict
        ):

            return {
                "sucesso": False,
                "erro":
                    "Oferta inválida."
            }

        mensagem = (
            oferta.get("texto")
            or oferta.get("mensagem")
            or ""
        )

        imagem = (
            oferta.get("imagem")
            or oferta.get("image")
            or ""
        )

        if imagem:

            return self.enviar_imagem(
                numero=numero,
                imagem_url=imagem,
                legenda=mensagem
            )

        return self.enviar_texto(
            numero=numero,
            mensagem=mensagem
        )

    def testar_conexao(self):

        if not self.configurado():

            return {
                "sucesso": False,
                "erro":
                    "Credenciais do WhatsApp não configuradas."
            }

        url = (
            f"{self.base_url}/"
            f"{self.phone_number_id}"
        )

        try:

            resposta = requests.get(
                url,
                headers=self._headers(),
                timeout=20
            )

            try:

                dados = resposta.json()

            except ValueError:

                dados = {
                    "resposta":
                        resposta.text
                }

            return {
                "sucesso":
                    resposta.ok,
                "status":
                    resposta.status_code,
                "dados":
                    dados
            }

        except requests.RequestException as erro:

            return {
                "sucesso": False,
                "erro":
                    str(erro)
            }
