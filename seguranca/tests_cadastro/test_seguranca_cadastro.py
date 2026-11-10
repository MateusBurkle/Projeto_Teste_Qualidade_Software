"""Testes de SEGURANCA basicos do Cadastro (META M8) - CT-S09 em diante.

Logica em memoria; nao e pentest nem API HTTP. Fakes para SMS/relogio; dados ficticios.
Passa = controle existe; falha = vulnerabilidade (incidente INC-S04+ no RESUMO_SEGURANCA.md).
Modulos importados SEM modificacao de ../cadastro/refactor (ver pytest_cadastro.ini).
Mapa RS (Quadros 8 e 9): RS-06 senha/dados sensiveis nunca em claro; RS-07 entrada maliciosa
recusada sem expor detalhes; RS-02 segundo fator; RS-08 isolamento entre contas; RC-01 CPF unico.
"""
import logging
import time
from decimal import Decimal

import pytest

from nextbank.cadastro import (
    CONTA_CRIADA, CPF_JA_CADASTRADO, CadastroService,
)
from nextbank.login import NEGADO, SEGUNDO_FATOR_NECESSARIO, AuthService

NOME, CPF, CPF_PLANO = "Maria da Silva", "390.533.447-05", "39053344705"
OUTRO_CPF = "123.456.789-09"
CELULAR, EMAIL, SENHA = "11912345678", "maria.silva@exemplo.com", "Senha@123"
MALICIOSOS = ["' OR 1=1 --", "<script>alert(1)</script>", "'; DROP TABLE contas;--",
              "a\x00b", "a\x01b\x1b[31m", "a\r\nb"]
LIMITE_SEG = 2.0  # tempo maximo aceitavel por chamada com entrada grande


def fullwidth(txt):
    """Troca 0-9 por digitos fullwidth (U+FF10..)."""
    return "".join(chr(0xFF10 + int(c)) if c.isdigit() else c for c in txt)


def arabe(txt):
    return "".join(chr(0x0660 + int(c)) if c.isdigit() else c for c in txt)


class Relogio:
    t = 0.0

    def agora(self):
        return self.t


class SmsFalso:
    def __init__(self):
        self.enviados = []

    def enviar(self, cpf, codigo):
        self.enviados.append((cpf, codigo))


@pytest.fixture
def sis():
    sms = SmsFalso()
    auth = AuthService(Relogio(), sms)
    return CadastroService(auth), auth, sms


def cad(svc, nome=NOME, cpf=CPF, cel=CELULAR, email=EMAIL, senha=SENHA, conf=None):
    return svc.cadastrar(nome, cpf, cel, email, senha, senha if conf is None else conf)


def total_contas(svc):
    return len(svc._contas)  # leitura do estado interno apenas para verificar


# CT-S09 (RS-06) senha nunca em claro
def test_CT_S09_senha_nunca_em_claro(sis, caplog):
    svc, auth, _ = sis
    senha = "Zq#Segredo987"
    with caplog.at_level(logging.DEBUG):
        r = cad(svc, senha=senha)
        cad(svc, senha=senha)  # duplicado
        cad(svc, cpf=OUTRO_CPF, senha=senha, conf="Diferente#1")
        auth.login(CPF, "errada")
    assert r.status == CONTA_CRIADA
    visivel = [repr(r), r.mensagem, repr(svc.dados_conta(CPF)), str(vars(svc.dados_conta(CPF))),
               caplog.text] + [x.getMessage() for x in caplog.records]
    assert all(senha not in v for v in visivel)
    usuario = auth._usuarios[CPF_PLANO]
    assert senha.encode() not in usuario.senha_hash + usuario.sal
    assert senha not in repr(usuario)


# CT-S10 (RS-06) CPF mascarado em logs e mensagens, inclusive duplicado
def test_CT_S10_cpf_mascarado_em_logs_e_mensagens(sis, caplog):
    svc, _, _ = sis
    with caplog.at_level(logging.DEBUG):
        r1 = cad(svc)
        r2 = cad(svc)  # duplicado
        r3 = cad(svc, cpf="111.111.111-11")
    assert r2.status == CPF_JA_CADASTRADO
    for texto in [r1.mensagem, r2.mensagem, r3.mensagem, caplog.text]:
        assert CPF not in texto and CPF_PLANO not in texto and "533" not in texto
    assert "***05" in caplog.text


# CT-S11 (RS-07) entradas maliciosas em cada campo: sem excecao, sem conta criada
@pytest.mark.parametrize("texto", MALICIOSOS)
@pytest.mark.parametrize("campo", ["nome", "cpf", "cel", "email", "senha"])
def test_CT_S11_entrada_maliciosa_recusada(sis, campo, texto):
    svc, _, _ = sis
    kw = {campo: texto}
    if campo == "senha":
        kw["conf"] = texto
    r = cad(svc, **kw)
    assert r.status != CONTA_CRIADA
    assert total_contas(svc) == 0
    assert texto not in r.mensagem  # nao devolve o payload


# CT-S12 (RS-07) caracteres de controle/byte nulo/tags no e-mail
@pytest.mark.parametrize("email", ["a\x00@exemplo.com", "a\x01@exemplo.com",
                                   "<script>alert(1)</script>@exemplo.com", "a\x7f@exemplo.com"])
def test_CT_S12_email_com_controle_ou_tag_recusado(sis, email):
    svc, _, _ = sis
    assert cad(svc, email=email).status != CONTA_CRIADA
    assert total_contas(svc) == 0


# CT-S13 (RS-07) senha com caractere nao codificavel (surrogate solitario) sem excecao
def test_CT_S13_senha_com_surrogate_sem_excecao(sis):
    svc, _, _ = sis
    senha = "Abc#1234\ud800"
    try:
        r = cad(svc, senha=senha)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"excecao interna: {type(e).__name__}: {e}")
    assert r.status != CONTA_CRIADA or total_contas(svc) == 1


# CT-S14 (RS-07) strings enormes e repetitivas: sem excecao e sem travar (ReDoS)
@pytest.mark.parametrize("campo", ["nome", "cpf", "cel", "email", "senha"])
@pytest.mark.parametrize("padrao", ["a", "a@", "a.", "1", " ", "-'", "١"])
def test_CT_S14_strings_enormes_sem_travar(sis, campo, padrao):
    svc, _, _ = sis
    grande = padrao * 200_000
    for variante in (grande, "x@" + grande, grande + "!"):
        kw = {campo: variante}
        if campo == "senha":
            kw["conf"] = variante
        t0 = time.perf_counter()
        r = cad(svc, **kw)
        assert time.perf_counter() - t0 < LIMITE_SEG, f"lento em {campo}"
        assert r.status != CONTA_CRIADA
    assert total_contas(svc) == 0


# CT-S15 (RS-07) e-mail gigante porem "valido" nao deveria ser aceito (limite de tamanho)
def test_CT_S15_email_gigante_valido_recusado(sis):
    svc, _, _ = sis
    email = "a" * 100_000 + "@exemplo.com"
    assert cad(svc, email=email).status != CONTA_CRIADA


# CT-S16 (RS-07/RC-01) digitos Unicode no CPF: recusados ou normalizados, nunca conta paralela
@pytest.mark.parametrize("conv", [fullwidth, arabe])
def test_CT_S16_cpf_unicode_nao_cria_duplicada(sis, conv):
    svc, _, _ = sis
    assert cad(svc).status == CONTA_CRIADA
    r = cad(svc, cpf=conv(CPF))
    assert r.status != CONTA_CRIADA
    assert total_contas(svc) == 1
    assert list(svc._contas) == [CPF_PLANO]


# CT-S17 (RS-07) CPF unicode como PRIMEIRO cadastro: so guarda chave em digitos latinos
@pytest.mark.parametrize("conv", [fullwidth, arabe])
def test_CT_S17_cpf_unicode_chave_somente_latina(sis, conv):
    svc, _, _ = sis
    cad(svc, cpf=conv(CPF))
    assert all(k.isascii() for k in svc._contas)
    if total_contas(svc) == 1:
        assert cad(svc).status == CPF_JA_CADASTRADO
    assert total_contas(svc) <= 1


# CT-S18 (RS-07) celular com digitos Unicode: recusado ou normalizado para ASCII
@pytest.mark.parametrize("cel", [fullwidth(CELULAR), arabe(CELULAR),
                                 fullwidth("11") + "912345678", arabe("11") + "9" + arabe("12345678")])
def test_CT_S18_celular_unicode(sis, cel):
    svc, _, _ = sis
    r = cad(svc, cel=cel)
    if r.status == CONTA_CRIADA:
        assert svc.dados_conta(CPF).celular.isascii()
        assert svc.dados_conta(CPF).celular == CELULAR


# CT-S19 (RC-01) duplicidade com variacoes de mascara/espacos/Unicode
@pytest.mark.parametrize("variacao", [CPF_PLANO, "390533447-05", "390.53344705", " 390.533.447-05",
                                      "390.533.447-05 ", "390.533.447-05\n", "390 533 447 05",
                                      fullwidth(CPF_PLANO), fullwidth(CPF), arabe(CPF_PLANO)])
def test_CT_S19_duplicidade_com_variacoes(sis, variacao):
    svc, auth, _ = sis
    cad(svc, nome="Maria Original")
    cad(svc, nome="Invasora Falsa", cpf=variacao, senha="Outra#9999")
    assert total_contas(svc) == 1
    assert svc.dados_conta(CPF).nome == "Maria Original"
    assert auth.login(CPF, "Outra#9999").status == NEGADO
    assert auth.login(CPF, SENHA).status == SEGUNDO_FATOR_NECESSARIO


# CT-S20 (RS-07) LC-04: mensagem explicita de CPF duplicado revela existencia (decisao do usuario)
def test_CT_S20_LC04_enumeracao_registrada(sis):
    svc, _, _ = sis
    cad(svc)
    existente = cad(svc)
    novo = cad(svc, cpf=OUTRO_CPF)
    assert existente.status == CPF_JA_CADASTRADO  # comportamento registrado (limitacao LC-04)
    assert novo.status == CONTA_CRIADA
    assert existente.mensagem != novo.mensagem


# CT-S21 (RS-07) tempo de resposta CPF duplicado x invalido nao difere de forma obvia
def test_CT_S21_tempo_duplicado_vs_invalido(sis):
    svc, _, _ = sis
    cad(svc)

    def medir(cpf):
        t0 = time.perf_counter()
        for _ in range(300):
            cad(svc, cpf=cpf)
        return time.perf_counter() - t0

    dup, inv = medir(CPF), medir("111.111.111-11")
    assert max(dup, inv) < 10 * max(min(dup, inv), 1e-4)


# CT-S22 (RS-07) milhares de tentativas invalidas nao criam contas nem corrompem estado
def test_CT_S22_forca_bruta_cadastro(sis):
    svc, auth, _ = sis
    cad(svc)
    antes = (dict(svc._contas), dict(auth._usuarios))
    for i in range(5000):
        cpf = f"{i:03d}.456.789-00"
        r = svc.cadastrar(MALICIOSOS[i % 6], cpf, "1", "x", "fraca", "outra")
        assert r.status != CONTA_CRIADA
    assert total_contas(svc) == 1
    assert (svc._contas, auth._usuarios) == antes
    assert cad(svc, cpf=OUTRO_CPF).status == CONTA_CRIADA


# CT-S23 (RS-06/RS-02/RS-08) conta nova sem privilegios indevidos
def test_CT_S23_conta_nasce_sem_privilegios(sis):
    svc, auth, sms = sis
    cad(svc)
    d = svc.dados_conta(CPF)
    assert d.saldo == Decimal("0.00") and isinstance(d.saldo, Decimal)
    u = auth._usuarios[CPF_PLANO]
    assert isinstance(u.senha_hash, bytes) and len(u.sal) >= 16 and u.senha_hash != SENHA.encode()
    assert not u.bloqueada and u.falhas == 0
    r = auth.login(CPF, SENHA)
    assert r.status == SEGUNDO_FATOR_NECESSARIO  # nao ha acesso direto sem 2o fator
    assert len(sms.enviados) == 1


# CT-S24 (RS-08) dados_conta com entradas estranhas nao vaza dados de outra conta
@pytest.mark.parametrize("entrada", ["", None, 123, "' OR 1=1 --", "*", "%", "390.533.447-0",
                                     "390.533.447-05' --", "..", ["39053344705"], b"39053344705",
                                     fullwidth(CPF_PLANO), "390.533.447-05\x00", OUTRO_CPF])
def test_CT_S24_dados_conta_entrada_estranha(sis, entrada):
    svc, _, _ = sis
    cad(svc)
    try:
        d = svc.dados_conta(entrada)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"excecao interna: {type(e).__name__}")
    assert d is None
