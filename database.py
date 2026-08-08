import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime


class Database:

    def __init__(
        self,
        caminho=None
    ):

        self.caminho = (
            caminho
            or os.getenv(
                "DATABASE_PATH",
                "robo_ofertas.db"
            )
        )

        self._criar_pasta()

        self.inicializar()

    def _criar_pasta(self):

        pasta = os.path.dirname(
            os.path.abspath(
                self.caminho
            )
        )

        if pasta:

            os.makedirs(
                pasta,
                exist_ok=True
            )

    @contextmanager
    def conectar(self):

        conexao = sqlite3.connect(
            self.caminho,
            timeout=30
        )

        conexao.row_factory = (
            sqlite3.Row
        )

        try:

            yield conexao

            conexao.commit()

        except Exception:

            conexao.rollback()

            raise

        finally:

            conexao.close()

    def inicializar(self):

        with self.conectar() as db:

            db.execute(
                """
                CREATE TABLE IF NOT EXISTS
                ofertas (

                    id INTEGER PRIMARY KEY
                    AUTOINCREMENT,

                    item_id TEXT UNIQUE,

                    titulo TEXT,

                    preco REAL DEFAULT 0,

                    preco_original REAL DEFAULT 0,

                    desconto REAL DEFAULT 0,

                    link TEXT,

                    imagem TEXT,

                    categoria TEXT,

                    vendedor TEXT,

                    status TEXT DEFAULT 'nova',

                    criado_em TEXT,

                    atualizado_em TEXT

                )
                """
            )

            db.execute(
                """
                CREATE TABLE IF NOT EXISTS
                publicacoes (

                    id INTEGER PRIMARY KEY
                    AUTOINCREMENT,

                    oferta_id INTEGER,

                    canal TEXT,

                    destinatario TEXT,

                    mensagem TEXT,

                    imagem TEXT,

                    status TEXT DEFAULT 'pendente',

                    resposta TEXT,

                    criado_em TEXT,

                    enviado_em TEXT,

                    FOREIGN KEY (
                        oferta_id
                    )
                    REFERENCES ofertas(id)

                )
                """
            )

            db.execute(
                """
                CREATE TABLE IF NOT EXISTS
                configuracoes (

                    chave TEXT PRIMARY KEY,

                    valor TEXT,

                    atualizado_em TEXT

                )
                """
            )

    # =========================================================
    # OFERTAS
    # =========================================================

    def salvar_oferta(
        self,
        oferta
    ):

        if not isinstance(
            oferta,
            dict
        ):
            return None

        item_id = oferta.get(
            "id"
        )

        if not item_id:
            return None

        agora = datetime.now().isoformat()

        with self.conectar() as db:

            cursor = db.execute(
                """
                INSERT INTO ofertas (

                    item_id,
                    titulo,
                    preco,
                    preco_original,
                    desconto,
                    link,
                    imagem,
                    categoria,
                    vendedor,
                    status,
                    criado_em,
                    atualizado_em

                )

                VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?
                )

                ON CONFLICT(item_id)
                DO UPDATE SET

                    titulo = excluded.titulo,

                    preco = excluded.preco,

                    preco_original =
                        excluded.preco_original,

                    desconto =
                        excluded.desconto,

                    link =
                        excluded.link,

                    imagem =
                        excluded.imagem,

                    categoria =
                        excluded.categoria,

                    vendedor =
                        excluded.vendedor,

                    atualizado_em =
                        excluded.atualizado_em
                """,
                (
                    str(item_id),

                    oferta.get(
                        "titulo",
                        ""
                    ),

                    float(
                        oferta.get(
                            "preco",
                            0
                        ) or 0
                    ),

                    float(
                        oferta.get(
                            "preco_original",
                            0
                        ) or 0
                    ),

                    float(
                        oferta.get(
                            "desconto",
                            0
                        ) or 0
                    ),

                    oferta.get(
                        "link",
                        ""
                    ),

                    oferta.get(
                        "imagem",
                        ""
                    ),

                    oferta.get(
                        "categoria",
                        ""
                    ),

                    str(
                        oferta.get(
                            "vendedor",
                            ""
                        )
                    ),

                    oferta.get(
                        "status",
                        "nova"
                    ),

                    agora,

                    agora
                )
            )

            oferta_id = cursor.lastrowid

            if not oferta_id:

                cursor = db.execute(
                    """
                    SELECT id
                    FROM ofertas
                    WHERE item_id = ?
                    """,
                    (
                        str(item_id),
                    )
                )

                linha = cursor.fetchone()

                if linha:

                    oferta_id = linha[
                        "id"
                    ]

            return oferta_id

    def buscar_ofertas(
        self,
        limite=100,
        status=None
    ):

        limite = max(
            1,
            int(limite)
        )

        with self.conectar() as db:

            if status:

                cursor = db.execute(
                    """
                    SELECT *
                    FROM ofertas

                    WHERE status = ?

                    ORDER BY
                        desconto DESC,
                        id DESC

                    LIMIT ?
                    """,
                    (
                        status,
                        limite
                    )
                )

            else:

                cursor = db.execute(
                    """
                    SELECT *
                    FROM ofertas

                    ORDER BY
                        desconto DESC,
                        id DESC

                    LIMIT ?
                    """,
                    (
                        limite,
                    )
                )

            return [
                dict(linha)
                for linha in
                cursor.fetchall()
            ]

    def buscar_oferta(
        self,
        item_id
    ):

        with self.conectar() as db:

            cursor = db.execute(
                """
                SELECT *
                FROM ofertas

                WHERE item_id = ?

                LIMIT 1
                """,
                (
                    str(item_id),
                )
            )

            linha = cursor.fetchone()

            if not linha:
                return None

            return dict(linha)

    def atualizar_status_oferta(
        self,
        item_id,
        status
    ):

        with self.conectar() as db:

            db.execute(
                """
                UPDATE ofertas

                SET status = ?,
                    atualizado_em = ?

                WHERE item_id = ?
                """,
                (
                    status,
                    datetime.now().isoformat(),
                    str(item_id)
                )
            )

    # =========================================================
    # PUBLICAÇÕES
    # =========================================================

    def registrar_publicacao(
        self,
        oferta_id,
        canal,
        destinatario,
        mensagem="",
        imagem="",
        status="pendente",
        resposta=""
    ):

        agora = datetime.now().isoformat()

        with self.conectar() as db:

            cursor = db.execute(
                """
                INSERT INTO publicacoes (

                    oferta_id,
                    canal,
                    destinatario,
                    mensagem,
                    imagem,
                    status,
                    resposta,
                    criado_em

                )

                VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?
                )
                """,
                (
                    oferta_id,
                    canal,
                    destinatario,
                    mensagem,
                    imagem,
                    status,
                    resposta,
                    agora
                )
            )

            return cursor.lastrowid

    def atualizar_publicacao(
        self,
        publicacao_id,
        status,
        resposta=""
    ):

        enviado_em = None

        if status == "enviado":

            enviado_em = (
                datetime.now().isoformat()
            )

        with self.conectar() as db:

            db.execute(
                """
                UPDATE publicacoes

                SET status = ?,
                    resposta = ?,
                    enviado_em = ?

                WHERE id = ?
                """,
                (
                    status,
                    resposta,
                    enviado_em,
                    publicacao_id
                )
            )

    def buscar_publicacoes(
        self,
        limite=100
    ):

        limite = max(
            1,
            int(limite)
        )

        with self.conectar() as db:

            cursor = db.execute(
                """
                SELECT *
                FROM publicacoes

                ORDER BY id DESC

                LIMIT ?
                """,
                (
                    limite,
                )
            )

            return [
                dict(linha)
                for linha in
                cursor.fetchall()
            ]

    # =========================================================
    # CONFIGURAÇÕES
    # =========================================================

    def salvar_configuracao(
        self,
        chave,
        valor
    ):

        agora = datetime.now().isoformat()

        with self.conectar() as db:

            db.execute(
                """
                INSERT INTO configuracoes (
                    chave,
                    valor,
                    atualizado_em
                )

                VALUES (?, ?, ?)

                ON CONFLICT(chave)
                DO UPDATE SET

                    valor =
                        excluded.valor,

                    atualizado_em =
                        excluded.atualizado_em
                """,
                (
                    str(chave),
                    str(valor),
                    agora
                )
            )

    def obter_configuracao(
        self,
        chave,
        padrao=None
    ):

        with self.conectar() as db:

            cursor = db.execute(
                """
                SELECT valor
                FROM configuracoes

                WHERE chave = ?

                LIMIT 1
                """,
                (
                    str(chave),
                )
            )

            linha = cursor.fetchone()

            if not linha:
                return padrao

            return linha[
                "valor"
            ]

    def excluir_configuracao(
        self,
        chave
    ):

        with self.conectar() as db:

            db.execute(
                """
                DELETE FROM configuracoes

                WHERE chave = ?
                """,
                (
                    str(chave),
                )
            )

    # =========================================================
    # ESTATÍSTICAS
    # =========================================================

    def estatisticas(self):

        with self.conectar() as db:

            ofertas = db.execute(
                """
                SELECT COUNT(*) AS total
                FROM ofertas
                """
            ).fetchone()

            publicacoes = db.execute(
                """
                SELECT COUNT(*) AS total
                FROM publicacoes
                """
            ).fetchone()

            enviadas = db.execute(
                """
                SELECT COUNT(*) AS total
                FROM publicacoes

                WHERE status = 'enviado'
                """
            ).fetchone()

            return {

                "ofertas":
                    ofertas["total"],

                "publicacoes":
                    publicacoes["total"],

                "publicacoes_enviadas":
                    enviadas["total"]

            }


# =============================================================
# INSTÂNCIA PRINCIPAL
# =============================================================

db = Database()
