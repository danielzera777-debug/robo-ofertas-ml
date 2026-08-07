# services/mercadolivre_service.py

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import requests


logger = logging.getLogger("robo-ofertas.mercadolivre")


class MercadoLivreService:
    """
    Serviço responsável pelas comunicações com a API do Mercado Livre.

    Regras importantes:
    - OAuth é usado somente quando a operação realmente exige autenticação.
    - A busca pública de produtos não envia access_token.
    - Timeout é obrigatório.
    - Erros HTTP são tratados sem derrubar o aplicativo.
    - O serviço não guarda CLIENT_SECRET nem tokens em arquivo.
    """

    API_BASE = "https://api.mercadolibre.com"
    SITE_ID = "MLB"

    USER_AGENT = "Robo-Ofertas-ML/10.0"

    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expires_at: float = 0,
    ):

        self.client_id = (client_id or "").strip()
        self.client_secret = (client_secret or "").strip()

        self.access_token = (
            access_token.strip()
            if isinstance(access_token, str)
            else None
        )

        self.refresh_token = (
            refresh_token.strip()
            if isinstance(refresh_token, str)
            else None
        )

        self.token_expires_at = float(
            token_expires_at or 0
        )

        self.session = requests.Session()

        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": self.USER_AGENT,
            }
        )

    # ========================================================
    # CONFIGURAÇÃO
    # ========================================================

    def configuration_status(self) -> Dict[str, Any]:

        return {
            "client_id_configurado": bool(
                self.client_id
            ),
            "client_secret_configurado": bool(
                self.client_secret
            ),
            "access_token_configurado": bool(
                self.access_token
            ),
            "refresh_token_configurado": bool(
                self.refresh_token
            ),
            "token_expirado": self.token_is_expired(),
        }

    # ========================================================
    # TOKEN
    # ========================================================

    def set_tokens(
        self,
        access_token: Optional[str],
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
    ) -> None:

        if access_token:
            self.access_token = access_token

        if refresh_token:
            self.refresh_token = refresh_token

        if expires_in:

            try:

                seconds = int(expires_in)

            except (TypeError, ValueError):

                seconds = 21600

            self.token_expires_at = (
                time.time()
                + max(
                    60,
                    seconds - 120,
                )
            )

    def token_is_expired(self) -> bool:

        if not self.access_token:
            return True

        if not self.token_expires_at:
            return False

        return time.time() >= self.token_expires_at

    def refresh_access_token(
        self,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:

        if not self.refresh_token:

            return False, None

        if not self.client_id:

            logger.error(
                "CLIENT_ID não configurado."
            )

            return False, None

        if not self.client_secret:

            logger.error(
                "CLIENT_SECRET não configurado."
            )

            return False, None

        url = (
            f"{self.API_BASE}/oauth/token"
        )

        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }

        try:

            response = self.session.post(
                url,
                data=payload,
                timeout=30,
            )

        except requests.RequestException as error:

            logger.error(
                "Erro ao renovar token: %s",
                error,
            )

            return False, None

        if response.status_code != 200:

            logger.error(
                "Refresh OAuth recusado: HTTP %s",
                response.status_code,
            )

            logger.error(
                "Resposta OAuth: %s",
                response.text[:1000],
            )

            return False, None

        try:

            data = response.json()

        except ValueError:

            logger.error(
                "OAuth retornou JSON inválido."
            )

            return False, None

        new_access_token = data.get(
            "access_token"
        )

        if not new_access_token:

            logger.error(
                "OAuth não retornou access_token."
            )

            return False, None

        self.set_tokens(
            access_token=new_access_token,
            refresh_token=data.get(
                "refresh_token"
            ),
            expires_in=data.get(
                "expires_in"
            ),
        )

        return True, data

    def ensure_token(self) -> Optional[str]:

        if not self.access_token:
            return None

        if not self.token_is_expired():
            return self.access_token

        logger.info(
            "Access token expirado. "
            "Tentando renovar."
        )

        success, _ = (
            self.refresh_access_token()
        )

        if not success:
            return None

        return self.access_token

    # ========================================================
    # HEADERS
    # ========================================================

    def public_headers(self) -> Dict[str, str]:
        """
        Headers para endpoints públicos.

        IMPORTANTE:
        Não adiciona Authorization.
        """

        return {
            "Accept": "application/json",
            "User-Agent": self.USER_AGENT,
        }

    def authenticated_headers(
        self,
    ) -> Dict[str, str]:

        headers = {
            "Accept": "application/json",
            "User-Agent": self.USER_AGENT,
        }

        token = self.ensure_token()

        if token:

            headers["Authorization"] = (
                f"Bearer {token}"
            )

        return headers

    # ========================================================
    # BUSCA PÚBLICA
    # ========================================================

    def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict]]:

        query = str(
            query or ""
        ).strip()

        if not query:

            return [], {
                "status": 400,
                "message": "Termo de busca vazio.",
            }

        try:

            limit = int(limit)

        except (TypeError, ValueError):

            limit = 20

        limit = max(
            1,
            min(
                limit,
                50,
            ),
        )

        try:

            offset = int(offset)

        except (TypeError, ValueError):

            offset = 0

        offset = max(
            0,
            offset,
        )

        url = (
            f"{self.API_BASE}/sites/"
            f"{self.SITE_ID}/search"
        )

        params = {
            "q": query,
            "limit": limit,
            "offset": offset,
        }

        logger.info(
            "Pesquisa pública Mercado Livre: %s",
            query,
        )

        try:

            response = self.session.get(
                url,
                params=params,
                headers=self.public_headers(),
                timeout=30,
            )

        except requests.Timeout:

            logger.error(
                "Timeout na busca: %s",
                query,
            )

            return [], {
                "status": 504,
                "message": (
                    "Tempo limite excedido "
                    "ao consultar o Mercado Livre."
                ),
            }

        except requests.RequestException as error:

            logger.error(
                "Erro de conexão na busca: %s",
                error,
            )

            return [], {
                "status": 502,
                "message": (
                    "Não foi possível conectar "
                    "ao Mercado Livre."
                ),
                "details": str(error),
            }

        logger.info(
            "Mercado Livre busca '%s' -> HTTP %s",
            query,
            response.status_code,
        )

        # ----------------------------------------------------
        # SUCESSO
        # ----------------------------------------------------

        if response.status_code == 200:

            try:

                data = response.json()

            except ValueError:

                return [], {
                    "status": 502,
                    "message": (
                        "Mercado Livre retornou "
                        "JSON inválido."
                    ),
                }

            results = data.get(
                "results",
                [],
            )

            if not isinstance(
                results,
                list,
            ):

                results = []

            return results, None

        # ----------------------------------------------------
        # 403
        # ----------------------------------------------------

        if response.status_code == 403:

            logger.error(
                "HTTP 403 na pesquisa pública."
            )

            logger.error(
                "Resposta: %s",
                response.text[:2000],
            )

            return [], {
                "status": 403,
                "message": (
                    "Mercado Livre bloqueou "
                    "a pesquisa (HTTP 403)."
                ),
                "details": response.text[:2000],
                "type": "search_forbidden",
            }

        # ----------------------------------------------------
        # 401
        # ----------------------------------------------------

        if response.status_code == 401:

            return [], {
                "status": 401,
                "message": (
                    "Autorização necessária "
                    "ou token inválido."
                ),
                "details": response.text[:2000],
                "type": "unauthorized",
            }

        # ----------------------------------------------------
        # RATE LIMIT
        # ----------------------------------------------------

        if response.status_code == 429:

            return [], {
                "status": 429,
                "message": (
                    "Limite de requisições "
                    "atingido pelo Mercado Livre."
                ),
                "details": response.text[:2000],
                "type": "rate_limit",
            }

        # ----------------------------------------------------
        # OUTROS
        # ----------------------------------------------------

        return [], {
            "status": response.status_code,
            "message": (
                "Mercado Livre retornou "
                f"HTTP {response.status_code}."
            ),
            "details": response.text[:2000],
            "type": "api_error",
        }

    # ========================================================
    # USUÁRIO AUTENTICADO
    # ========================================================

    def get_me(
        self,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict]]:

        token = self.ensure_token()

        if not token:

            return None, {
                "status": 401,
                "message": (
                    "Access token não disponível."
                ),
            }

        url = (
            f"{self.API_BASE}/users/me"
        )

        try:

            response = self.session.get(
                url,
                headers=self.authenticated_headers(),
                timeout=30,
            )

        except requests.RequestException as error:

            return None, {
                "status": 502,
                "message": (
                    "Erro ao consultar usuário."
                ),
                "details": str(error),
            }

        if response.status_code == 401:

            logger.warning(
                "Token recusado ao consultar /users/me."
            )

            if self.refresh_token:

                success, _ = (
                    self.refresh_access_token()
                )

                if success:

                    try:

                        response = (
                            self.session.get(
                                url,
                                headers=(
                                    self.authenticated_headers()
                                ),
                                timeout=30,
                            )
                        )

                    except requests.RequestException as error:

                        return None, {
                            "status": 502,
                            "message": str(error),
                        }

            if response.status_code == 401:

                return None, {
                    "status": 401,
                    "message": (
                        "Token inválido ou expirado."
                    ),
                    "details": response.text[:2000],
                }

        if response.status_code != 200:

            return None, {
                "status": response.status_code,
                "message": (
                    "Mercado Livre recusou "
                    "a consulta do usuário."
                ),
                "details": response.text[:2000],
            }

        try:

            return response.json(), None

        except ValueError:

            return None, {
                "status": 502,
                "message": (
                    "Resposta inválida do Mercado Livre."
                ),
            }

    # ========================================================
    # TESTE COMPLETO
    # ========================================================

    def diagnostic_test(
        self,
        query: str = "whey protein",
    ) -> Dict[str, Any]:

        result = {
            "ok": False,
            "api": self.API_BASE,
            "site": self.SITE_ID,
            "configuracao": (
                self.configuration_status()
            ),
            "teste_busca": {},
        }

        products, error = self.search(
            query=query,
            limit=5,
        )

        if error:

            result["teste_busca"] = {
                "ok": False,
                "status": error.get(
                    "status"
                ),
                "mensagem": error.get(
                    "message"
                ),
                "tipo": error.get(
                    "type"
                ),
            }

            return result

        result["ok"] = True

        result["teste_busca"] = {
            "ok": True,
            "status": 200,
            "quantidade": len(
                products
            ),
        }

        return result
