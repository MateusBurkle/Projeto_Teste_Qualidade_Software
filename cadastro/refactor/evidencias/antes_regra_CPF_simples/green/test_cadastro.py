"""Testes do modulo Criacao de conta (CT-C01 a CT-C13) - Plano de Testes (META M8).

Escritos primeiro (fase RED) e mantidos SEM alteracao nas fases Green e Refactor.
Requisitos: RF (cadastro e validacao de dados), RS (senha forte, senha nunca em claro,
CPF mascarado em logs), RC (CPF unico, conta nasce com saldo zero), RD (dados guardados).
Servicos externos (relogio, SMS) sao fakes; todos os dados sao ficticios.
"""
import logging
from decimal import Decimal

import pytest

from nextbank.cadastro import (
    CELULAR_INVALIDO,
    CONFIRMACAO_DIFERENTE,
    CONTA_CRIADA,
    CPF_INVALIDO,
    CPF_JA_CADASTRADO,
    EMAIL_INVALIDO,
    ENTRADA_INVALIDA,
    NOME_INVALIDO,
    SENHA_FRACA,
    CadastroService,
)
from nextbank.login import NEGADO, SEGUNDO_FATOR_NECESSARIO, AuthService

NOME = "Maria da Silva"
CPF = "390.533.447-05"
CPF_SEM_MASCARA = "39053344705"
OUTRO_CPF = "123.456.789-09"
CELULAR = "11912345678"
EMAIL = "maria.silva@exemplo.com"
SENHA = "Senha@123"
OUTRA_SENHA = "Outra#456Z"


class RelogioFalso:
    def __init__(self):
        self.t = 0.0

    def agora(self):
        return self.t


class SmsFalso:
    """Mock do servico de SMS: guarda os codigos enviados."""

    def __init__(self):
        self.enviados = []

    def enviar(self, cpf, codigo):
        self.enviados.append((cpf, codigo))


@pytest.fixture
def auth():
    return AuthService(relogio=RelogioFalso(), sms=SmsFalso())


@pytest.fixture
def svc(auth):
    return CadastroService(auth)


def cadastrar(svc, **alterados):
    dados = dict(nome=NOME, cpf=CPF, celular=CELULAR, email=EMAIL,
                 senha=SENHA, confirmacao_senha=SENHA)
    dados.update(alterados)
    return svc.cadastrar(**dados)


def assert_recusado(res, status):
    assert res.status == status
    assert isinstance(res.mensagem, str) and res.mensagem.strip()
    assert "Traceback" not in res.mensagem


def assert_conta_nao_criada(svc, auth, cpf=CPF):
    assert svc.dados_conta(cpf) is None
    assert auth.login(cpf, SENHA).status == NEGADO


# ---------------- Cadastro valido (CT-C01) ----------------

def test_ct_c01_cadastro_valido_e_login_funciona(svc, auth):
    """CT-C01 (RF cadastro, integracao com RF-01/RF-02 do Login): conta criada e login aceita a senha."""
    res = cadastrar(svc)
    assert res.status == CONTA_CRIADA
    assert res.mensagem.strip()
    assert auth.login(CPF, SENHA).status == SEGUNDO_FATOR_NECESSARIO


def test_ct_c01_dados_guardados_e_saldo_zero(svc):
    """CT-C01 (RD dados da conta, RC saldo inicial zero): guarda nome, celular, e-mail; sem senha."""
    cadastrar(svc)
    conta = svc.dados_conta(CPF)
    assert (conta.nome, conta.celular, conta.email) == (NOME, CELULAR, EMAIL)
    assert conta.saldo == Decimal("0.00")
    assert not hasattr(conta, "senha") and SENHA not in repr(conta)


def test_ct_c01_log_sem_senha_e_com_cpf_mascarado(svc, caplog):
    """CT-C01 (RS senha nunca em claro, CPF mascarado em logs/mensagens)."""
    with caplog.at_level(logging.DEBUG):
        res = cadastrar(svc)
    texto = caplog.text + res.mensagem
    assert SENHA not in texto
    assert CPF not in texto and CPF_SEM_MASCARA not in texto


# ---------------- CPF (CT-C02, CT-C03) ----------------

@pytest.mark.parametrize("cpf", ["123", "abc.def.ghi-jk", "390.533.447-0", "390.533.447-055"])
def test_ct_c02_cpf_formato_invalido(svc, cpf):
    """CT-C02 (RF validacao de CPF): formato invalido e recusado e nao cria conta."""
    assert_recusado(cadastrar(svc, cpf=cpf), CPF_INVALIDO)
    assert svc.dados_conta(cpf) is None


@pytest.mark.parametrize("cpf", ["390.533.447-06", "111.111.111-11", "12345678900"])
def test_ct_c03_cpf_digitos_verificadores_invalidos(svc, cpf):
    """CT-C03 (RF validacao de CPF): formato ok, digitos verificadores errados."""
    assert_recusado(cadastrar(svc, cpf=cpf), CPF_INVALIDO)
    assert svc.dados_conta(cpf) is None


# ---------------- CPF duplicado (CT-C04, CT-C05) ----------------

def test_ct_c04_cpf_duplicado_recusado_e_conta_intacta(svc, auth):
    """CT-C04 (RC CPF unico, LC-04 mensagem explicita): recusa e a conta existente fica intacta."""
    cadastrar(svc)
    res = cadastrar(svc, nome="Outra Pessoa", celular="21987654321",
                    email="outra@exemplo.com", senha=OUTRA_SENHA, confirmacao_senha=OUTRA_SENHA)
    assert_recusado(res, CPF_JA_CADASTRADO)
    assert "CPF" in res.mensagem and "já vinculado" in res.mensagem
    assert CPF not in res.mensagem and CPF_SEM_MASCARA not in res.mensagem
    conta = svc.dados_conta(CPF)
    assert (conta.nome, conta.celular, conta.email) == (NOME, CELULAR, EMAIL)
    assert auth.login(CPF, SENHA).status == SEGUNDO_FATOR_NECESSARIO
    assert auth.login(CPF, OUTRA_SENHA).status == NEGADO


@pytest.mark.parametrize("primeiro, segundo", [(CPF, CPF_SEM_MASCARA), (CPF_SEM_MASCARA, CPF)])
def test_ct_c05_mesmo_cpf_com_e_sem_mascara(svc, auth, primeiro, segundo):
    """CT-C05 (RC CPF unico): CPF com e sem mascara e o mesmo CPF."""
    assert cadastrar(svc, cpf=primeiro).status == CONTA_CRIADA
    res = cadastrar(svc, cpf=segundo, senha=OUTRA_SENHA, confirmacao_senha=OUTRA_SENHA)
    assert_recusado(res, CPF_JA_CADASTRADO)
    assert auth.login(CPF, SENHA).status == SEGUNDO_FATOR_NECESSARIO
    assert auth.login(CPF, OUTRA_SENHA).status == NEGADO


# ---------------- Senha (CT-C06 a CT-C11) ----------------

def test_ct_c06_senha_sem_maiuscula(svc, auth):
    """CT-C06 (RS senha forte): sem letra maiuscula."""
    assert_recusado(cadastrar(svc, senha="senha@123", confirmacao_senha="senha@123"), SENHA_FRACA)
    assert_conta_nao_criada(svc, auth)


def test_ct_c07_senha_sem_minuscula(svc, auth):
    """CT-C07 (RS senha forte): sem letra minuscula."""
    assert_recusado(cadastrar(svc, senha="SENHA@123", confirmacao_senha="SENHA@123"), SENHA_FRACA)
    assert_conta_nao_criada(svc, auth)


def test_ct_c08_senha_sem_numero(svc, auth):
    """CT-C08 (RS senha forte): sem numero."""
    assert_recusado(cadastrar(svc, senha="Senha@abc", confirmacao_senha="Senha@abc"), SENHA_FRACA)
    assert_conta_nao_criada(svc, auth)


def test_ct_c09_senha_sem_caractere_especial(svc, auth):
    """CT-C09 (RS senha forte): sem caractere especial."""
    assert_recusado(cadastrar(svc, senha="Senha1234", confirmacao_senha="Senha1234"), SENHA_FRACA)
    assert_conta_nao_criada(svc, auth)


@pytest.mark.parametrize("simbolo", list("!$%^&*()-_=+[]{};:,.?/") + ["~", "|", "<", "'"])
def test_ct_c09_qualquer_simbolo_nao_alfanumerico_e_aceito(svc, simbolo):
    """CT-C09 (RS senha forte): !@#$%^&*()-_=+[]{};:,.?/ e qualquer simbolo nao alfanumerico servem."""
    senha = f"Senha{simbolo}123"
    assert cadastrar(svc, senha=senha, confirmacao_senha=senha).status == CONTA_CRIADA


def test_ct_c09_espaco_nao_conta_como_caractere_especial(svc, auth):
    """CT-C09 (RS senha forte): espaco NAO e caractere especial."""
    assert_recusado(cadastrar(svc, senha="Senha 1234", confirmacao_senha="Senha 1234"), SENHA_FRACA)
    assert_conta_nao_criada(svc, auth)


def test_ct_c10_senha_curta(svc, auth):
    """CT-C10 (RS senha forte, valor limite): 7 caracteres e recusada."""
    assert_recusado(cadastrar(svc, senha="Sen@123", confirmacao_senha="Sen@123"), SENHA_FRACA)
    assert_conta_nao_criada(svc, auth)


def test_ct_c10_senha_com_64_caracteres_e_aceita(svc):
    """CT-C10 (RS senha forte, valor limite): 64 caracteres (teto) e aceita."""
    senha = "Aa@1" + "x" * 60
    assert len(senha) == 64
    assert cadastrar(svc, senha=senha, confirmacao_senha=senha).status == CONTA_CRIADA


def test_ct_c10_senha_com_65_caracteres_e_recusada(svc, auth):
    """CT-C10 (RS senha forte, valor limite): 65 caracteres excede o teto -> SENHA_FRACA."""
    senha = "Aa@1" + "x" * 61
    assert len(senha) == 65
    assert_recusado(cadastrar(svc, senha=senha, confirmacao_senha=senha), SENHA_FRACA)
    assert svc.dados_conta(CPF) is None


def test_ct_c11_confirmacao_de_senha_diferente(svc, auth):
    """CT-C11 (RF confirmacao de senha): confirmacao diferente da senha."""
    assert_recusado(cadastrar(svc, confirmacao_senha="Senha@124"), CONFIRMACAO_DIFERENTE)
    assert_conta_nao_criada(svc, auth)


@pytest.mark.parametrize("senha", ["Senha@123 ", "Senha @123"])
def test_ct_c10_senha_e_preservada_exatamente_como_digitada(svc, auth, senha):
    """CT-C10 (RS senha forte): sem strip; espaco na ponta ou interno e aceito e o login exige a senha igual."""
    assert cadastrar(svc, senha=senha, confirmacao_senha=senha).status == CONTA_CRIADA
    assert auth.login(CPF, senha).status == SEGUNDO_FATOR_NECESSARIO


# ---------------- Nome, celular e e-mail (CT-C12) ----------------

@pytest.mark.parametrize("campo, valor, status", [
    ("nome", "Jo", NOME_INVALIDO),
    ("nome", "Joao123", NOME_INVALIDO),
    ("nome", "Ana.Maria", NOME_INVALIDO),
    ("celular", "1191234567", CELULAR_INVALIDO),
    ("celular", "11812345678", CELULAR_INVALIDO),
    ("celular", "11a12345678", CELULAR_INVALIDO),
    ("email", "maria.exemplo.com", EMAIL_INVALIDO),
    ("email", "maria@", EMAIL_INVALIDO),
])
def test_ct_c12_nome_celular_ou_email_invalido(svc, auth, campo, valor, status):
    """CT-C12 (RF validacao de nome, celular e e-mail): um cenario invalido por campo."""
    assert_recusado(cadastrar(svc, **{campo: valor}), status)
    assert_conta_nao_criada(svc, auth)


def test_ct_c12_email_dominio_sem_ponto_recusado(svc, auth):
    """CT-C12 (RF validacao de e-mail): exige @ e dominio com ponto; maria@exemplo e recusado."""
    assert_recusado(cadastrar(svc, email="maria@exemplo"), EMAIL_INVALIDO)
    assert_conta_nao_criada(svc, auth)


@pytest.mark.parametrize("nome", ["José da Silva", "Ângela Müller Conceição",
                                  "Ana-Clara", "D'Ávila", "Ana Maria", "Ana"])
def test_ct_c12_nome_aceita_acentos_hifen_apostrofo_e_espacos(svc, nome):
    """CT-C12 (RF validacao de nome): letras com acento, espacos, hifen e apostrofo; minimo 3."""
    assert cadastrar(svc, nome=nome).status == CONTA_CRIADA
    assert svc.dados_conta(CPF).nome == nome


def test_ct_c12_nome_espacos_duplos_internos_sao_colapsados(svc):
    """CT-C12 (RF validacao de nome, RD dados guardados): 'Ana  Maria' e guardado como 'Ana Maria'."""
    assert cadastrar(svc, nome="Ana  Maria").status == CONTA_CRIADA
    assert svc.dados_conta(CPF).nome == "Ana Maria"


@pytest.mark.parametrize("nome", ["  José da Silva", "José da Silva  ", "   José da Silva   "])
def test_ct_c12_nome_com_espacos_nas_pontas_e_guardado_sem_eles(svc, nome):
    """CT-C12 (RF validacao de nome, RD dados guardados): espacos nas pontas sao removidos."""
    assert cadastrar(svc, nome=nome).status == CONTA_CRIADA
    assert svc.dados_conta(CPF).nome == "José da Silva"


@pytest.mark.parametrize("nome", [" Jo ", "  Jo", "J  o", " J o "])
def test_ct_c12_nome_minimo_de_3_conta_apos_normalizar_espacos(svc, auth, nome):
    """CT-C12 (RF validacao de nome): o minimo de 3 caracteres vale apos trim e colapso de espacos."""
    assert_recusado(cadastrar(svc, nome=nome), NOME_INVALIDO)
    assert_conta_nao_criada(svc, auth)


def test_ct_c12_nome_com_espacos_nas_pontas_e_3_letras_e_aceito(svc):
    """CT-C12 (RF validacao de nome, RD dados guardados): ' Ana ' e aceito e guardado como 'Ana'."""
    assert cadastrar(svc, nome=" Ana ").status == CONTA_CRIADA
    assert svc.dados_conta(CPF).nome == "Ana"


def test_ct_c12_nome_com_100_caracteres_e_aceito(svc):
    """CT-C12 (RF validacao de nome, valor limite): 100 caracteres (teto) e aceito."""
    nome = "A" * 100
    assert cadastrar(svc, nome=nome).status == CONTA_CRIADA
    assert svc.dados_conta(CPF).nome == nome


def test_ct_c12_nome_com_101_caracteres_e_recusado(svc, auth):
    """CT-C12 (RF validacao de nome, valor limite): 101 caracteres excede o teto."""
    assert_recusado(cadastrar(svc, nome="A" * 101), NOME_INVALIDO)
    assert_conta_nao_criada(svc, auth)


@pytest.mark.parametrize("nome", ["---", "'''", "-Ana", "Ana-", "Ana'"])
def test_ct_c12_nome_deve_comecar_e_terminar_com_letra(svc, auth, nome):
    """CT-C12 (RF validacao de nome): sem letra, ou iniciando/terminando em hifen/apostrofo -> recusado."""
    assert_recusado(cadastrar(svc, nome=nome), NOME_INVALIDO)
    assert_conta_nao_criada(svc, auth)


@pytest.mark.parametrize("celular", ["(11) 91234-5678", "11912345678", "(11)912345678", "11 91234-5678"])
def test_ct_c12_celular_aceita_com_e_sem_mascara_e_normaliza(svc, celular):
    """CT-C12 (RF validacao de celular): aceita mascara; dados_conta devolve so digitos."""
    assert cadastrar(svc, celular=celular).status == CONTA_CRIADA
    assert svc.dados_conta(CPF).celular == "11912345678"


# ---------------- Ordem de validacao (CT-C12 / CT-C13 / CT-C04) ----------------
# Ordem: ENTRADA_INVALIDA -> CPF_INVALIDO -> CPF_JA_CADASTRADO -> NOME -> CELULAR -> EMAIL
#        -> SENHA_FRACA -> CONFIRMACAO_DIFERENTE. Retorna o PRIMEIRO erro encontrado.

@pytest.mark.parametrize("alterados, status", [
    (dict(cpf="123", nome="Jo", celular="1", email="x", senha="a", confirmacao_senha="b"), CPF_INVALIDO),
    (dict(nome="Jo", celular="1", email="x", senha="a", confirmacao_senha="b"), NOME_INVALIDO),
    (dict(nome="Jo", email="maria.exemplo.com"), NOME_INVALIDO),
    (dict(celular="1191234567", email="maria.exemplo.com"), CELULAR_INVALIDO),
    (dict(celular="1191234567", senha="fraca", confirmacao_senha="outra"), CELULAR_INVALIDO),
    (dict(email="maria.exemplo.com", senha="fraca", confirmacao_senha="outra"), EMAIL_INVALIDO),
    (dict(senha="fraca", confirmacao_senha="outra"), SENHA_FRACA),
])
def test_ct_c12_ordem_de_validacao_com_dois_erros(svc, auth, alterados, status):
    """CT-C12 (RF validacao): CPF, nome, celular, e-mail, senha, confirmacao; vale o primeiro erro."""
    assert_recusado(cadastrar(svc, **alterados), status)
    assert_conta_nao_criada(svc, auth)


def test_ct_c04_cpf_duplicado_tem_prioridade_sobre_senha_fraca(svc, auth):
    """CT-C04 (RC CPF unico): CPF ja cadastrado + senha fraca -> CPF_JA_CADASTRADO; conta intacta.
    A duplicidade e checada logo apos validar o CPF, ANTES de nome/celular/e-mail/senha."""
    cadastrar(svc)
    res = cadastrar(svc, nome="Outra Pessoa", senha="fraca", confirmacao_senha="outra")
    assert_recusado(res, CPF_JA_CADASTRADO)
    assert svc.dados_conta(CPF).nome == NOME
    assert auth.login(CPF, SENHA).status == SEGUNDO_FATOR_NECESSARIO


@pytest.mark.parametrize("alterados", [
    dict(nome="Jo"),
    dict(celular="1191234567"),
    dict(email="maria.exemplo.com"),
    dict(senha=OUTRA_SENHA, confirmacao_senha="Diferente@1"),
], ids=["nome_invalido", "celular_invalido", "email_invalido", "confirmacao_diferente"])
def test_ct_c04_cpf_duplicado_tem_prioridade_sobre_nome_celular_email_confirmacao(svc, auth, alterados):
    """CT-C04 (RC CPF unico): CPF ja cadastrado + outro erro (nome/celular/e-mail/confirmacao)
    -> sempre CPF_JA_CADASTRADO; conta existente intacta."""
    cadastrar(svc)
    assert_recusado(cadastrar(svc, **alterados), CPF_JA_CADASTRADO)
    conta = svc.dados_conta(CPF)
    assert (conta.nome, conta.celular, conta.email) == (NOME, CELULAR, EMAIL)
    assert auth.login(CPF, SENHA).status == SEGUNDO_FATOR_NECESSARIO
    assert auth.login(CPF, OUTRA_SENHA).status == NEGADO


def test_ct_c04_cpf_invalido_vem_antes_de_duplicado(svc):
    """CT-C04 (RC CPF unico): CPF invalido e recusado como CPF_INVALIDO, nunca como duplicado."""
    cadastrar(svc)
    assert_recusado(cadastrar(svc, cpf="390.533.447-06", senha="fraca"), CPF_INVALIDO)


# ---------------- Entradas vazias, None ou tipo errado (CT-C13) ----------------

CAMPOS = ["nome", "cpf", "celular", "email", "senha", "confirmacao_senha"]
VALORES_RUINS = ["", "   ", None, 123, ["x"]]


@pytest.mark.parametrize("campo", CAMPOS)
@pytest.mark.parametrize("valor", VALORES_RUINS)
def test_ct_c13_campo_vazio_none_ou_tipo_errado(svc, auth, campo, valor):
    """CT-C13 (RF robustez): sem excecao; resultado ENTRADA_INVALIDA e nenhuma conta criada."""
    assert_recusado(cadastrar(svc, **{campo: valor}), ENTRADA_INVALIDA)
    assert_conta_nao_criada(svc, auth)


@pytest.mark.parametrize("alterados", [
    dict(cpf="123", nome=None),
    dict(cpf="390.533.447-06", celular=""),
    dict(cpf="123", email=123),
    dict(cpf="123", senha=None),
    dict(nome="Jo", confirmacao_senha=None),
])
def test_ct_c13_entrada_invalida_vem_antes_de_qualquer_outra_validacao(svc, alterados):
    """CT-C13 (RF robustez): ENTRADA_INVALIDA tem prioridade ate sobre CPF_INVALIDO."""
    assert_recusado(cadastrar(svc, **alterados), ENTRADA_INVALIDA)


def test_ct_c13_entrada_invalida_vem_antes_de_cpf_duplicado(svc):
    """CT-C13 (RF robustez): CPF ja cadastrado + campo None -> ENTRADA_INVALIDA."""
    cadastrar(svc)
    assert_recusado(cadastrar(svc, nome=None), ENTRADA_INVALIDA)
    assert svc.dados_conta(CPF).nome == NOME


def test_ct_c13_todos_os_campos_none(svc):
    """CT-C13 (RF robustez): todos os campos None, sem excecao."""
    assert_recusado(svc.cadastrar(None, None, None, None, None, None), ENTRADA_INVALIDA)
