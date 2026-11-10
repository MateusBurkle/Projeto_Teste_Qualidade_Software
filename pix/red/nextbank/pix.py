"""FASE RED - apenas a interface (stub). Nada esta implementado; os testes devem FALHAR."""
from dataclasses import dataclass
from decimal import Decimal

CONCLUIDA = "CONCLUIDA"
RECUSADA = "RECUSADA"
BLOQUEADA = "BLOQUEADA"
RETIDA_ANALISE = "RETIDA_ANALISE"
NEGADO = "NEGADO"
FALHA = "FALHA"

LIMITE_ALTO_VALOR = Decimal("7000.00")  # RS-03 (Word, Quadro 9)


@dataclass
class ResultadoPix:
    status: str
    mensagem: str
    exige_autenticacao: bool = False


@dataclass
class RegistroAuditoria:
    evento: str
    usuario: str
    valor: Decimal
    destino: str
    data_hora: object


class PixService:
    def __init__(self, relogio, antifraude, limite_alto_valor=LIMITE_ALTO_VALOR, ponto_de_falha=None):
        pass

    def cadastrar_conta(self, usuario, conta, saldo):
        pass  # ainda sem comportamento

    def cadastrar_chave(self, chave, conta):
        pass  # ainda sem comportamento

    def saldo(self, conta):
        raise NotImplementedError

    def saldo_reservado(self, conta):
        raise NotImplementedError

    def transferir(self, usuario, conta_origem, chave_destino, valor, autenticacao_adicional=False):
        raise NotImplementedError

    def registros_auditoria(self):
        raise NotImplementedError
