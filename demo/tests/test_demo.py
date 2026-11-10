"""Teste de fumaca da DEMONSTRACAO (modo --auto). Nao e teste de modulo de producao."""
from decimal import Decimal

import pytest

import demo_nextbank as demo
from nextbank.cadastro import CONTA_CRIADA, CPF_JA_CADASTRADO
from nextbank.extrato import CREDITO, DEBITO, GERADO
from nextbank.login import ACESSO_LIBERADO, NEGADO
from nextbank.pix import CONCLUIDA


@pytest.fixture
def execucao(capsys):
    codigo = demo.principal(["--auto"])
    return codigo, capsys.readouterr().out


@pytest.fixture
def estado():
    return demo.executar(auto=True)


def test_auto_termina_com_sucesso(execucao):
    assert execucao[0] == 0


def test_conta_criada_e_cpf_duplicado_recusado(estado):
    assert estado.res_cadastro.status == CONTA_CRIADA
    assert estado.res_duplicado.status == CPF_JA_CADASTRADO


def test_login_com_segundo_fator_liberado(estado):
    assert estado.res_fator.status == ACESSO_LIBERADO


def test_saldo_credito_pix_e_extrato(estado):
    assert estado.pix.saldo(demo.CONTA_ORIGEM) == Decimal("750.00")
    assert estado.res_pix.status == CONCLUIDA
    r = estado.res_extrato
    assert r.status == GERADO
    assert [(l.tipo, l.valor) for l in r.lancamentos] == [
        (CREDITO, Decimal("1000.00")), (DEBITO, Decimal("250.00"))]
    assert r.saldo_final == Decimal("750.00")
    assert estado.cadastro.dados_conta("39053344705").saldo == Decimal("0.00")  # cadastro nasce com zero


def test_saida_mensagens_cpf_mascarado_e_sem_senha(execucao):
    _, saida = execucao
    assert "R$ 1.000,00" in saida and "CPF_JA_CADASTRADO" in saida
    assert "ACESSO_LIBERADO" in saida and "CONCLUIDA" in saida and "[SMS FALSO]" in saida
    assert "***05" in saida
    for proibido in ("390.533.447", "39053344705", demo.DADOS_AUTO["senha"], demo.DESTINO["senha"]):
        assert proibido not in saida


# --- Modo interativo: codigo fixo de demonstracao (so na demo; nao existe no produto) ---
ENTRADAS_CADASTRO = ["Maria Souza Lima", "390.533.447-05", "(11) 91234-5678",
                     "maria.lima@exemplo.com", "Senha@123", "Senha@123"]


def _executar_interativo(codigo_digitado, capsys=None):
    """Roda o modo interativo; `codigo_digitado` e uma funcao (demo.sms) -> texto digitado."""
    respostas = iter(ENTRADAS_CADASTRO)
    caixa = {}

    def entrada(prompt):
        if "SMS" in prompt:
            return codigo_digitado(caixa["demo"].sms)
        return next(respostas)

    class DemoCapturada(demo.Demonstracao):
        def __init__(self):
            super().__init__()
            caixa["demo"] = self

    original = demo.Demonstracao
    demo.Demonstracao = DemoCapturada
    try:
        return demo.executar(auto=False, entrada=entrada)
    finally:
        demo.Demonstracao = original


def test_interativo_codigo_errado_negado():
    def errado(sms):
        real = sms.ultimo_codigo()
        return "000000" if real != "000000" else "111111"  # garante que nao coincide
    estado = _executar_interativo(errado)
    assert estado.res_fator.status == NEGADO
    assert estado.res_extrato is None


def test_interativo_codigo_fixo_123456_libera_e_chega_ao_extrato():
    estado = _executar_interativo(lambda sms: "123456")
    assert estado.res_fator.status == ACESSO_LIBERADO
    assert estado.res_extrato.status == GERADO


def test_interativo_codigo_fixo_com_espaco_no_fim_libera():
    estado = _executar_interativo(lambda sms: "123456 ")
    assert estado.res_fator.status == ACESSO_LIBERADO
    assert estado.res_extrato.status == GERADO


def test_interativo_aviso_do_codigo_de_demonstracao_na_saida(capsys):
    _executar_interativo(lambda sms: "123456")
    assert "Codigo de demonstracao (so nesta demo): 123456" in capsys.readouterr().out
