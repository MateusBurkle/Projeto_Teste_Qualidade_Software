"""Testes do modulo PIX (CT-P01 a CT-P11, CT-P14 e CT-P17) - Projeto_Parte2.docx, secao 4 (Quadro 12 e Quadro 16).

Escritos primeiro (fase RED) e mantidos SEM alteracao nas fases Green e Refactor.
Ciclos: 1 transferencia basica | 2 atomicidade e concorrencia | 3 limite de alto valor |
        4 tabela de decisao e antifraude | 5 auditoria e seguranca (integrada ao AuthService do Login).
Valores do Word: alto valor > R$ 7.000,00 (RS-03). Servicos externos (antifraude, SMS) sao fakes.
CT-P12, CT-P13 (carga e pico) e CT-P15, CT-P16 (estresse e resistencia): ficam para o Locust (meta M5).
Transferencia RETIDA_ANALISE: o valor sai do saldo disponivel e fica em saldo_reservado(conta) da origem.
"""
from datetime import datetime
from decimal import Decimal

import pytest

from nextbank.login import ACESSO_LIBERADO, AuthService
from nextbank.pix import (
    BLOQUEADA,
    CONCLUIDA,
    FALHA,
    NEGADO,
    RECUSADA,
    RETIDA_ANALISE,
    PixService,
)

D = Decimal
USUARIO_A = "usuario_a"
USUARIO_B = "usuario_b"
CONTA_A = "0001-1"
CONTA_B = "0002-2"
CHAVE_B = "529.982.247-25"  # chave PIX (CPF ficticio) da conta B
CHAVE_INEXISTENTE = "111.444.777-35"  # bem formada, mas nao cadastrada
CHAVE_MAL_FORMADA = "abc###"
SALDO_A = D("10000.00")


class RelogioFalso:
    """Relogio controlavel: devolve o instante (datetime) da operacao."""

    def __init__(self):
        self.instante = datetime(2026, 11, 7, 14, 0, 0)

    def agora(self):
        return self.instante

    def definir_hora(self, hora):
        self.instante = self.instante.replace(hour=hora)


class AntifraudeFalso:
    """Mock do antifraude: registra as consultas e sinaliza padrao atipico.

    Regra do fake (media do cliente = R$ 200,00): valor >= 10x a media ou horario entre 0h e 5h.
    """

    MEDIA = D("200.00")

    def __init__(self, forcar_atipico=None):
        self.forcar_atipico = forcar_atipico
        self.consultas = []

    def analisar(self, usuario, valor, instante):
        self.consultas.append((usuario, valor, instante))
        if self.forcar_atipico is not None:
            return self.forcar_atipico
        return valor >= 10 * self.MEDIA or instante.hour < 5


@pytest.fixture
def relogio():
    return RelogioFalso()


@pytest.fixture
def antifraude():
    return AntifraudeFalso(forcar_atipico=False)  # por padrao, padrao normal


@pytest.fixture
def pix(relogio, antifraude):
    servico = PixService(relogio=relogio, antifraude=antifraude, limite_alto_valor=D("7000.00"))
    servico.cadastrar_conta(USUARIO_A, CONTA_A, SALDO_A)
    servico.cadastrar_conta(USUARIO_B, CONTA_B, D("0.00"))
    servico.cadastrar_chave(CHAVE_B, CONTA_B)
    return servico


# ---------------- Ciclo 1: transferencia basica (RF-03) ----------------
def test_ct_p01_saldo_suficiente_conclui_transferencia(pix):
    r = pix.transferir(USUARIO_A, CONTA_A, CHAVE_B, D("100.00"))
    assert r.status == CONCLUIDA
    assert pix.saldo(CONTA_A) == SALDO_A - D("100.00")
    assert pix.saldo(CONTA_B) == D("100.00")


def test_ct_p02_saldo_insuficiente_recusa_e_saldo_inalterado(pix):
    r = pix.transferir(USUARIO_A, CONTA_A, CHAVE_B, SALDO_A + D("0.01"))
    assert r.status == RECUSADA
    assert pix.saldo(CONTA_A) == SALDO_A
    assert pix.saldo(CONTA_B) == D("0.00")


def test_ct_p03_valor_igual_ao_saldo_conclui_e_zera_saldo(relogio, antifraude):
    svc = PixService(relogio=relogio, antifraude=antifraude)
    svc.cadastrar_conta(USUARIO_A, CONTA_A, D("500.00"))
    svc.cadastrar_conta(USUARIO_B, CONTA_B, D("0.00"))
    svc.cadastrar_chave(CHAVE_B, CONTA_B)
    r = svc.transferir(USUARIO_A, CONTA_A, CHAVE_B, D("500.00"))
    assert r.status == CONCLUIDA
    assert svc.saldo(CONTA_A) == D("0.00")
    assert svc.saldo(CONTA_B) == D("500.00")


@pytest.mark.parametrize("valor", [D("0.00"), D("-1.00")])
def test_ct_p04_valor_zero_ou_negativo_e_recusado(pix, valor):
    r = pix.transferir(USUARIO_A, CONTA_A, CHAVE_B, valor)
    assert r.status == RECUSADA
    assert pix.saldo(CONTA_A) == SALDO_A
    assert pix.saldo(CONTA_B) == D("0.00")


@pytest.mark.parametrize("chave", [CHAVE_MAL_FORMADA, CHAVE_INEXISTENTE])
def test_ct_p05_chave_invalida_ou_inexistente_e_recusada(pix, chave):
    r = pix.transferir(USUARIO_A, CONTA_A, chave, D("100.00"))
    assert r.status == RECUSADA
    assert pix.saldo(CONTA_A) == SALDO_A


# ---------------- Ciclo 2: atomicidade e concorrencia (RF-04) ----------------
def test_ct_p06_falha_apos_debito_reverte_o_debito(relogio, antifraude):
    def falha_simulada():
        raise RuntimeError("falha simulada apos o debito")

    svc = PixService(relogio=relogio, antifraude=antifraude, ponto_de_falha=falha_simulada)
    svc.cadastrar_conta(USUARIO_A, CONTA_A, SALDO_A)
    svc.cadastrar_conta(USUARIO_B, CONTA_B, D("0.00"))
    svc.cadastrar_chave(CHAVE_B, CONTA_B)
    r = svc.transferir(USUARIO_A, CONTA_A, CHAVE_B, D("100.00"))
    assert r.status == FALHA
    assert svc.saldo(CONTA_A) == SALDO_A  # debito revertido
    assert svc.saldo(CONTA_B) == D("0.00")  # sem credito
    assert svc.saldo(CONTA_A) + svc.saldo(CONTA_B) == SALDO_A  # nenhum dinheiro perdido


def test_ct_p14_duas_ordens_na_mesma_conta_so_uma_conclui(relogio, antifraude):
    svc = PixService(relogio=relogio, antifraude=antifraude)
    svc.cadastrar_conta(USUARIO_A, CONTA_A, D("1000.00"))  # saldo para uma ordem apenas
    svc.cadastrar_conta(USUARIO_B, CONTA_B, D("0.00"))
    svc.cadastrar_chave(CHAVE_B, CONTA_B)
    r1 = svc.transferir(USUARIO_A, CONTA_A, CHAVE_B, D("800.00"))
    r2 = svc.transferir(USUARIO_A, CONTA_A, CHAVE_B, D("800.00"))
    assert [r1.status, r2.status].count(CONCLUIDA) == 1
    assert r2.status == RECUSADA
    assert svc.saldo(CONTA_A) == D("200.00")
    assert svc.saldo(CONTA_B) == D("800.00")  # sem saldo negativo nem dinheiro duplicado


# ---------------- Ciclo 3: limite de alto valor (RS-03) ----------------
def test_ct_p07_valor_igual_ao_limite_nao_exige_autenticacao_adicional(pix):
    r = pix.transferir(USUARIO_A, CONTA_A, CHAVE_B, D("7000.00"))
    assert r.status == CONCLUIDA
    assert r.exige_autenticacao is False


def test_ct_p08_valor_acima_do_limite_exige_autenticacao_adicional(pix):
    r = pix.transferir(USUARIO_A, CONTA_A, CHAVE_B, D("7000.01"))
    assert r.exige_autenticacao is True
    assert r.status != CONCLUIDA
    assert r.status == BLOQUEADA  # sem autenticacao adicional (decisao aprovada)
    assert pix.saldo(CONTA_A) == SALDO_A
    assert pix.saldo_reservado(CONTA_A) == D("0.00")
    assert pix.saldo(CONTA_B) == D("0.00")


# ---------------- Ciclo 4: tabela de decisao e antifraude (RS-03, RS-04) ----------------
# Quadro 16: (valor > 7000, autenticacao adicional OK, padrao atipico) -> resultado
@pytest.mark.parametrize(
    "valor, autenticacao, atipico, status_esperado, movimenta",
    [
        (D("100.00"), False, False, CONCLUIDA, True),  # regra 1
        (D("100.00"), False, True, RETIDA_ANALISE, False),  # regra 2
        (D("7000.01"), True, False, CONCLUIDA, True),  # regra 3
        (D("7000.01"), False, False, BLOQUEADA, False),  # regra 4 (atipico = "-": testado com Nao)
        (D("7000.01"), False, True, BLOQUEADA, False),  # regra 4 (atipico = "-": testado com Sim)
        (D("7000.01"), True, True, RETIDA_ANALISE, False),  # regra 5
    ],
    ids=["regra1", "regra2", "regra3", "regra4a", "regra4b", "regra5"],
)
def test_ct_p09_tabela_de_decisao_do_pix(relogio, valor, autenticacao, atipico, status_esperado, movimenta):
    svc = PixService(relogio=relogio, antifraude=AntifraudeFalso(forcar_atipico=atipico))
    svc.cadastrar_conta(USUARIO_A, CONTA_A, SALDO_A)
    svc.cadastrar_conta(USUARIO_B, CONTA_B, D("0.00"))
    svc.cadastrar_chave(CHAVE_B, CONTA_B)
    r = svc.transferir(USUARIO_A, CONTA_A, CHAVE_B, valor, autenticacao_adicional=autenticacao)
    assert r.status == status_esperado
    if movimenta:
        assert svc.saldo(CONTA_A) == SALDO_A - valor
        assert svc.saldo_reservado(CONTA_A) == D("0.00")
        assert svc.saldo(CONTA_B) == valor
    elif status_esperado == RETIDA_ANALISE:
        # retida de verdade: sai do disponivel, fica reservada, destino inalterado, nada se perde
        assert svc.saldo(CONTA_A) == SALDO_A - valor
        assert svc.saldo_reservado(CONTA_A) == valor
        assert svc.saldo(CONTA_B) == D("0.00")
        assert svc.saldo(CONTA_A) + svc.saldo_reservado(CONTA_A) == SALDO_A
    else:  # BLOQUEADA: nada muda
        assert svc.saldo(CONTA_A) == SALDO_A
        assert svc.saldo_reservado(CONTA_A) == D("0.00")
        assert svc.saldo(CONTA_B) == D("0.00")


def test_ct_p10_transferencia_atipica_20x_a_media_as_3h_e_retida(relogio):
    relogio.definir_hora(3)
    antifraude = AntifraudeFalso()  # decide pela propria regra (valor e horario)
    svc = PixService(relogio=relogio, antifraude=antifraude)
    svc.cadastrar_conta(USUARIO_A, CONTA_A, SALDO_A)
    svc.cadastrar_conta(USUARIO_B, CONTA_B, D("0.00"))
    svc.cadastrar_chave(CHAVE_B, CONTA_B)
    valor = 20 * AntifraudeFalso.MEDIA  # R$ 4.000,00: abaixo do limite de alto valor
    r = svc.transferir(USUARIO_A, CONTA_A, CHAVE_B, valor)
    assert r.status == RETIDA_ANALISE
    assert antifraude.consultas == [(USUARIO_A, valor, relogio.agora())]
    assert svc.saldo(CONTA_A) == SALDO_A - valor  # saiu do saldo disponivel
    assert svc.saldo_reservado(CONTA_A) == valor  # e ficou reservado
    assert svc.saldo(CONTA_B) == D("0.00")  # destino nao recebeu


# ---------------- Ciclo 5: auditoria e seguranca (RS-05, RS-08) ----------------
def test_ct_p11_alto_valor_gera_log_de_auditoria(pix, relogio):
    r = pix.transferir(USUARIO_A, CONTA_A, CHAVE_B, D("7000.01"), autenticacao_adicional=True)
    assert r.status == CONCLUIDA
    registros = pix.registros_auditoria()
    assert len(registros) == 1
    reg = registros[0]
    assert reg.usuario == USUARIO_A
    assert reg.valor == D("7000.01")
    assert reg.destino == CHAVE_B
    assert reg.data_hora == relogio.agora()


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


CPF_A = "390.533.447-05"  # CPFs ficticios; sao o identificador de usuario no PIX neste teste
CPF_B = "168.995.350-09"


def autenticar(auth, sms, cpf, senha):
    """Login completo (senha + segundo fator) via AuthService; devolve o usuario autenticado."""
    auth.login(cpf, senha)
    r = auth.confirmar_segundo_fator(cpf, sms.enviados[cpf.replace(".", "").replace("-", "")])
    assert r.status == ACESSO_LIBERADO
    return cpf


def test_ct_p17_usuario_a_autenticado_com_conta_de_origem_de_b_e_negado_e_registrado(relogio, antifraude):
    # Integracao com o AuthService (Parte4_TDD/login): A se autentica de verdade; B nao participa do login.
    sms = SmsFalso()
    auth = AuthService(relogio=RelogioLogin(), sms=sms)
    auth.cadastrar_usuario(CPF_A, "Senha@123")
    usuario_a = autenticar(auth, sms, CPF_A, "Senha@123")

    svc = PixService(relogio=relogio, antifraude=antifraude)
    svc.cadastrar_conta(usuario_a, CONTA_A, SALDO_A)
    svc.cadastrar_conta(CPF_B, CONTA_B, D("300.00"))
    svc.cadastrar_chave("111.444.777-35", CONTA_A)

    r = svc.transferir(usuario_a, CONTA_B, "111.444.777-35", D("100.00"))

    assert r.status == NEGADO
    assert svc.saldo(CONTA_B) == D("300.00")  # conta de B intacta
    assert svc.saldo(CONTA_A) == SALDO_A
    registros = svc.registros_auditoria()
    assert len(registros) == 1
    assert registros[0].usuario == usuario_a
    assert registros[0].valor == D("100.00")
    assert registros[0].destino == "111.444.777-35"
    assert registros[0].data_hora == relogio.agora()


# CT-P12 e CT-P13 (carga normal e pico 10x, RD-01/RD-02) nao entram no TDD unitario: ficam para o Locust (M5).
