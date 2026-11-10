"""FASE GREEN - codigo minimo para fazer os testes passarem (sem refatoracao)."""
from dataclasses import dataclass
import logging
import re
from decimal import Decimal

from nextbank.login import mascarar, normalizar_cpf

logger = logging.getLogger("nextbank.cadastro")

CONTA_CRIADA = "CONTA_CRIADA"
CPF_INVALIDO = "CPF_INVALIDO"
CPF_JA_CADASTRADO = "CPF_JA_CADASTRADO"
NOME_INVALIDO = "NOME_INVALIDO"
CELULAR_INVALIDO = "CELULAR_INVALIDO"
EMAIL_INVALIDO = "EMAIL_INVALIDO"
SENHA_FRACA = "SENHA_FRACA"
CONFIRMACAO_DIFERENTE = "CONFIRMACAO_DIFERENTE"
ENTRADA_INVALIDA = "ENTRADA_INVALIDA"

MSG_CONTA_CRIADA = "Conta criada com sucesso."
MSG_CPF_JA_CADASTRADO = "CPF já vinculado a uma conta."


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


class CadastroService:
    """Criacao de conta. Contrato (a implementar no Green):

    Ordem de validacao (devolve o PRIMEIRO erro):
      1. ENTRADA_INVALIDA (campo vazio/so espacos/None/tipo nao-str; vem antes de TUDO,
         inclusive de CPF_INVALIDO)
      2. CPF_INVALIDO (formato e digitos verificadores; aceita com/sem mascara)
      3. CPF_JA_CADASTRADO (logo apos validar o CPF, ANTES de nome/celular/e-mail/senha/confirmacao)
      4. NOME_INVALIDO (so letras com acento, espacos, hifen e apostrofo; ponto e digitos
         recusados; espacos nas pontas removidos e espacos internos duplos colapsados ANTES
         de validar; minimo 3 e maximo 100 caracteres apos essa normalizacao (" Jo " ->
         invalido, " Ana " -> guardado "Ana"); deve comecar e terminar com letra, logo
         "---", "'''", "-Ana", "Ana-", "Ana'" sao invalidos; "Ana-Clara" e "D'Avila" validos)
      5. CELULAR_INVALIDO (aceita mascara com parenteses, espaco e hifen; letras recusadas;
         normalizado para so digitos; 3o digito = 9)
      6. EMAIL_INVALIDO (exige @ e dominio com ponto)
      7. SENHA_FRACA (8 a 64 caracteres; maiuscula, minuscula, numero e especial; qualquer
         simbolo nao alfanumerico conta como especial, ESPACO NAO conta; mais de 64 -> SENHA_FRACA;
         a senha e preservada EXATAMENTE como digitada, sem strip: "Senha@123 " e
         "Senha @123" sao aceitas e o login exige a senha identica; senha so com espacos
         e ENTRADA_INVALIDA, ver item 1)
      8. CONFIRMACAO_DIFERENTE
    Conta nova: saldo Decimal("0.00"); dados_conta(cpf) devolve None se nao existir.
    """

    def __init__(self, auth):
        self._auth = auth
        self._contas = {}

    def cadastrar(self, nome, cpf, celular, email, senha, confirmacao_senha):
        campos = (nome, cpf, celular, email, senha, confirmacao_senha)
        for c in campos:
            if not isinstance(c, str) or not c.strip():
                return ResultadoCadastro(ENTRADA_INVALIDA, "Dados de entrada inválidos.")
        cpf_n = normalizar_cpf(cpf)
        if cpf_n is None or not _cpf_dv_ok(cpf_n):
            return ResultadoCadastro(CPF_INVALIDO, "CPF inválido.")
        if cpf_n in self._contas:
            logger.warning("cadastro cpf_duplicado cpf=%s", mascarar(cpf_n))
            return ResultadoCadastro(CPF_JA_CADASTRADO, MSG_CPF_JA_CADASTRADO)
        nome_n = re.sub(r" +", " ", nome.strip())
        letras = sum(1 for ch in nome_n if ch.isalpha())
        if (len(nome_n) > 100 or letras < 3 or not nome_n[0].isalpha()
                or not nome_n[-1].isalpha()
                or not re.fullmatch(r"(?:[^\W\d_]|[ '\-])+", nome_n)):
            return ResultadoCadastro(NOME_INVALIDO, "Nome inválido.")
        if not re.fullmatch(r"\(?\d{2}\)? ?9\d{4}-?\d{4}", celular):
            return ResultadoCadastro(CELULAR_INVALIDO, "Celular inválido.")
        celular_n = re.sub(r"\D", "", celular)
        if not re.fullmatch(r"[^@\s]+@[^@\s.]+(\.[^@\s.]+)+", email):
            return ResultadoCadastro(EMAIL_INVALIDO, "E-mail inválido.")
        if (not 8 <= len(senha) <= 64 or not re.search(r"[A-Z]", senha)
                or not re.search(r"[a-z]", senha) or not re.search(r"\d", senha)
                or not re.search(r"[^A-Za-z0-9\s]", senha)):
            return ResultadoCadastro(SENHA_FRACA, "Senha fraca.")
        if senha != confirmacao_senha:
            return ResultadoCadastro(CONFIRMACAO_DIFERENTE, "Confirmação de senha diferente.")
        self._auth.cadastrar_usuario(cpf_n, senha)
        self._contas[cpf_n] = DadosConta(nome_n, celular_n, email, Decimal("0.00"))
        logger.info("cadastro conta_criada cpf=%s", mascarar(cpf_n))
        return ResultadoCadastro(CONTA_CRIADA, MSG_CONTA_CRIADA)

    def dados_conta(self, cpf):
        cpf_n = normalizar_cpf(cpf)
        return self._contas.get(cpf_n)


def _cpf_dv_ok(cpf):
    if cpf == cpf[0] * 11:
        return False
    for tam in (9, 10):
        soma = sum(int(d) * (tam + 1 - i) for i, d in enumerate(cpf[:tam]))
        dv = (soma * 10) % 11 % 10
        if dv != int(cpf[tam]):
            return False
    return True
