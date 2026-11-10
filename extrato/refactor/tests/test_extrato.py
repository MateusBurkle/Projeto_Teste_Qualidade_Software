"""Testes do modulo Extrato (CT-E01 a CT-E04 e CT-E07 a CT-E10) - Projeto_Parte2_novo.docx, secao 4 (Quadro 13).

Escritos primeiro (fase RED) e mantidos SEM alteracao nas fases Green e Refactor.
Ciclos: 1 extrato por periodo (RF-05) | 2 falha e nova tentativa (RC-02) | 3 grande volume (RC-01)
        | 4 acesso de outro cliente, integrado ao AuthService do Login (RS-08).
CT-E05, CT-E06 (consistencia de saldo e sem omissao/duplicidade) e CT-E09 (1.000 requisicoes):
ficam para o Locust (meta M5).
Servicos externos sao fakes; dados ficticios. Falha do servico simulada por ponto_de_falha (como no PIX).
Convencoes: lancamento tem datetime (com hora); periodo em date, fechado nas duas pontas, dia final
incluido ate 23:59:59. Ordem: cronologica e, em empate, de insercao. saldo_inicial = saldo de abertura +
lancamentos anteriores a data inicial; saldo_final = saldo_inicial + creditos - debitos do periodo.
Mensagens de erro: nao vazias, sem 'Traceback' nem 'RuntimeError' (texto exato nao fixado).
"""
import time
from datetime import date, datetime
from decimal import Decimal

import pytest

from nextbank.extrato import (
    CREDITO,
    DEBITO,
    FALHA,
    GERADO,
    NEGADO,
    PERIODO_INVALIDO,
    ExtratoService,
)
from nextbank.login import ACESSO_LIBERADO, AuthService

D = Decimal
USUARIO_A = "usuario_a"
USUARIO_B = "usuario_b"
CONTA_A = "0001-1"
CONTA_B = "0002-2"
SALDO_ABERTURA = D("1000.00")  # saldo de A antes do primeiro lancamento
TEMPO_MAXIMO_S = 5.0  # CT-E08: "dentro do tempo" (limite adotado nos testes)
CPF_A = "390.533.447-05"  # CPFs ficticios
CPF_B = "168.995.350-09"


@pytest.fixture
def extrato():
    svc = ExtratoService()
    svc.cadastrar_conta(USUARIO_A, CONTA_A, SALDO_ABERTURA)
    svc.cadastrar_conta(USUARIO_B, CONTA_B, D("50.00"))
    # Setembro (antes do periodo de outubro)
    svc.registrar_lancamento(CONTA_A, datetime(2026, 9, 20, 10, 0, 0), CREDITO, D("200.00"), "deposito")
    # Outubro
    svc.registrar_lancamento(CONTA_A, datetime(2026, 10, 1, 0, 0, 0), CREDITO, D("500.00"), "salario")
    svc.registrar_lancamento(CONTA_A, datetime(2026, 10, 15, 14, 30, 0), DEBITO, D("120.00"), "pix enviado")
    svc.registrar_lancamento(CONTA_A, datetime(2026, 10, 31, 23, 59, 59), DEBITO, D("80.00"), "boleto")
    # Novembro (depois do periodo de outubro)
    svc.registrar_lancamento(CONTA_A, datetime(2026, 11, 2, 9, 0, 0), CREDITO, D("999.00"), "deposito")
    return svc


# ---------------- Ciclo 1: extrato por periodo (RF-05) ----------------
def test_ct_e01_periodo_valido_lista_todos_os_lancamentos(extrato):
    r = extrato.gerar_extrato(USUARIO_A, CONTA_A, date(2026, 10, 1), date(2026, 10, 31))
    assert r.status == GERADO
    assert [l.descricao for l in r.lancamentos] == ["salario", "pix enviado", "boleto"]
    assert r.saldo_inicial == D("1200.00")
    assert r.saldo_final == D("1200.00") + D("500.00") - D("120.00") - D("80.00")


def test_ct_e02_data_final_menor_que_inicial_retorna_erro(extrato):
    r = extrato.gerar_extrato(USUARIO_A, CONTA_A, date(2026, 10, 31), date(2026, 10, 1))
    assert r.status == PERIODO_INVALIDO
    assert r.mensagem.strip() != ""
    assert "Traceback" not in r.mensagem and "RuntimeError" not in r.mensagem
    assert r.lancamentos == []


def test_ct_e03_periodo_de_um_dia_retorna_lancamentos_do_dia_ate_23_59_59():
    # RF-05: dia final incluido ate 23:59:59; horas diferentes; insercao fora de ordem; empate de horario.
    svc = ExtratoService()
    svc.cadastrar_conta(USUARIO_A, CONTA_A, SALDO_ABERTURA)
    ins = svc.registrar_lancamento
    ins(CONTA_A, datetime(2026, 10, 15, 23, 59, 59), DEBITO, D("20.00"), "quase meia-noite")
    ins(CONTA_A, datetime(2026, 10, 14, 23, 59, 59), CREDITO, D("10.00"), "dia anterior")
    ins(CONTA_A, datetime(2026, 10, 15, 12, 30, 0), DEBITO, D("30.00"), "almoco")
    ins(CONTA_A, datetime(2026, 10, 15, 0, 0, 0), CREDITO, D("100.00"), "inicio do dia")
    ins(CONTA_A, datetime(2026, 10, 15, 12, 30, 0), DEBITO, D("5.00"), "cafe")  # empate com "almoco"
    ins(CONTA_A, datetime(2026, 10, 16, 0, 0, 0), CREDITO, D("500.00"), "dia seguinte")

    r = svc.gerar_extrato(USUARIO_A, CONTA_A, date(2026, 10, 15), date(2026, 10, 15))

    assert r.status == GERADO
    assert [l.descricao for l in r.lancamentos] == ["inicio do dia", "almoco", "cafe", "quase meia-noite"]
    assert r.saldo_inicial == D("1010.00")
    assert r.saldo_final == D("1055.00")


def test_ct_e04_periodo_sem_lancamentos_retorna_extrato_vazio_com_saldo_correto(extrato):
    r = extrato.gerar_extrato(USUARIO_A, CONTA_A, date(2026, 8, 1), date(2026, 8, 31))
    assert r.status == GERADO
    assert r.lancamentos == []
    assert r.saldo_inicial == SALDO_ABERTURA  # nenhum lancamento antes de agosto
    assert r.saldo_final == SALDO_ABERTURA


# ---------------- Ciclo 2: falha e nova tentativa (RC-02) ----------------
def test_ct_e07_falha_na_geracao_retorna_mensagem_clara_e_nova_tentativa_funciona():
    falhas = [True]  # falha simulada apenas na 1a chamada

    def falha_simulada():
        if falhas:
            falhas.pop()
            raise RuntimeError("falha simulada no servico de extrato")

    svc = ExtratoService(ponto_de_falha=falha_simulada)
    svc.cadastrar_conta(USUARIO_A, CONTA_A, SALDO_ABERTURA)
    svc.registrar_lancamento(CONTA_A, datetime(2026, 10, 10, 9, 0, 0), CREDITO, D("300.00"), "deposito")

    r1 = svc.gerar_extrato(USUARIO_A, CONTA_A, date(2026, 10, 1), date(2026, 10, 31))
    assert r1.status == FALHA
    assert r1.mensagem.strip() != ""
    assert "Traceback" not in r1.mensagem and "RuntimeError" not in r1.mensagem

    r2 = svc.gerar_extrato(USUARIO_A, CONTA_A, date(2026, 10, 1), date(2026, 10, 31))  # nova tentativa
    assert r2.status == GERADO
    assert len(r2.lancamentos) == 1  # sem perda de dados
    assert r2.saldo_final == D("1300.00")


# ---------------- Ciclo 3: grande volume (RC-01) ----------------
def test_ct_e08_dez_mil_lancamentos_sao_gerados_sem_erro_dentro_do_tempo():
    svc = ExtratoService()
    svc.cadastrar_conta(USUARIO_A, CONTA_A, D("0.00"))
    for i in range(10000):
        svc.registrar_lancamento(CONTA_A, datetime(2026, 10, 1 + i % 31, i % 24, 0, 0), CREDITO, D("1.00"), f"lancamento {i}")

    inicio = time.perf_counter()
    r = svc.gerar_extrato(USUARIO_A, CONTA_A, date(2026, 10, 1), date(2026, 10, 31))
    duracao = time.perf_counter() - inicio

    assert r.status == GERADO
    assert len(r.lancamentos) == 10000
    assert r.saldo_final == D("10000.00")
    assert duracao < TEMPO_MAXIMO_S


# ---------------- Ciclo 4: seguranca (RS-08), integrada ao AuthService ----------------
class RelogioLogin:
    """Relogio numerico (segundos) exigido pelo AuthService do Login."""

    def agora(self):
        return 0.0


class SmsFalso:
    """Mock do SMS do Login: guarda o codigo enviado ao CPF."""

    def __init__(self):
        self.enviados = {}

    def enviar(self, cpf, codigo):
        self.enviados[cpf] = codigo


def autenticar(auth, sms, cpf, senha):
    """Login completo (senha + segundo fator) via AuthService; devolve o usuario autenticado."""
    auth.login(cpf, senha)
    r = auth.confirmar_segundo_fator(cpf, sms.enviados[cpf.replace(".", "").replace("-", "")])
    assert r.status == ACESSO_LIBERADO
    return cpf


def test_ct_e10_usuario_a_autenticado_pedindo_extrato_da_conta_de_b_e_negado():
    # Integracao com o AuthService (Parte4_TDD/login): A se autentica de verdade; B nao participa do login.
    sms = SmsFalso()
    auth = AuthService(relogio=RelogioLogin(), sms=sms)
    auth.cadastrar_usuario(CPF_A, "Senha@123")
    usuario_a = autenticar(auth, sms, CPF_A, "Senha@123")

    svc = ExtratoService()
    svc.cadastrar_conta(usuario_a, CONTA_A, SALDO_ABERTURA)
    svc.cadastrar_conta(CPF_B, CONTA_B, D("300.00"))
    svc.registrar_lancamento(CONTA_B, datetime(2026, 10, 5, 9, 0, 0), CREDITO, D("40.00"), "deposito de B")

    r = svc.gerar_extrato(usuario_a, CONTA_B, date(2026, 10, 1), date(2026, 10, 31))

    assert r.status == NEGADO
    assert r.lancamentos == []  # nenhum dado de B vaza
    assert r.saldo_final == D("0.00")
