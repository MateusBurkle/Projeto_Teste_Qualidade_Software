"""Testes de SISTEMA (fluxo ponta a ponta) Login -> PIX -> Extrato - meta M6.

Usa o codigo final (refactor) dos tres modulos, copiado sem alteracao para nextbank/.
Decisao aprovada: PIX e Extrato sao INDEPENDENTES. O PIX nao gera lancamento no Extrato;
por isso o teste registra os lancamentos correspondentes via ExtratoService.registrar_lancamento,
como faria o sistema integrador. Transferencia RETIDA_ANALISE nao gera lancamento.
Servicos externos (SMS, antifraude, relogio) sao fakes; CPFs ficticios.
Os modulos nao possuem sessao: o "porteiro" abaixo (Sessao) e do proprio teste e so libera
PIX/Extrato para quem concluiu o login com segundo fator.
"""
from datetime import date, datetime
from decimal import Decimal

import pytest

from nextbank.extrato import CREDITO, DEBITO, GERADO, NEGADO as E_NEGADO, ExtratoService
from nextbank.login import (
    ACESSO_LIBERADO,
    BLOQUEADA as L_BLOQUEADA,
    NEGADO as L_NEGADO,
    SEGUNDO_FATOR_NECESSARIO,
    AuthService,
)
from nextbank.pix import (
    BLOQUEADA as P_BLOQUEADA,
    CONCLUIDA,
    NEGADO as P_NEGADO,
    RETIDA_ANALISE,
    PixService,
)

D = Decimal
SENHA = "Senha@123"
CPF_A = "390.533.447-05"
CPF_B = "168.995.350-09"
USER_A, USER_B = "39053344705", "16899535009"  # identificador = CPF normalizado
CONTA_A, CONTA_B = "0001-1", "0002-2"
CHAVE_B = "chave-b"
SALDO_A, SALDO_B = D("10000.00"), D("50.00")
HOJE = datetime(2026, 11, 7, 14, 0, 0)
PERIODO = (date(2026, 11, 1), date(2026, 11, 30))


class RelogioLogin:
    def __init__(self):
        self.t = 0.0

    def agora(self):
        return self.t


class RelogioPix:
    def agora(self):
        return HOJE


class SmsFalso:
    def __init__(self):
        self.enviados = []

    def enviar(self, cpf, codigo):
        self.enviados.append((cpf, codigo))

    def ultimo_codigo(self):
        return self.enviados[-1][1]


class AntifraudeFalso:
    def __init__(self, atipico=False):
        self.atipico = atipico

    def analisar(self, usuario, valor, instante):
        return self.atipico


class Sessao:
    """Porteiro do teste: so quem completou login + segundo fator acessa PIX e Extrato."""

    def __init__(self):
        self.autenticados = set()

    def exigir(self, user):
        if user not in self.autenticados:
            raise PermissionError("usuario nao autenticado")


class Sistema:
    def __init__(self, antifraude=None):
        self.relogio = RelogioLogin()
        self.sms = SmsFalso()
        self.auth = AuthService(self.relogio, self.sms)
        self.pix = PixService(RelogioPix(), antifraude or AntifraudeFalso())
        self.extrato = ExtratoService()
        self.sessao = Sessao()
        for cpf in (CPF_A, CPF_B):  # cadastro
            self.auth.cadastrar_usuario(cpf, SENHA)
        self.pix.cadastrar_conta(USER_A, CONTA_A, SALDO_A)
        self.pix.cadastrar_conta(USER_B, CONTA_B, SALDO_B)
        self.pix.cadastrar_chave(CHAVE_B, CONTA_B)
        self.extrato.cadastrar_conta(USER_A, CONTA_A, SALDO_A)
        self.extrato.cadastrar_conta(USER_B, CONTA_B, SALDO_B)

    def entrar(self, cpf, user, senha=SENHA):
        r = self.auth.login(cpf, senha)
        if r.status != SEGUNDO_FATOR_NECESSARIO:
            return r
        r = self.auth.confirmar_segundo_fator(cpf, self.sms.ultimo_codigo())
        if r.status == ACESSO_LIBERADO:
            self.sessao.autenticados.add(user)
        return r

    def pix_de_a(self, valor, **kw):
        self.sessao.exigir(USER_A)
        return self.pix.transferir(USER_A, CONTA_A, CHAVE_B, valor, **kw)

    def lancar_pix_concluido(self, valor):
        """Papel do integrador: registra no Extrato os dois lados de um PIX CONCLUIDO."""
        self.extrato.registrar_lancamento(CONTA_A, HOJE, DEBITO, valor, "pix enviado")
        self.extrato.registrar_lancamento(CONTA_B, HOJE, CREDITO, valor, "pix recebido")

    def extrato_de(self, user, conta):
        self.sessao.exigir(user)
        return self.extrato.gerar_extrato(user, conta, *PERIODO)


@pytest.fixture
def sis():
    return Sistema()


def test_st01_fluxo_feliz_login_pix_extrato_consistentes(sis):
    """ST-01 | CT-L01, CT-L05, CT-P01, CT-E01 | RF-03, RF-05: saldo do PIX = saldo do Extrato."""
    assert sis.entrar(CPF_A, USER_A).status == ACESSO_LIBERADO
    assert sis.pix_de_a(D("500.00")).status == CONCLUIDA
    sis.lancar_pix_concluido(D("500.00"))
    assert sis.entrar(CPF_B, USER_B).status == ACESSO_LIBERADO
    ea, eb = sis.extrato_de(USER_A, CONTA_A), sis.extrato_de(USER_B, CONTA_B)
    assert ea.status == eb.status == GERADO
    assert [(l.tipo, l.valor) for l in ea.lancamentos] == [(DEBITO, D("500.00"))]
    assert [(l.tipo, l.valor) for l in eb.lancamentos] == [(CREDITO, D("500.00"))]
    assert ea.saldo_final == sis.pix.saldo(CONTA_A) == D("9500.00")
    assert eb.saldo_final == sis.pix.saldo(CONTA_B) == D("550.00")


def test_st02_alto_valor_exige_autenticacao_adicional_e_depois_concilia(sis):
    """ST-02 | CT-P07, CT-P08, CT-P11, CT-E01 | RS-03 (> R$ 7.000,00): bloqueio sem nada lancado."""
    sis.entrar(CPF_A, USER_A)
    valor = D("7000.01")
    r = sis.pix_de_a(valor)
    assert r.status == P_BLOQUEADA and r.exige_autenticacao
    assert sis.pix.saldo(CONTA_A) == SALDO_A
    assert sis.extrato_de(USER_A, CONTA_A).lancamentos == []
    assert sis.pix_de_a(valor, autenticacao_adicional=True).status == CONCLUIDA
    assert len(sis.pix.registros_auditoria()) == 1
    sis.lancar_pix_concluido(valor)
    assert sis.extrato_de(USER_A, CONTA_A).saldo_final == sis.pix.saldo(CONTA_A) == SALDO_A - valor


def test_st03_pix_retido_em_analise_nao_aparece_no_extrato():
    """ST-03 | CT-P10, CT-E04 | RS-04, RF-05: retida nao gera lancamento; valor fica em saldo reservado."""
    sis = Sistema(AntifraudeFalso(atipico=True))
    sis.entrar(CPF_A, USER_A)
    assert sis.pix_de_a(D("300.00")).status == RETIDA_ANALISE
    ea = sis.extrato_de(USER_A, CONTA_A)
    assert ea.lancamentos == []
    assert sis.pix.saldo_reservado(CONTA_A) == D("300.00")
    assert sis.pix.saldo(CONTA_A) + sis.pix.saldo_reservado(CONTA_A) == ea.saldo_final == SALDO_A
    assert sis.pix.saldo(CONTA_B) == SALDO_B


def test_st04_conta_bloqueada_nao_faz_pix_nem_ve_extrato(sis):
    """ST-04 | CT-L04, CT-L08 (regra 4) | RS-01: 5a falha bloqueia; PIX e Extrato nao sao liberados."""
    for _ in range(5):
        r = sis.entrar(CPF_A, USER_A, senha="errada")
    assert r.status == L_BLOQUEADA and sis.auth.conta_bloqueada(CPF_A)
    assert sis.entrar(CPF_A, USER_A).status == L_BLOQUEADA  # senha certa, ainda bloqueada
    with pytest.raises(PermissionError):
        sis.pix_de_a(D("10.00"))
    with pytest.raises(PermissionError):
        sis.extrato_de(USER_A, CONTA_A)
    assert sis.pix.saldo(CONTA_A) == SALDO_A and sis.pix.saldo(CONTA_B) == SALDO_B


def test_st05_sem_login_ou_token_expirado_e_autenticado_nao_acessa_conta_alheia(sis):
    """ST-05 | CT-L06, CT-P17, CT-E10 | RS-08: sem 2o fator nada; com login, conta de B e negada."""
    with pytest.raises(PermissionError):
        sis.pix_de_a(D("10.00"))  # nunca fez login
    assert sis.auth.login(CPF_A, SENHA).status == SEGUNDO_FATOR_NECESSARIO
    sis.relogio.t += 121  # token de 2 min expirado
    assert sis.auth.confirmar_segundo_fator(CPF_A, sis.sms.ultimo_codigo()).status == L_NEGADO
    with pytest.raises(PermissionError):
        sis.extrato_de(USER_A, CONTA_A)
    assert sis.entrar(CPF_A, USER_A).status == ACESSO_LIBERADO  # novo token valido
    assert sis.pix.transferir(USER_A, CONTA_B, CHAVE_B, D("10.00")).status == P_NEGADO
    assert sis.extrato_de(USER_A, CONTA_B).status == E_NEGADO
    assert sis.pix.saldo(CONTA_B) == SALDO_B
