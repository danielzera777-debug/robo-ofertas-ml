import logging
import os
import sys
from logging.handlers import RotatingFileHandler


LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO"
).upper()

LOG_DIR = os.getenv(
    "LOG_DIR",
    "logs"
)

LOG_FILE = os.getenv(
    "LOG_FILE",
    "robo_ofertas.log"
)


def criar_pasta_logs():

    os.makedirs(
        LOG_DIR,
        exist_ok=True
    )


def obter_nivel():

    niveis = {
        "CRITICAL":
            logging.CRITICAL,

        "ERROR":
            logging.ERROR,

        "WARNING":
            logging.WARNING,

        "INFO":
            logging.INFO,

        "DEBUG":
            logging.DEBUG
    }

    return niveis.get(
        LOG_LEVEL,
        logging.INFO
    )


def configurar_logging():

    criar_pasta_logs()

    logger = logging.getLogger()

    logger.setLevel(
        obter_nivel()
    )

    if logger.handlers:

        return logger

    formato = logging.Formatter(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console = logging.StreamHandler(
        sys.stdout
    )

    console.setLevel(
        obter_nivel()
    )

    console.setFormatter(
        formato
    )

    caminho_log = os.path.join(
        LOG_DIR,
        LOG_FILE
    )

    arquivo = RotatingFileHandler(
        caminho_log,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )

    arquivo.setLevel(
        obter_nivel()
    )

    arquivo.setFormatter(
        formato
    )

    logger.addHandler(
        console
    )

    logger.addHandler(
        arquivo
    )

    return logger


def get_logger(
    nome=None
):

    configurar_logging()

    return logging.getLogger(
        nome
    )


def log_info(
    mensagem
):

    get_logger(
        "robo-ofertas"
    ).info(
        mensagem
    )


def log_warning(
    mensagem
):

    get_logger(
        "robo-ofertas"
    ).warning(
        mensagem
    )


def log_error(
    mensagem
):

    get_logger(
        "robo-ofertas"
    ).error(
        mensagem
    )


def log_debug(
    mensagem
):

    get_logger(
        "robo-ofertas"
    ).debug(
        mensagem
    )


def log_critical(
    mensagem
):

    get_logger(
        "robo-ofertas"
    ).critical(
        mensagem
    )


# ============================================================
# CONFIGURAÇÃO AUTOMÁTICA
# ============================================================

logger = configurar_logging()
