"""Testes do modulo Login (CT-L01 a CT-L10) - Plano de Testes, secao 4.3.1.

Escritos primeiro (fase RED) e mantidos SEM alteracao nas fases Green e Refactor.
Ciclos: 1 login basico | 2 bloqueio | 3 segundo fator (token) | 4 tabela de decisao | 5 seguranca.
"""
import logging

import pytest

from nextbank.login import (
    ACESSO_LIBERADO,
    BLOQUEADA,
    ENTRADA_INVALIDA,
    NEGADO,
    SEGUNDO_FATOR_NECESSARIO,
    AuthService,
)

CPF = "529.982.247-25"
SENHA = "Senha@123"


class RelogioFalso:
    """Relogio controlavel para testar a expiracao do token (valor limite)."""

    def __init__(self):
        self.t = 0.0

    def agora(self):
        return self.t

    def avancar(self, segundos):
        self.t += segundos


class SmsFalso:
    """Mock do servico de SMS: guarda os codigos enviados."""

    def __init__(self):
        self.enviados = []

    def enviar(self, cpf, codigo):
        self.enviados.append((cpf, codigo))

    def ultimo_codigo(self):
        return self.enviados[-1][1]


@pytest.fixture
def relogio():
    return RelogioFalso()


@pytest.fixture
def sms():
    return SmsFalso()


@pytest.fixture
def svc(relogio, sms):
    servico = AuthService(relogio=relogio, sms=sms, max_tentativas=5, ttl_token=120)
    servico.cadastrar_usuario(CPF, SENHA)
    return servico


def codigo_diferente(real):
    return "000000" if real != "000000" else "111111"


# ---------------- Ciclo 1: login basico (RF-01, RF-02) ----------------
def test_ct_l01_credenciais_validas_solicitam_segundo_fator(svc, sms):
    r = svc.login(CPF, SENHA)
    assert r.status == SEGUNDO_FATOR_NECESSARIO
    assert r.status != ACESSO_LIBERADO
    assert len(sms.enviados) == 1


def test_ct_l02_senha_invalida_negada_com_mensagem_generica(svc, sms):
    r = svc.login(CPF, "senha-errada")
    assert r.status == NEGADO
    assert "inválidas" in r.mensagem
    assert sms.enviados == []


# ---------------- Ciclo 2: bloqueio (RS-01) ----------------
def test_ct_l03_quarta_tentativa_invalida_conta_ainda_ativa(svc):
    for _ in range(4):
        assert svc.login(CPF, "errada").status == NEGADO
    assert svc.conta_bloqueada(CPF) is False
    assert svc.tentativas_falhas(CPF) == 4
    assert svc.login(CPF, SENHA).status == SEGUNDO_FATOR_NECESSARIO


def test_ct_l04_quinta_tentativa_invalida_bloqueia_conta(svc, sms):
    resultados = [svc.login(CPF, "errada") for _ in range(5)]
    assert resultados[-1].status == BLOQUEADA
    assert svc.conta_bloqueada(CPF) is True
    r = svc.login(CPF, SENHA)  # mesmo com a senha correta
    assert r.status == BLOQUEADA
    assert sms.enviados == []


# ---------------- Ciclo 3: segundo fator / token (RS-02) ----------------
def test_ct_l05_token_valido_dentro_do_prazo(svc, sms, relogio):
    svc.login(CPF, SENHA)
    relogio.avancar(119)  # 1 min 59 s
    assert svc.confirmar_segundo_fator(CPF, sms.ultimo_codigo()).status == ACESSO_LIBERADO


def test_ct_l06_token_expirado(svc, sms, relogio):
    svc.login(CPF, SENHA)
    relogio.avancar(121)  # 2 min 01 s
    assert svc.confirmar_segundo_fator(CPF, sms.ultimo_codigo()).status == NEGADO


def test_ct_l07_token_nao_pode_ser_reutilizado(svc, sms):
    svc.login(CPF, SENHA)
    codigo = sms.ultimo_codigo()
    assert svc.confirmar_segundo_fator(CPF, codigo).status == ACESSO_LIBERADO
    assert svc.confirmar_segundo_fator(CPF, codigo).status == NEGADO


# ---------------- Ciclo 4: tabela de decisao (RF-02, RS-01) ----------------
def test_ct_l08_regra1_senha_ok_token_ok_conta_ativa_libera(svc, sms):
    svc.login(CPF, SENHA)
    assert svc.confirmar_segundo_fator(CPF, sms.ultimo_codigo()).status == ACESSO_LIBERADO


def test_ct_l08_regra2_senha_ok_token_invalido_nega(svc, sms):
    svc.login(CPF, SENHA)
    errado = codigo_diferente(sms.ultimo_codigo())
    assert svc.confirmar_segundo_fator(CPF, errado).status == NEGADO


def test_ct_l08_regra3_senha_errada_nega_e_conta_tentativa(svc):
    assert svc.login(CPF, "errada").status == NEGADO
    assert svc.tentativas_falhas(CPF) == 1


def test_ct_l08_regra4_senha_ok_token_ok_conta_bloqueada_nega(svc, sms):
    svc.login(CPF, SENHA)
    codigo = sms.ultimo_codigo()
    for _ in range(5):
        svc.login(CPF, "errada")
    r = svc.confirmar_segundo_fator(CPF, codigo)
    assert r.status == BLOQUEADA
    assert r.status != ACESSO_LIBERADO


# ---------------- Ciclo 5: seguranca (RS-06, RS-07) ----------------
@pytest.mark.parametrize("payload", ["' OR '1'='1", "52998224725'; DROP TABLE usuarios;--"])
def test_ct_l09_injecao_sql_no_cpf_e_rejeitada(svc, payload):
    r = svc.login(payload, SENHA)
    assert r.status == ENTRADA_INVALIDA
    texto = r.mensagem.lower()
    for termo in ("sql", "syntax", "traceback", "exception", "usuarios", payload.lower()):
        assert termo not in texto


def test_ct_l10_senha_nao_aparece_em_resposta_nem_em_log(svc, caplog):
    caplog.set_level(logging.DEBUG)
    outra = "Outra@456"
    r1 = svc.login(CPF, SENHA)
    r2 = svc.login(CPF, outra)
    for r in (r1, r2):
        assert SENHA not in repr(r) and outra not in repr(r)
    assert len(caplog.records) > 0  # ha log de auditoria
    assert SENHA not in caplog.text and outra not in caplog.text
