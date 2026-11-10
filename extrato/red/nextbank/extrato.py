"""FASE RED - apenas a interface (stub). Nada esta implementado; os testes devem FALHAR."""
from datetime import datetime
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


class ExtratoService:
    def __init__(self, ponto_de_falha=None):
        pass

    def cadastrar_conta(self, usuario, conta, saldo_inicial):
        pass  # ainda sem comportamento

    def registrar_lancamento(self, conta, data, tipo, valor, descricao=""):
        pass  # ainda sem comportamento

    def gerar_extrato(self, usuario, conta, data_inicial, data_final):
        raise NotImplementedError
