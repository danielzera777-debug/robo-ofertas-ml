"""
Robo Ofertas PRO
services/security.py

Camada central de segurança da aplicação.

Responsabilidades:
- geração de tokens aleatórios;
- geração de identificadores seguros;
- hash de valores sensíveis;
- comparação segura de hashes;
- geração de códigos temporários;
- validação básica de tokens.

IMPORTANTE:
Este arquivo NÃO armazena:
- ML_CLIENT_ID;
- ML_CLIENT_SECRET;
- access_token;
- refresh_token.

Esses valores devem permanecer nas variáveis de ambiente
ou no armazenamento seguro apropriado.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import string
from typing import Optional


# ============================================================
# CONFIGURAÇÕES
# ============================================================

DEFAULT_TOKEN_BYTES = 32
DEFAULT_CODE_LENGTH = 6


# ============================================================
# TOKEN SEGURO
# ============================================================

def generate_token(
    nbytes: int = DEFAULT_TOKEN_BYTES,
) -> str:
    """
    Gera um token criptograficamente seguro.

    Retorna uma string hexadecimal.
    """

    if not isinstance(nbytes, int):
        nbytes = DEFAULT_TOKEN_BYTES

    nbytes = max(
        16,
        min(nbytes, 128),
    )

    return secrets.token_hex(
        nbytes
    )


# ============================================================
# TOKEN URL SAFE
# ============================================================

def generate_urlsafe_token(
    nbytes: int = DEFAULT_TOKEN_BYTES,
) -> str:
    """
    Gera token seguro adequado para URLs,
    links de confirmação e identificadores temporários.
    """

    if not isinstance(nbytes, int):
        nbytes = DEFAULT_TOKEN_BYTES

    nbytes = max(
        16,
        min(nbytes, 128),
    )

    return secrets.token_urlsafe(
        nbytes
    )


# ============================================================
# NONCE
# ============================================================

def generate_nonce(
    length: int = 32,
) -> str:
    """
    Gera um nonce seguro.

    Pode ser utilizado futuramente em:
    - CSP;
    - formulários;
    - operações internas;
    - prevenção de replay.
    """

    if not isinstance(length, int):
        length = 32

    length = max(
        16,
        min(length, 128),
    )

    alphabet = (
        string.ascii_letters
        + string.digits
    )

    return "".join(
        secrets.choice(alphabet)
        for _ in range(length)
    )


# ============================================================
# HASH SHA-256
# ============================================================

def sha256(
    value: str,
) -> str:
    """
    Calcula SHA-256 de uma string.

    Atenção:
    para senhas de usuários, prefira Argon2/PBKDF2/bcrypt.
    Esta função é destinada a identificadores, fingerprints
    e outros valores que precisem de hash simples.
    """

    if value is None:
        value = ""

    if not isinstance(value, str):
        value = str(value)

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


# ============================================================
# HMAC
# ============================================================

def hmac_sha256(
    value: str,
    secret: str,
) -> str:
    """
    Cria uma assinatura HMAC-SHA256.
    """

    if value is None:
        value = ""

    if secret is None:
        secret = ""

    if not isinstance(value, str):
        value = str(value)

    if not isinstance(secret, str):
        secret = str(secret)

    return hmac.new(
        secret.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# ============================================================
# COMPARAÇÃO SEGURA
# ============================================================

def secure_compare(
    first: str,
    second: str,
) -> bool:
    """
    Compara duas strings utilizando comparação resistente
    a ataques de timing.
    """

    if first is None:
        first = ""

    if second is None:
        second = ""

    if not isinstance(first, str):
        first = str(first)

    if not isinstance(second, str):
        second = str(second)

    return hmac.compare_digest(
        first,
        second,
    )


# ============================================================
# VERIFICAÇÃO HMAC
# ============================================================

def verify_hmac(
    value: str,
    signature: str,
    secret: str,
) -> bool:
    """
    Verifica uma assinatura HMAC.
    """

    if not signature:
        return False

    expected = hmac_sha256(
        value,
        secret,
    )

    return secure_compare(
        expected,
        signature,
    )


# ============================================================
# CÓDIGO NUMÉRICO TEMPORÁRIO
# ============================================================

def generate_numeric_code(
    length: int = DEFAULT_CODE_LENGTH,
) -> str:
    """
    Gera código numérico seguro.

    Exemplo:
        482913
    """

    if not isinstance(length, int):
        length = DEFAULT_CODE_LENGTH

    length = max(
        4,
        min(length, 12),
    )

    lower = 10 ** (length - 1)
    upper = (10 ** length) - 1

    return str(
        secrets.randbelow(
            upper - lower + 1
        ) + lower
    )


# ============================================================
# VALIDAR TOKEN
# ============================================================

def is_valid_token(
    token: Optional[str],
    minimum_length: int = 32,
) -> bool:
    """
    Verificação básica de token.

    Não verifica autorização.
    Apenas confirma que o valor possui formato
    minimamente aceitável.
    """

    if not token:
        return False

    if not isinstance(token, str):
        return False

    token = token.strip()

    if len(token) < minimum_length:
        return False

    if len(token) > 4096:
        return False

    return True


# ============================================================
# SANITIZAÇÃO DE IDENTIFICADOR
# ============================================================

def safe_identifier(
    value: str,
    max_length: int = 128,
) -> str:
    """
    Normaliza um identificador para uso interno.

    Não deve ser utilizado como substituto de escaping HTML
    ou validação específica de banco de dados.
    """

    if value is None:
        return ""

    if not isinstance(value, str):
        value = str(value)

    value = value.strip()

    allowed = (
        string.ascii_letters
        + string.digits
        + "_-."
    )

    result = "".join(
        char
        for char in value
        if char in allowed
    )

    return result[:max_length]


# ============================================================
# FINGERPRINT
# ============================================================

def fingerprint(
    value: str,
) -> str:
    """
    Gera fingerprint SHA-256.

    Útil para identificar uma informação sem armazená-la
    diretamente em logs.
    """

    return sha256(
        value
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "generate_token",
    "generate_urlsafe_token",
    "generate_nonce",
    "sha256",
    "hmac_sha256",
    "secure_compare",
    "verify_hmac",
    "generate_numeric_code",
    "is_valid_token",
    "safe_identifier",
    "fingerprint",
]
