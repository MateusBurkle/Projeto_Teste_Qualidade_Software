"""Integracao Login + Cadastro (nivel Sistema, em memoria).

CadastroService real + AuthService real; apenas relogio e SMS sao falsos.
Executar com PYTHONPATH apontando para cadastro/refactor (pacote nextbank).
"""
from nextbank.cadastro import (
    CONTA_CRIADA,
    CPF_JA_CADASTRADO,
    CadastroService,
)
from nextbank.login import (
    ACESSO_LIBERADO,
    NEGADO,
    SEGUNDO_FATOR_NECESSARIO,
    AuthService,
)

CPF = "529.982.247-25"
SENHA = "Senha@123"
SENHA_NOVA = "Outra@4567"


class RelogioFalso:
    def __init__(self):
        self.t = 0.0

    def agora(self):
        return self.t


class SmsFalso:
    def __init__(self):
        self.enviados = []

    def enviar(self, cpf, codigo):
        self.enviados.append((cpf, codigo))

    def ultimo_codigo(self):
        return self.enviados[-1][1]


def _montar():
    sms = SmsFalso()
    auth = AuthService(relogio=RelogioFalso(), sms=sms)
    return CadastroService(auth), auth, sms


def _cadastrar(cad, senha=SENHA, nome="Maria da Silva"):
    return cad.cadastrar(nome, CPF, "(11) 98765-4321", "maria@exemplo.com", senha, senha)


def test_cadastro_seguido_de_login_com_segundo_fator():
    cad, auth, sms = _montar()
    assert _cadastrar(cad).status == CONTA_CRIADA
    r1 = auth.login(CPF, SENHA)
    assert r1.status == SEGUNDO_FATOR_NECESSARIO
    assert len(sms.enviados) == 1
    r2 = auth.confirmar_segundo_fator(CPF, sms.ultimo_codigo())
    assert r2.status == ACESSO_LIBERADO


def test_login_antes_do_cadastro_e_negado():
    cad, auth, sms = _montar()
    assert auth.login(CPF, SENHA).status == NEGADO
    assert sms.enviados == []


def test_cpf_duplicado_nao_sobrescreve_conta_existente():
    cad, auth, sms = _montar()
    assert _cadastrar(cad).status == CONTA_CRIADA
    dup = _cadastrar(cad, senha=SENHA_NOVA, nome="Outra Pessoa")
    assert dup.status == CPF_JA_CADASTRADO
    # dados da conta original preservados
    assert cad.dados_conta(CPF).nome == "Maria da Silva"
    # senha antiga continua valida
    assert auth.login(CPF, SENHA).status == SEGUNDO_FATOR_NECESSARIO
    assert auth.confirmar_segundo_fator(CPF, sms.ultimo_codigo()).status == ACESSO_LIBERADO
    # senha da tentativa duplicada nao funciona
    assert auth.login(CPF, SENHA_NOVA).status == NEGADO


# --- Regra CPF simples (so formato, sem digitos verificadores) ---
CPF_DV_ERRADO = "123.456.789-00"


def test_cpf_formato_valido_com_dv_errado_cria_conta_e_faz_login():
    cad, auth, sms = _montar()
    r = cad.cadastrar("Maria da Silva", CPF_DV_ERRADO, "(11) 98765-4321",
                      "maria@exemplo.com", SENHA, SENHA)
    assert r.status == CONTA_CRIADA
    assert auth.login(CPF_DV_ERRADO, SENHA).status == SEGUNDO_FATOR_NECESSARIO
    assert auth.confirmar_segundo_fator(CPF_DV_ERRADO, sms.ultimo_codigo()).status == ACESSO_LIBERADO
