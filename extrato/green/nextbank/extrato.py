"""FASE GREEN - implementacao minima do Extrato (RF-05, RC-01, RC-02, RS-08)."""
from datetime import datetime, time
from dataclasses import dataclass, field
from decimal import Decimal

GERADO = "GERADO"
PERIODO_INVALIDO = "PERIODO_INVALIDO"
NEGADO = "NEGADO"
FALHA = "FALHA"

CREDITO = "CREDITO"
DEBITO = "DEBITO"


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
    saldo_inicial: Decimal = Decimal("0.00")
    saldo_final: Decimal = Decimal("0.00")


def _movimento(lancamento):
    return lancamento.valor if lancamento.tipo == CREDITO else -lancamento.valor


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
            return ResultadoExtrato(FALHA, "Nao foi possivel gerar o extrato agora. Tente novamente.")

    def _gerar(self, usuario, conta, data_inicial, data_final):
        if conta not in self._contas or self._contas[conta][0] != usuario:
            return ResultadoExtrato(NEGADO, "Acesso negado a esta conta.")
        if data_final < data_inicial:
            return ResultadoExtrato(PERIODO_INVALIDO, "A data final deve ser igual ou posterior a data inicial.")
        inicio = datetime.combine(data_inicial, time.min)
        fim = datetime.combine(data_final, time.max)
        saldo = self._contas[conta][1]
        periodo = []
        for l in sorted(self._lancamentos[conta], key=lambda x: x.data):  # sorted e estavel
            if l.data < inicio:
                saldo += _movimento(l)
            elif l.data <= fim:
                periodo.append(l)
        saldo_final = saldo + sum((_movimento(l) for l in periodo), Decimal("0.00"))
        return ResultadoExtrato(GERADO, "Extrato gerado.", periodo, saldo, saldo_final)
