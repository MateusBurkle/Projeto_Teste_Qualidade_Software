"""FASE GREEN - codigo minimo para os testes do PIX passarem."""
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
        self._relogio = relogio
        self._antifraude = antifraude
        self._limite = limite_alto_valor
        self._ponto_de_falha = ponto_de_falha
        self._donos = {}
        self._saldos = {}
        self._reservado = {}
        self._chaves = {}
        self._auditoria = []

    def cadastrar_conta(self, usuario, conta, saldo):
        self._donos[conta] = usuario
        self._saldos[conta] = saldo
        self._reservado[conta] = Decimal("0.00")

    def cadastrar_chave(self, chave, conta):
        self._chaves[chave] = conta

    def saldo(self, conta):
        return self._saldos[conta]

    def saldo_reservado(self, conta):
        return self._reservado[conta]

    def transferir(self, usuario, conta_origem, chave_destino, valor, autenticacao_adicional=False):
        if self._donos.get(conta_origem) != usuario:
            self._registrar(usuario, valor, chave_destino)
            return ResultadoPix(NEGADO, "Operacao negada.")
        if valor <= 0:
            return ResultadoPix(RECUSADA, "Valor invalido.")
        conta_destino = self._chaves.get(chave_destino)
        if conta_destino is None:
            return ResultadoPix(RECUSADA, "Chave PIX invalida.")
        if valor > self._saldos[conta_origem]:
            return ResultadoPix(RECUSADA, "Saldo insuficiente.")
        alto_valor = valor > self._limite
        if alto_valor and not autenticacao_adicional:
            return ResultadoPix(BLOQUEADA, "Autenticacao adicional necessaria.", exige_autenticacao=True)
        if alto_valor:
            self._registrar(usuario, valor, chave_destino)
        if self._antifraude.analisar(usuario, valor, self._relogio.agora()):
            self._saldos[conta_origem] -= valor
            self._reservado[conta_origem] += valor
            return ResultadoPix(RETIDA_ANALISE, "Transferencia retida para analise.")
        return self._debitar_e_creditar(conta_origem, conta_destino, valor)

    def _debitar_e_creditar(self, origem, destino, valor):
        saldo_origem, saldo_destino = self._saldos[origem], self._saldos[destino]
        try:
            self._saldos[origem] -= valor
            if self._ponto_de_falha:
                self._ponto_de_falha()
            self._saldos[destino] += valor
        except Exception:
            self._saldos[origem], self._saldos[destino] = saldo_origem, saldo_destino
            return ResultadoPix(FALHA, "Falha na transferencia; operacao revertida.")
        return ResultadoPix(CONCLUIDA, "Transferencia concluida.")

    def _registrar(self, usuario, valor, destino):
        self._auditoria.append(
            RegistroAuditoria("PIX", usuario, valor, destino, self._relogio.agora())
        )

    def registros_auditoria(self):
        return list(self._auditoria)
