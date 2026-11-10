"""Testes EXPLORATORIOS extras do Cadastro (reteste M8, apos correcao INC-S04..S08).

Arquivo novo; nao altera test_seguranca_cadastro.py. Logica em memoria, dados ficticios.
Falha aqui = possivel incidente novo (INC-S09+).
"""

import pytest

from nextbank.cadastro import CONTA_CRIADA, CadastroService
from nextbank.login import AuthService

NOME, CPF, CEL, EMAIL, SENHA = "Maria da Silva", "390.533.447-05", "11912345678", "a@exemplo.com", "Senha@123"


class Rel:
    def agora(self):
        return 0.0


class Sms:
    def enviar(self, cpf, codigo):
        pass


@pytest.fixture
def svc():
    return CadastroService(AuthService(Rel(), Sms()))


def cad(s, nome=NOME, cpf=CPF, cel=CEL, email=EMAIL, senha=SENHA, conf=None):
    return s.cadastrar(nome, cpf, cel, email, senha, senha if conf is None else conf)


def digitos_nd(n=6):
    """Um digito por bloco Nd (zero + 0..9) em varios scripts."""
    blocos = [0x0660, 0x06F0, 0x07C0, 0x0966, 0x09E6, 0x0E50, 0xFF10, 0x1D7CE, 0x1D7D8, 0x1D7E2, 0x1D7EC, 0x1D7F6]
    return blocos


def troca(txt, base):
    return "".join(chr(base + int(c)) if c.isdigit() else c for c in txt)


@pytest.mark.parametrize("base", digitos_nd())
def test_cpf_digitos_unicode_nd_todos_blocos(svc, base):
    r = cad(svc, cpf=troca("39053344705", base))
    assert r.status != CONTA_CRIADA and not svc._contas


@pytest.mark.parametrize("base", digitos_nd())
def test_cpf_unicode_com_mascara_e_misto(svc, base):
    for cpf in (troca(CPF, base), CPF[:-1] + chr(base + 5), chr(base + 3) + CPF[1:]):
        r = cad(svc, cpf=cpf)
        assert r.status != CONTA_CRIADA
    assert not svc._contas


@pytest.mark.parametrize("base", digitos_nd())
def test_celular_unicode_em_qualquer_posicao(svc, base):
    for i in range(11):
        cel = CEL[:i] + chr(base + int(CEL[i])) + CEL[i + 1:]
        assert cad(svc, cel=cel).status != CONTA_CRIADA, repr(cel)
    assert cad(svc, cel=troca("(11) 91234-5678", base)).status != CONTA_CRIADA


@pytest.mark.parametrize("cpf", ["39053344705\n", " 39053344705", "390-533-447.05", "390.533.447-05\x00", "³⁹⁰.533.447-05"])
def test_cpf_mascara_estranha_recusada(svc, cpf):
    assert cad(svc, cpf=cpf).status != CONTA_CRIADA


@pytest.mark.parametrize("email", [
    "a@exemplo.com\n", "a@exemplo.com\x00", "a\t@exemplo.com", "a\x1b[31m@exemplo.com", "a\x7f@exemplo.com",
    "ação@exemplo.com", "a@exemplo.cóm", "a@ехample.com", "a‮@exemplo.com", "a​@exemplo.com",
    "a\u0085@exemplo.com", "a @exemplo.com", "<a@exemplo.com", "a@exemplo.com>", "a@@exemplo.com",
    "a@exemplo..com", "a@.exemplo.com", "a@exemplo.com.", "a@exemplo",
])
def test_email_controle_e_unicode_recusados(svc, email):
    assert cad(svc, email=email).status != CONTA_CRIADA


def test_email_tamanho_limite(svc):
    ok = "a" * (254 - len("@exemplo.com")) + "@exemplo.com"
    assert len(ok) == 254 and cad(svc, email=ok).status == CONTA_CRIADA
    for n in (255, 256, 1000):
        s = CadastroService(AuthService(Rel(), Sms()))
        assert cad(s, email="a" * (n - 12) + "@exemplo.com").status != CONTA_CRIADA


@pytest.mark.parametrize("senha", ["Abc#1234\ud800", "\udfffAbc#1234", "Ab\ud83d#1234", "Abc#1234\udc00\udc00"])
def test_senha_surrogate_sem_excecao(svc, senha):
    assert cad(svc, senha=senha).status != CONTA_CRIADA
    assert cad(svc, senha=SENHA, conf=senha).status != CONTA_CRIADA  # so a confirmacao
    assert not svc._contas


@pytest.mark.parametrize("campo", ["nome", "cel", "email"])
def test_surrogate_em_outros_campos_sem_excecao(svc, campo):
    kw = {campo: {"nome": "Maria\ud800 Silva", "cel": "11\ud80012345678", "email": "a\ud800@exemplo.com"}[campo]}
    assert cad(svc, **kw).status != CONTA_CRIADA


def test_cpf_surrogate_sem_excecao(svc):
    assert cad(svc, cpf="390.533.447-0\ud800").status != CONTA_CRIADA


@pytest.mark.parametrize("nome", ["Mariá Silva", "Ma​ria Silva", "Maria\nSilva", "<b>Maria</b>", "Maria\x00 Silva", "Mar1a Silva"])
def test_nome_estranho_recusado(svc, nome):
    assert cad(svc, nome=nome).status != CONTA_CRIADA


def test_senha_sem_digito_ascii_nao_deveria_valer(svc):
    """Politica: digito Unicode (Nd) nao deveria contar como 'numero' na senha."""
    assert cad(svc, senha="Senha@٣٤٥٦").status != CONTA_CRIADA


def test_senha_acentuada_como_especial_nao_deveria_valer(svc):
    """Politica: letra acentuada nao deveria contar como caractere especial."""
    assert cad(svc, senha="Senha1éééé").status != CONTA_CRIADA


def test_resultado_nao_ecoa_entrada(svc):
    r = cad(svc, email="<script>alert(1)</script>@x.com", nome="' OR 1=1 --")
    assert "script" not in r.mensagem and "OR 1=1" not in r.mensagem


def test_cpf_mascara_parcial_ascii_e_mesmo_cpf(svc):
    """Mascara parcial ASCII e aceita pelo padrao, mas vira a mesma chave: duplicidade barrada."""
    assert cad(svc).status == CONTA_CRIADA
    assert cad(svc, cpf="390.533.44705").status != CONTA_CRIADA
    assert len(svc._contas) == 1
