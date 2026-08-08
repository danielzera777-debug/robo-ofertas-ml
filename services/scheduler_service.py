import threading
import time
from datetime import datetime


class SchedulerService:

    def __init__(self):

        self._thread = None
        self._rodando = False
        self._intervalo = 3600
        self._funcao = None
        self._ultimo_inicio = None
        self._ultimo_erro = None

    def configurar(
        self,
        funcao,
        intervalo=3600
    ):

        if not callable(funcao):

            raise ValueError(
                "A função do agendador "
                "precisa ser executável."
            )

        try:

            intervalo = int(
                intervalo
            )

        except (
            ValueError,
            TypeError
        ):

            intervalo = 3600

        if intervalo < 60:

            intervalo = 60

        self._funcao = funcao
        self._intervalo = intervalo

    def executar_agora(self):

        if not callable(
            self._funcao
        ):

            return {
                "sucesso": False,
                "erro":
                    "Nenhuma função configurada."
            }

        self._ultimo_inicio = (
            datetime.now()
        )

        try:

            resultado = (
                self._funcao()
            )

            self._ultimo_erro = None

            return {
                "sucesso": True,
                "resultado":
                    resultado
            }

        except Exception as erro:

            self._ultimo_erro = str(
                erro
            )

            return {
                "sucesso": False,
                "erro":
                    str(erro)
            }

    def _loop(self):

        while self._rodando:

            self.executar_agora()

            inicio = time.time()

            while (
                self._rodando
                and (
                    time.time()
                    - inicio
                    < self._intervalo
                )
            ):

                time.sleep(1)

    def iniciar(self):

        if self._rodando:

            return {
                "sucesso": True,
                "mensagem":
                    "Agendador já está rodando."
            }

        if not callable(
            self._funcao
        ):

            return {
                "sucesso": False,
                "erro":
                    "Nenhuma função configurada."
            }

        self._rodando = True

        self._thread = threading.Thread(
            target=self._loop,
            daemon=True
        )

        self._thread.start()

        return {
            "sucesso": True,
            "mensagem":
                "Agendador iniciado."
        }

    def parar(self):

        if not self._rodando:

            return {
                "sucesso": True,
                "mensagem":
                    "Agendador já está parado."
            }

        self._rodando = False

        return {
            "sucesso": True,
            "mensagem":
                "Agendador parado."
        }

    def rodando(self):

        return self._rodando

    def status(self):

        return {
            "rodando":
                self._rodando,
            "intervalo":
                self._intervalo,
            "ultimo_inicio":
                (
                    self._ultimo_inicio.isoformat()
                    if self._ultimo_inicio
                    else None
                ),
            "ultimo_erro":
                self._ultimo_erro
        }

    def alterar_intervalo(
        self,
        intervalo
    ):

        try:

            intervalo = int(
                intervalo
            )

        except (
            ValueError,
            TypeError
        ):

            return {
                "sucesso": False,
                "erro":
                    "Intervalo inválido."
            }

        if intervalo < 60:

            return {
                "sucesso": False,
                "erro":
                    "O intervalo mínimo "
                    "é de 60 segundos."
            }

        self._intervalo = intervalo

        return {
            "sucesso": True,
            "intervalo":
                intervalo
        }

    def executar_ciclo(
        self,
        funcao=None
    ):

        tarefa = (
            funcao
            or self._funcao
        )

        if not callable(tarefa):

            return {
                "sucesso": False,
                "erro":
                    "Nenhuma função disponível."
            }

        try:

            inicio = datetime.now()

            resultado = tarefa()

            return {
                "sucesso": True,
                "inicio":
                    inicio.isoformat(),
                "resultado":
                    resultado
            }

        except Exception as erro:

            self._ultimo_erro = str(
                erro
            )

            return {
                "sucesso": False,
                "erro":
                    str(erro)
            }
