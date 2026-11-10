"""FASE REFACTOR - cadastro: mesmo comportamento do Green, codigo reorganizado.

Responsabilidades separadas:
  - constantes/mensagens/padroes regex (topo do modulo)
  - validadores puros (funcoes pequenas, sem estado e sem log)
  - CadastroService: orquestra a ordem, armazena contas e registra log
Ordem de validacao (primeiro erro): ENTRADA, CPF, CPF duplicado, NOME,
CELULAR, EMAIL, SENHA, CONFIRMACAO.
"""
from dataclasses import dataclass
import logging
import re
from decimal import Decimal

from nextbank.login import mascarar, normalizar_cpf

logger = logging.getLogger("nextbank.cadastro")

# --- Status ---
CONTA_CRIADA = "CONTA_CRIADA"
CPF_INVALIDO = "CPF_INVALIDO"
CPF_JA_CADASTRADO = "CPF_JA_CADASTRADO"
NOME_INVALIDO = "NOME_INVALIDO"
CELULAR_INVALIDO = "CELULAR_INVALIDO"
EMAIL_INVALIDO = "EMAIL_INVALIDO"
SENHA_FRACA = "SENHA_FRACA"
CONFIRMACAO_DIFERENTE = "CONFIRMACAO_DIFERENTE"
ENTRADA_INVALIDA = "ENTRADA_INVALIDA"

# --- Mensagens ---
MSG_CONTA_CRIADA = "Conta criada com sucesso."
MSG_CPF_JA_CADASTRADO = "CPF já vinculado a uma conta."
MSG_ENTRADA_INVALIDA = "Dados de entrada inválidos."
MSG_CPF_INVALIDO = "CPF inválido."
MSG_NOME_INVALIDO = "Nome inválido."
MSG_CELULAR_INVALIDO = "Celular inválido."
MSG_EMAIL_INVALIDO = "E-mail inválido."
MSG_SENHA_FRACA = "Senha fraca."
MSG_CONFIRMACAO_DIFERENTE = "Confirmação de senha diferente."

# --- Limites ---
NOME_MIN_LETRAS = 3
NOME_MAX = 100
SENHA_MIN = 8
SENHA_MAX = 64
SALDO_INICIAL = Decimal("0.00")

# --- Padroes (compilados) ---
RE_ESPACOS_MULTIPLOS = re.compile(r" +")
RE_NOME = re.compile(r"(?:[^\W\d_]|[ '\-])+")
RE_CELULAR = re.compile(r"\(?\d{2}\)? ?9\d{4}-?\d{4}")
RE_NAO_DIGITO = re.compile(r"\D")
RE_EMAIL = re.compile(r"[^@\s]+@[^@\s.]+(\.[^@\s.]+)+")
RE_MAIUSCULA = re.compile(r"[A-Z]")
RE_MINUSCULA = re.compile(r"[a-z]")
RE_DIGITO = re.compile(r"\d")
RE_ESPECIAL = re.compile(r"[^A-Za-z0-9\s]")
RE_SENHA_REGRAS = (RE_MAIUSCULA, RE_MINUSCULA, RE_DIGITO, RE_ESPECIAL)


@dataclass
class ResultadoCadastro:
    status: str
    mensagem: str


@dataclass
class DadosConta:
    nome: str
    celular: str
    email: str
    saldo: Decimal


# --- Validadores puros ---
def _campo_valido(valor):
    return isinstance(valor, str) and bool(valor.strip())


def _entrada_ok(campos):
    return all(_campo_valido(c) for c in campos)


def _cpf_dv_ok(cpf):
    if cpf == cpf[0] * 11:
        return False
    return all(_dv_confere(cpf, tam) for tam in (9, 10))


def _dv_confere(cpf, tam):
    soma = sum(int(d) * (tam + 1 - i) for i, d in enumerate(cpf[:tam]))
    return (soma * 10) % 11 % 10 == int(cpf[tam])


def _cpf_ok(cpf_n):
    return cpf_n is not None and _cpf_dv_ok(cpf_n)


def _normalizar_nome(nome):
    return RE_ESPACOS_MULTIPLOS.sub(" ", nome.strip())


def _nome_ok(nome_n):
    letras = sum(1 for ch in nome_n if ch.isalpha())
    return (len(nome_n) <= NOME_MAX and letras >= NOME_MIN_LETRAS
            and nome_n[0].isalpha() and nome_n[-1].isalpha()
            and RE_NOME.fullmatch(nome_n) is not None)


def _celular_ok(celular):
    return RE_CELULAR.fullmatch(celular) is not None


def _normalizar_celular(celular):
    return RE_NAO_DIGITO.sub("", celular)


def _email_ok(email):
    return RE_EMAIL.fullmatch(email) is not None


def _senha_ok(senha):
    return (SENHA_MIN <= len(senha) <= SENHA_MAX
            and all(r.search(senha) for r in RE_SENHA_REGRAS))


def _erro(status, mensagem):
    return ResultadoCadastro(status, mensagem)


class CadastroService:
    """Criacao de conta (ver ordem de validacao no docstring do modulo).

    Conta nova: saldo Decimal("0.00"); dados_conta(cpf) devolve None se nao existir.
    A senha e preservada exatamente como digitada (sem strip).
    """

    def __init__(self, auth):
        self._auth = auth
        self._contas = {}

    def cadastrar(self, nome, cpf, celular, email, senha, confirmacao_senha):
        erro = self._validar(nome, cpf, celular, email, senha, confirmacao_senha)
        if erro is not None:
            return erro
        self._gravar(normalizar_cpf(cpf), _normalizar_nome(nome),
                     _normalizar_celular(celular), email, senha)
        return _erro(CONTA_CRIADA, MSG_CONTA_CRIADA)

    def dados_conta(self, cpf):
        return self._contas.get(normalizar_cpf(cpf))

    def _validar(self, nome, cpf, celular, email, senha, confirmacao):
        if not _entrada_ok((nome, cpf, celular, email, senha, confirmacao)):
            return _erro(ENTRADA_INVALIDA, MSG_ENTRADA_INVALIDA)
        cpf_n = normalizar_cpf(cpf)
        if not _cpf_ok(cpf_n):
            return _erro(CPF_INVALIDO, MSG_CPF_INVALIDO)
        if cpf_n in self._contas:
            logger.warning("cadastro cpf_duplicado cpf=%s", mascarar(cpf_n))
            return _erro(CPF_JA_CADASTRADO, MSG_CPF_JA_CADASTRADO)
        return self._validar_dados(nome, celular, email, senha, confirmacao)

    @staticmethod
    def _validar_dados(nome, celular, email, senha, confirmacao):
        if not _nome_ok(_normalizar_nome(nome)):
            return _erro(NOME_INVALIDO, MSG_NOME_INVALIDO)
        if not _celular_ok(celular):
            return _erro(CELULAR_INVALIDO, MSG_CELULAR_INVALIDO)
        if not _email_ok(email):
            return _erro(EMAIL_INVALIDO, MSG_EMAIL_INVALIDO)
        if not _senha_ok(senha):
            return _erro(SENHA_FRACA, MSG_SENHA_FRACA)
        if senha != confirmacao:
            return _erro(CONFIRMACAO_DIFERENTE, MSG_CONFIRMACAO_DIFERENTE)
        return None

    def _gravar(self, cpf_n, nome_n, celular_n, email, senha):
        self._auth.cadastrar_usuario(cpf_n, senha)
        self._contas[cpf_n] = DadosConta(nome_n, celular_n, email, SALDO_INICIAL)
        logger.info("cadastro conta_criada cpf=%s", mascarar(cpf_n))
