"""FASE RED - apenas a interface (stub). Nada esta implementado; os testes devem FALHAR."""
from dataclasses import dataclass

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
        pass

    def cadastrar_usuario(self, cpf, senha):
        pass  # ainda sem comportamento

    def login(self, cpf, senha):
        raise NotImplementedError

    def confirmar_segundo_fator(self, cpf, codigo):
        raise NotImplementedError

    def tentativas_falhas(self, cpf):
        raise NotImplementedError

    def conta_bloqueada(self, cpf):
        raise NotImplementedError
