"""FASE REFACTOR - mesmo comportamento da fase Green, com o codigo reorganizado.

Melhorias: constantes e mensagens centralizadas, separacao de responsabilidades
(validacao de CPF, hash de senha, servico de token), metodos pequenos e senha com
PBKDF2 + sal e comparacao em tempo constante. Os testes nao foram alterados.
"""
import hashlib
import hmac
import logging
import re
import secrets
from dataclasses import dataclass

logger = logging.getLogger("nextbank.login")

SEGUNDO_FATOR_NECESSARIO = "SEGUNDO_FATOR_NECESSARIO"
ACESSO_LIBERADO = "ACESSO_LIBERADO"
NEGADO = "NEGADO"
BLOQUEADA = "BLOQUEADA"
ENTRADA_INVALIDA = "ENTRADA_INVALIDA"

MSG_ENTRADA_INVALIDA = "Dados de entrada inválidos."
MSG_CREDENCIAIS_INVALIDAS = "Credenciais inválidas."
MSG_CONTA_BLOQUEADA = "Conta bloqueada. Procure o atendimento."
MSG_INFORME_CODIGO = "Informe o código enviado."
MSG_CODIGO_INVALIDO = "Código inválido ou expirado."
MSG_ACESSO_LIBERADO = "Acesso liberado."

_PADRAO_CPF = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")
_ITERACOES_HASH = 100_000
_TAMANHO_CODIGO = 6


@dataclass
class ResultadoLogin:
    status: str
    mensagem: str


@dataclass
class Usuario:
    senha_hash: bytes
    sal: bytes
    falhas: int = 0
    bloqueada: bool = False


@dataclass
class Token:
    codigo: str
    emitido_em: float
    usado: bool = False


def normalizar_cpf(cpf):
    """Retorna so os digitos do CPF ou None se o formato for invalido."""
    if not isinstance(cpf, str) or not _PADRAO_CPF.fullmatch(cpf):
        return None
    return re.sub(r"\D", "", cpf)


def mascarar(cpf):
    return "***" + cpf[-2:]


def _hash_senha(senha, sal):
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, _ITERACOES_HASH)


class ServicoToken:
    """Gera e valida o codigo do segundo fator (validade limitada e uso unico)."""

    def __init__(self, relogio, ttl):
        self._relogio = relogio
        self._ttl = ttl
        self._tokens = {}

    def emitir(self, cpf):
        codigo = "".join(secrets.choice("0123456789") for _ in range(_TAMANHO_CODIGO))
        self._tokens[cpf] = Token(codigo, self._relogio.agora())
        return codigo

    def consumir(self, cpf, codigo):
        token = self._tokens.get(cpf)
        if token is None or token.usado or self._expirou(token):
            return False
        if not hmac.compare_digest(token.codigo, codigo):
            return False
        token.usado = True
        return True

    def _expirou(self, token):
        return self._relogio.agora() - token.emitido_em > self._ttl


class AuthService:
    def __init__(self, relogio, sms, max_tentativas=5, ttl_token=120):
        self._sms = sms
        self._max_tentativas = max_tentativas
        self._tokens = ServicoToken(relogio, ttl_token)
        self._usuarios = {}

    def cadastrar_usuario(self, cpf, senha):
        sal = secrets.token_bytes(16)
        self._usuarios[normalizar_cpf(cpf)] = Usuario(_hash_senha(senha, sal), sal)

    def login(self, cpf, senha):
        cpf_norm = normalizar_cpf(cpf)
        if cpf_norm is None:
            logger.warning("login entrada_invalida")
            return ResultadoLogin(ENTRADA_INVALIDA, MSG_ENTRADA_INVALIDA)
        usuario = self._usuarios.get(cpf_norm)
        if usuario is None:
            return self._negar(cpf_norm)
        if usuario.bloqueada:
            return self._bloqueada(cpf_norm)
        if not self._senha_confere(usuario, senha):
            return self._registrar_falha(cpf_norm, usuario)
        usuario.falhas = 0
        self._sms.enviar(cpf_norm, self._tokens.emitir(cpf_norm))
        logger.info("login segundo_fator_enviado cpf=%s", mascarar(cpf_norm))
        return ResultadoLogin(SEGUNDO_FATOR_NECESSARIO, MSG_INFORME_CODIGO)

    def confirmar_segundo_fator(self, cpf, codigo):
        cpf_norm = normalizar_cpf(cpf) or ""
        usuario = self._usuarios.get(cpf_norm)
        if usuario is not None and usuario.bloqueada:
            return ResultadoLogin(BLOQUEADA, MSG_CONTA_BLOQUEADA)
        if not self._tokens.consumir(cpf_norm, codigo):
            return ResultadoLogin(NEGADO, MSG_CODIGO_INVALIDO)
        logger.info("login acesso_liberado cpf=%s", mascarar(cpf_norm))
        return ResultadoLogin(ACESSO_LIBERADO, MSG_ACESSO_LIBERADO)

    def tentativas_falhas(self, cpf):
        return self._usuarios[normalizar_cpf(cpf)].falhas

    def conta_bloqueada(self, cpf):
        return self._usuarios[normalizar_cpf(cpf)].bloqueada

    @staticmethod
    def _senha_confere(usuario, senha):
        return hmac.compare_digest(usuario.senha_hash, _hash_senha(senha, usuario.sal))

    def _registrar_falha(self, cpf, usuario):
        usuario.falhas += 1
        if usuario.falhas >= self._max_tentativas:
            usuario.bloqueada = True
            return self._bloqueada(cpf)
        return self._negar(cpf)

    @staticmethod
    def _negar(cpf):
        logger.info("login negado cpf=%s", mascarar(cpf))
        return ResultadoLogin(NEGADO, MSG_CREDENCIAIS_INVALIDAS)

    @staticmethod
    def _bloqueada(cpf):
        logger.warning("login bloqueada cpf=%s", mascarar(cpf))
        return ResultadoLogin(BLOQUEADA, MSG_CONTA_BLOQUEADA)
