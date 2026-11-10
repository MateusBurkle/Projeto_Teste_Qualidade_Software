"""FASE REFACTOR - Extrato (RF-05, RC-01, RC-02, RS-08). Mesmo comportamento da fase Green."""
from datetime import datetime, time
from dataclasses import dataclass, field
from decimal import Decimal

GERADO = "GERADO"
PERIODO_INVALIDO = "PERIODO_INVALIDO"
NEGADO = "NEGADO"
FALHA = "FALHA"

CREDITO = "CREDITO"
DEBITO = "DEBITO"

MSG_GERADO = "Extrato gerado."
MSG_NEGADO = "Acesso negado a esta conta."
MSG_PERIODO_INVALIDO = "A data final deve ser igual ou posterior a data inicial."
MSG_FALHA = "Nao foi possivel gerar o extrato agora. Tente novamente."

ZERO = Decimal("0.00")


@dataclass
class Lancamento:
    data: datetime
    tipo: str
    valor: Decimal
    descricao: str = ""


@dataclass
class ResultadoExtrato:
    status: str
    mensagem: str
    lancamentos: list = field(default_factory=list)
    saldo_inicial: Decimal = ZERO
    saldo_final: Decimal = ZERO


def _movimento(lancamento):
    """Efeito do lancamento no saldo: credito soma, debito subtrai."""
    return lancamento.valor if lancamento.tipo == CREDITO else -lancamento.valor


def _somar_movimentos(lancamentos, saldo):
    return saldo + sum((_movimento(l) for l in lancamentos), ZERO)


def _limites_do_periodo(data_inicial, data_final):
    """Dia inicial a 00:00:00 e dia final ate 23:59:59 (periodo fechado)."""
    return datetime.combine(data_inicial, time.min), datetime.combine(data_final, time.max)


class ExtratoService:
    def __init__(self, ponto_de_falha=None):
        self._ponto_de_falha = ponto_de_falha
        self._contas = {}  # conta -> (usuario, saldo de abertura)
        self._lancamentos = {}  # conta -> lista na ordem de insercao

    def cadastrar_conta(self, usuario, conta, saldo_inicial):
        self._contas[conta] = (usuario, saldo_inicial)
        self._lancamentos[conta] = []

    def registrar_lancamento(self, conta, data, tipo, valor, descricao=""):
        self._lancamentos[conta].append(Lancamento(data, tipo, valor, descricao))

    def gerar_extrato(self, usuario, conta, data_inicial, data_final):
        try:
            if self._ponto_de_falha is not None:
                self._ponto_de_falha()
            return self._gerar(usuario, conta, data_inicial, data_final)
        except Exception:
            return ResultadoExtrato(FALHA, MSG_FALHA)

    def _gerar(self, usuario, conta, data_inicial, data_final):
        if not self._conta_do_usuario(usuario, conta):
            return ResultadoExtrato(NEGADO, MSG_NEGADO)
        if data_final < data_inicial:
            return ResultadoExtrato(PERIODO_INVALIDO, MSG_PERIODO_INVALIDO)
        inicio, fim = _limites_do_periodo(data_inicial, data_final)
        anteriores, periodo = self._separar_lancamentos(conta, inicio, fim)
        saldo_inicial = _somar_movimentos(anteriores, self._contas[conta][1])
        saldo_final = _somar_movimentos(periodo, saldo_inicial)
        return ResultadoExtrato(GERADO, MSG_GERADO, periodo, saldo_inicial, saldo_final)

    def _conta_do_usuario(self, usuario, conta):
        return conta in self._contas and self._contas[conta][0] == usuario

    def _separar_lancamentos(self, conta, inicio, fim):
        """Devolve (anteriores ao periodo, dentro do periodo), em ordem cronologica."""
        anteriores, periodo = [], []
        for l in sorted(self._lancamentos[conta], key=lambda x: x.data):  # sorted e estavel
            if l.data < inicio:
                anteriores.append(l)
            elif l.data <= fim:
                periodo.append(l)
        return anteriores, periodo
