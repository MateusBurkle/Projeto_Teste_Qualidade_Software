"""FASE RED - apenas a interface (stub). Nada esta implementado; os testes devem FALHAR."""
from dataclasses import dataclass
from decimal import Decimal

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
        pass

    def cadastrar(self, nome, cpf, celular, email, senha, confirmacao_senha):
        raise NotImplementedError

    def dados_conta(self, cpf):
        raise NotImplementedError
