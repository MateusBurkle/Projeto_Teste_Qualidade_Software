"""Testes de SEGURANCA basicos (logica em memoria) - CT-S01 a CT-S08.

Nao e pentest nem teste de API HTTP. Servicos externos (SMS, antifraude, relogio) sao fakes;
CPFs e senhas sao ficticios. Teste que PASSA = controle existe; que FALHA = vulnerabilidade
(registrada como incidente no RESUMO_SEGURANCA.md, sem corrigir o codigo).
Mapa de requisitos (Quadros 8 e 9 do Word, aprovado): CT-S01=RS-07, CT-S02=RS-01, CT-S03=RS-02,
CT-S04=RS-08, CT-S05=RS-07, CT-S06=RS-05 e RS-06, CT-S07=RS-07, CT-S08=RS-03.
"""
import logging
from datetime import date, datetime
from decimal import Decimal

import pytest

from nextbank.extrato import ExtratoService, NEGADO as E_NEGADO
from nextbank.login import (
    ACESSO_LIBERADO, BLOQUEADA, ENTRADA_INVALIDA, NEGADO, AuthService,
)
from nextbank.pix import BLOQUEADA as P_BLOQUEADA, CONCLUIDA, NEGADO as P_NEGADO, RECUSADA, PixService

D = Decimal
SENHA = "Senha@123"
CPF_A, CPF_B = "390.533.447-05", "168.995.350-09"
ID_A, ID_B = "39053344705", "16899535009"
CONTA_A, CONTA_B = "0001-1", "0002-2"
CHAVE_B = "chave-b"
HOJE = datetime(2026, 11, 7, 14, 0, 0)
MALICIOSOS = ["' OR 1=1 --", "<script>alert(1)</script>"]


class Relogio:
    def __init__(self):
        self.t = 0.0

    def agora(self):
        return self.t


class RelogioData:
    def agora(self):
        return HOJE


class SmsFalso:
    def __init__(self):
        self.enviados = []

    def enviar(self, cpf, codigo):
        self.enviados.append((cpf, codigo))

    def ultimo(self):
        return self.enviados[-1][1]


class AntifraudeFalso:
    def analisar(self, usuario, valor, quando):
        return False


@pytest.fixture
def auth():
    relogio, sms = Relogio(), SmsFalso()
    a = AuthService(relogio, sms)
    a.cadastrar_usuario(CPF_A, SENHA)
    a.cadastrar_usuario(CPF_B, SENHA)
    return a, relogio, sms


@pytest.fixture
def pix():
    p = PixService(RelogioData(), AntifraudeFalso())
    p.cadastrar_conta(ID_A, CONTA_A, D("20000.00"))
    p.cadastrar_conta(ID_B, CONTA_B, D("100.00"))
    p.cadastrar_chave(CHAVE_B, CONTA_B)
    p.cadastrar_chave("chave-a", CONTA_A)
    return p


# CT-S01 (RS-07) entrada maliciosa
@pytest.mark.parametrize("texto", MALICIOSOS)
def test_CT_S01_entrada_maliciosa_recusada(auth, pix, texto):
    a, _, sms = auth
    r = a.login(texto, SENHA)  # no CPF
    assert r.status == ENTRADA_INVALIDA
    r = a.login(CPF_A, texto)  # na senha
    assert r.status == NEGADO
    assert sms.enviados == []
    r = pix.transferir(ID_A, CONTA_A, texto, D("10.00"))  # na chave PIX
    assert r.status == RECUSADA
    assert pix.saldo(CONTA_A) == D("20000.00")


# CT-S02 (RS-01) forca bruta
def test_CT_S02_bloqueio_na_quinta_tentativa(auth):
    a, _, _ = auth
    for _ in range(4):
        assert a.login(CPF_A, "errada").status == NEGADO
    assert a.login(CPF_A, "errada").status == BLOQUEADA
    assert a.login(CPF_A, SENHA).status == BLOQUEADA  # senha correta apos bloqueio
    assert a.conta_bloqueada(CPF_A)


# CT-S03 (RS-02) token
def test_CT_S03_token_expira_em_2_min(auth):
    a, relogio, sms = auth
    a.login(CPF_A, SENHA)
    relogio.t = 121
    assert a.confirmar_segundo_fator(CPF_A, sms.ultimo()).status == NEGADO


def test_CT_S03_token_nao_reutilizavel(auth):
    a, _, sms = auth
    a.login(CPF_A, SENHA)
    codigo = sms.ultimo()
    assert a.confirmar_segundo_fator(CPF_A, codigo).status == ACESSO_LIBERADO
    assert a.confirmar_segundo_fator(CPF_A, codigo).status == NEGADO


def test_CT_S03_token_de_outro_usuario_recusado(auth):
    a, _, sms = auth
    a.login(CPF_A, SENHA)
    codigo_a = sms.ultimo()
    a.login(CPF_B, SENHA)
    assert a.confirmar_segundo_fator(CPF_B, codigo_a).status == NEGADO


# CT-S04 (RS-08) conta alheia
def test_CT_S04_extrato_de_conta_alheia_negado():
    e = ExtratoService()
    e.cadastrar_conta(ID_A, CONTA_A, D("10.00"))
    e.cadastrar_conta(ID_B, CONTA_B, D("10.00"))
    r = e.gerar_extrato(ID_A, CONTA_B, date(2026, 11, 1), date(2026, 11, 30))
    assert r.status == E_NEGADO
    assert r.lancamentos == []


def test_CT_S04_pix_de_conta_alheia_negado(pix):
    r = pix.transferir(ID_B, CONTA_A, CHAVE_B, D("10.00"))  # B tenta mover a conta de A
    assert r.status == P_NEGADO
    assert pix.saldo(CONTA_A) == D("20000.00")
    assert pix.saldo(CONTA_B) == D("100.00")


# CT-S05 (RS-07) mensagens genericas
def test_CT_S05_mensagem_igual_para_cpf_inexistente_e_senha_errada(auth):
    a, _, _ = auth
    inexistente = a.login("111.444.777-35", SENHA)
    errada = a.login(CPF_A, "errada")
    assert (inexistente.status, inexistente.mensagem) == (errada.status, errada.mensagem)


# CT-S06 (RS-05, RS-06) dados sensiveis
def test_CT_S06_cpf_mascarado_nos_logs_e_senha_ausente(auth, caplog):
    a, _, _ = auth
    with caplog.at_level(logging.DEBUG, logger="nextbank"):
        a.login(CPF_A, "errada")
        a.login(CPF_A, SENHA)
    texto = caplog.text
    assert ID_A not in texto and CPF_A not in texto
    assert "errada" not in texto and SENHA not in texto


def test_CT_S06_cpf_mascarado_na_auditoria(pix):
    pix.transferir(ID_A, CONTA_A, CHAVE_B, D("8000.00"), autenticacao_adicional=True)
    for reg in pix.registros_auditoria():
        assert ID_A not in str(reg) and CPF_A not in str(reg)


def test_CT_S06_senha_nao_fica_em_texto_puro(auth):
    a, _, _ = auth
    r = a.login(CPF_A, SENHA)
    assert SENHA not in r.mensagem
    usuario = a._usuarios[ID_A]
    assert SENHA.encode() not in usuario.senha_hash and SENHA not in repr(usuario)


# CT-S07 (RS-07) valores invalidos no PIX
@pytest.mark.parametrize("valor", [D("-10.00"), D("0"), "abc", D("1e30")])
def test_CT_S07_valor_invalido_recusado(pix, valor):
    try:
        r = pix.transferir(ID_A, CONTA_A, CHAVE_B, valor)
    except Exception as erro:  # erro interno = falha do teste
        pytest.fail(f"erro interno ao receber valor {valor!r}: {type(erro).__name__}")
    assert r.status == RECUSADA
    assert pix.saldo(CONTA_A) == D("20000.00")


# CT-S08 (RS-03) alto valor
def test_CT_S08_alto_valor_exige_confirmacao_extra(pix):
    r = pix.transferir(ID_A, CONTA_A, CHAVE_B, D("7000.01"))
    assert r.status == P_BLOQUEADA and r.exige_autenticacao
    assert pix.saldo(CONTA_A) == D("20000.00")


def test_CT_S08_alto_valor_nao_contornado_por_valor_texto_ou_flag_falsa(pix):
    r = pix.transferir(ID_A, CONTA_A, CHAVE_B, D("9000.00"), autenticacao_adicional=False)
    assert r.status == P_BLOQUEADA
    try:
        r = pix.transferir(ID_A, CONTA_A, CHAVE_B, "9000.00")
        assert r.status != CONCLUIDA
    except TypeError:
        pass  # recusado por erro (nao contornou); o erro em si e tratado no CT-S07
    assert pix.saldo(CONTA_A) == D("20000.00")
    assert pix.saldo(CONTA_B) == D("100.00")


def test_CT_S08_limite_exato_nao_exige(pix):
    assert pix.transferir(ID_A, CONTA_A, CHAVE_B, D("7000.00")).status == CONCLUIDA
