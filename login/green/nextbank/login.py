"""FASE GREEN - codigo minimo para os testes passarem (ainda com duplicacoes)."""
import hashlib
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


@dataclass
class ResultadoLogin:
    status: str
    mensagem: str


class AuthService:
    def __init__(self, relogio, sms, max_tentativas=5, ttl_token=120):
        self.relogio = relogio
        self.sms = sms
        self.max_tentativas = max_tentativas
        self.ttl_token = ttl_token
        self.usuarios = {}
        self.tokens = {}

    def cadastrar_usuario(self, cpf, senha):
        cpf = re.sub(r"[.\-]", "", cpf)
        self.usuarios[cpf] = {
            "hash": hashlib.sha256(senha.encode()).hexdigest(),
            "falhas": 0,
            "bloqueada": False,
        }

    def login(self, cpf, senha):
        if not re.fullmatch(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}", cpf):
            logger.warning("login entrada_invalida")
            return ResultadoLogin(ENTRADA_INVALIDA, "Dados de entrada inválidos.")
        cpf = re.sub(r"[.\-]", "", cpf)
        usuario = self.usuarios.get(cpf)
        if usuario is None:
            logger.info("login negado cpf=***%s", cpf[-2:])
            return ResultadoLogin(NEGADO, "Credenciais inválidas.")
        if usuario["bloqueada"]:
            logger.warning("login bloqueada cpf=***%s", cpf[-2:])
            return ResultadoLogin(BLOQUEADA, "Conta bloqueada. Procure o atendimento.")
        if hashlib.sha256(senha.encode()).hexdigest() != usuario["hash"]:
            usuario["falhas"] += 1
            if usuario["falhas"] >= self.max_tentativas:
                usuario["bloqueada"] = True
                logger.warning("login bloqueada cpf=***%s", cpf[-2:])
                return ResultadoLogin(BLOQUEADA, "Conta bloqueada. Procure o atendimento.")
            logger.info("login negado cpf=***%s", cpf[-2:])
            return ResultadoLogin(NEGADO, "Credenciais inválidas.")
        usuario["falhas"] = 0
        codigo = "".join(secrets.choice("0123456789") for _ in range(6))
        self.tokens[cpf] = {"codigo": codigo, "emitido_em": self.relogio.agora(), "usado": False}
        self.sms.enviar(cpf, codigo)
        logger.info("login segundo_fator_enviado cpf=***%s", cpf[-2:])
        return ResultadoLogin(SEGUNDO_FATOR_NECESSARIO, "Informe o código enviado.")

    def confirmar_segundo_fator(self, cpf, codigo):
        cpf = re.sub(r"[.\-]", "", cpf)
        usuario = self.usuarios.get(cpf)
        if usuario is not None and usuario["bloqueada"]:
            return ResultadoLogin(BLOQUEADA, "Conta bloqueada. Procure o atendimento.")
        token = self.tokens.get(cpf)
        if token is None or token["usado"]:
            return ResultadoLogin(NEGADO, "Código inválido ou expirado.")
        if self.relogio.agora() - token["emitido_em"] > self.ttl_token:
            return ResultadoLogin(NEGADO, "Código inválido ou expirado.")
        if token["codigo"] != codigo:
            return ResultadoLogin(NEGADO, "Código inválido ou expirado.")
        token["usado"] = True
        logger.info("login acesso_liberado cpf=***%s", cpf[-2:])
        return ResultadoLogin(ACESSO_LIBERADO, "Acesso liberado.")

    def tentativas_falhas(self, cpf):
        return self.usuarios[re.sub(r"[.\-]", "", cpf)]["falhas"]

    def conta_bloqueada(self, cpf):
        return self.usuarios[re.sub(r"[.\-]", "", cpf)]["bloqueada"]
