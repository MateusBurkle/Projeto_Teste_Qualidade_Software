"""Testes EXPLORATORIOS 2 do Cadastro: tentativa de burlar a politica de senha (reteste INC-S09/S10).

Arquivo novo. Logica em memoria, dados ficticios. Falha aqui = incidente novo (INC-S11+).
Cada senha tem 3 classes ASCII validas e a 4a classe preenchida SO com caractere nao-ASCII/invisivel.
"""
import pytest

from nextbank.cadastro import CONTA_CRIADA, CadastroService
from nextbank.login import AuthService

NOME, CPF, CEL, EMAIL = "Maria da Silva", "390.533.447-05", "11912345678", "a@exemplo.com"


class Rel:
    def agora(self):
        return 0.0


class Sms:
    def enviar(self, cpf, codigo):
        pass


@pytest.fixture
def svc():
    return CadastroService(AuthService(Rel(), Sms()))


def tenta(s, senha):
    return s.cadastrar(NOME, CPF, CEL, EMAIL, senha, senha)


# Sem especial ASCII: o "especial" e Unicode, espaco ou controle
FALSOS_ESPECIAIS = ["§", "©", "€", "£", "°", "ª", "é", "ç", "Ω", "中", "😀", "☃", " ", " ", "\t",
                    "\n", "\x00", "\x1b", "\x7f", "​", "‮", "　", " ", "_" * 0]
# Sem digito ASCII: digito Unicode Nd ou simbolos numericos
FALSOS_DIGITOS = ["٣", "۳", "߃", "३", "৩", "๓", "３", "𝟑", "𝟛", "²", "³", "½", "Ⅲ", "①", "௩"]
# Sem maiuscula/minuscula ASCII
FALSAS_LETRAS = ["É", "Ç", "Ω", "Ａ", "ａ", "é", "ñ", "Ж", "ж"]


@pytest.mark.parametrize("c", [x for x in FALSOS_ESPECIAIS if x])
def test_especial_falso_nao_vale(svc, c):
    """RS-07 (inferido): so simbolo ASCII conta como especial."""
    assert tenta(svc, "Senha12" + c * 3).status != CONTA_CRIADA


@pytest.mark.parametrize("d", FALSOS_DIGITOS)
def test_digito_falso_nao_vale(svc, d):
    assert tenta(svc, "Senha@" + d * 3).status != CONTA_CRIADA


@pytest.mark.parametrize("l", FALSAS_LETRAS)
def test_maiuscula_falsa_nao_vale(svc, l):
    assert tenta(svc, "senha@12" + l).status != CONTA_CRIADA


@pytest.mark.parametrize("l", FALSAS_LETRAS)
def test_minuscula_falsa_nao_vale(svc, l):
    assert tenta(svc, "SENHA@12" + l).status != CONTA_CRIADA


@pytest.mark.parametrize("senha", ["Aa1@" + "x" * 3, "Aa1@" + "x" * 61, "Aa1@" * 20, ""])
def test_tamanho_fora_dos_limites(svc, senha):
    assert tenta(svc, senha).status != CONTA_CRIADA


@pytest.mark.parametrize("senha", ["Aa1@" + "x" * 4, "Aa1@" + "x" * 60])
def test_tamanho_nos_limites_aceita(svc, senha):
    assert tenta(svc, senha).status == CONTA_CRIADA


def test_comprimento_conta_pontos_de_codigo_nao_bytes(svc):
    """Senha curta em chars mas longa em bytes (emoji) nao deve passar do minimo."""
    assert tenta(svc, "Aa1@😀😀").status != CONTA_CRIADA


def test_senha_valida_ascii_ainda_aceita(svc):
    assert tenta(svc, "Senha@123").status == CONTA_CRIADA


def test_espaco_no_meio_nao_substitui_especial(svc):
    assert tenta(svc, "Senha 1234").status != CONTA_CRIADA
