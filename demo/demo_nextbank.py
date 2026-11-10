"""DEMONSTRACAO NextBank (nao e modulo de producao).

Fluxo: criar conta (Cadastro) -> login com 2o fator (Login, SMS falso que imprime o
codigo) -> creditar saldo inicial (parametro da demo) -> PIX -> Extrato.

Usa o codigo final (refactor) dos modulos SEM altera-lo: as pastas nextbank/ de
cadastro, login, pix e extrato sao somadas ao pacote 'nextbank' via __path__.
PIX e Extrato sao independentes do Cadastro; a ligacao e feita aqui, com o CPF
normalizado, como no teste de sistema. Tudo em memoria; SMS e antifraude sao falsos.

Uso:  python demo_nextbank.py          (interativo)
      python demo_nextbank.py --auto   (dados fixos de exemplo, sem input)
"""
import argparse
import os
import sys
from datetime import date, datetime
from decimal import Decimal

RAIZ = os.path.dirname(os.path.abspath(__file__))
# O primeiro 'nextbank' encontrado vira o pacote; o login.py e igual nos quatro modulos.
_MODULOS = ("cadastro", "login", "pix", "extrato")


def _preparar_pacote():
    pastas = [os.path.abspath(os.path.join(RAIZ, "..", m, "refactor")) for m in _MODULOS]
    sys.path.insert(0, pastas[0])
    import nextbank
    for pasta in pastas[1:]:
        caminho = os.path.join(pasta, "nextbank")
        if caminho not in nextbank.__path__:
            nextbank.__path__.append(caminho)


_preparar_pacote()

from nextbank.cadastro import CONTA_CRIADA, CadastroService  # noqa: E402
from nextbank.extrato import CREDITO, DEBITO, GERADO, ExtratoService  # noqa: E402
from nextbank.login import (  # noqa: E402
    ACESSO_LIBERADO,
    SEGUNDO_FATOR_NECESSARIO,
    AuthService,
    mascarar,
    normalizar_cpf,
)
from nextbank.pix import CONCLUIDA, PixService  # noqa: E402

SALDO_INICIAL_DEMO = Decimal("1000.00")  # parametro da demo (o cadastro nasce com saldo zero)
VALOR_PIX = Decimal("250.00")
# Facilidade SO da demo interativa; o Login real gera codigo aleatorio de uso unico.
CODIGO_DEMO = "123456"
CHAVE_DESTINO = "chave-destino-demo"
CONTA_ORIGEM, CONTA_DESTINO = "0001-1", "0002-2"

# Dados ficticios do modo --auto
DADOS_AUTO = {
    "nome": "Maria Souza Lima",
    "cpf": "390.533.447-05",
    "celular": "(11) 91234-5678",
    "email": "maria.lima@exemplo.com",
    "senha": "Senha@123",
}
# Titular ficticio do destino do PIX (a senha nunca e exibida)
DESTINO = {
    "nome": "Joao Pereira Santos",
    "cpf": "168.995.350-09",
    "celular": "(21) 98765-4321",
    "email": "joao.santos@exemplo.com",
    "senha": "Destino@456",
}


def formatar_reais(valor):
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + texto


class RelogioFalso:
    """Relogio do login (segundos); fixo, pois a demo e instantanea."""

    def agora(self):
        return 0.0


class RelogioPix:
    def agora(self):
        return datetime.now()


class AntifraudeFalso:
    def analisar(self, usuario, valor, instante):
        return False


class SmsFalso:
    """Em vez de enviar SMS, imprime o codigo na tela."""

    def __init__(self):
        self.ultimo = None

    def enviar(self, cpf, codigo):
        self.ultimo = codigo
        print(f"  [SMS FALSO] Codigo para o CPF {mascarar(cpf)}: {codigo}")

    def ultimo_codigo(self):
        return self.ultimo


class Demonstracao:
    """Guarda os servicos e os resultados de cada etapa (usado tambem pelo teste)."""

    def __init__(self):
        self.sms = SmsFalso()
        self.auth = AuthService(RelogioFalso(), self.sms)
        self.cadastro = CadastroService(self.auth)
        self.pix = PixService(RelogioPix(), AntifraudeFalso())
        self.extrato = ExtratoService()
        self.res_cadastro = self.res_duplicado = None
        self.res_login = self.res_fator = self.res_pix = self.res_extrato = None


def titulo(texto):
    print()
    print(f"=== {texto} ===")


def coletar_dados(entrada):
    return {
        "nome": entrada("Nome completo: "),
        "cpf": entrada("CPF: "),
        "celular": entrada("Celular: "),
        "email": entrada("E-mail: "),
        "senha": entrada("Senha: "),
        "confirmacao": entrada("Confirme a senha: "),
    }


def etapa_cadastro(demo, dados):
    r = demo.cadastro.cadastrar(dados["nome"], dados["cpf"], dados["celular"],
                                dados["email"], dados["senha"], dados["confirmacao"])
    print(f"  Resultado: {r.status} - {r.mensagem}")
    if r.status == CONTA_CRIADA:
        cpf = normalizar_cpf(dados["cpf"])
        conta = demo.cadastro.dados_conta(cpf)
        print(f"  Titular: {conta.nome} | CPF {mascarar(cpf)} | "
              f"saldo no cadastro: {formatar_reais(conta.saldo)}")
    return r


def etapa_cadastro_destino(demo):
    d = DESTINO
    r = demo.cadastro.cadastrar(d["nome"], d["cpf"], d["celular"], d["email"], d["senha"], d["senha"])
    print(f"  Conta de destino do PIX ({d['nome']}, CPF {mascarar(normalizar_cpf(d['cpf']))}): {r.status}")
    return r


def etapa_login(demo, cpf, senha, entrada, automatico=False):
    titulo("Login com segundo fator")
    r1 = demo.auth.login(cpf, senha)
    print(f"  Senha: {r1.status} - {r1.mensagem}")
    if r1.status != SEGUNDO_FATOR_NECESSARIO:
        return r1, None
    if not automatico:
        print(f"  Codigo de demonstracao (so nesta demo): {CODIGO_DEMO}")
    codigo = entrada("Digite o codigo recebido por SMS: ").strip()
    if codigo == CODIGO_DEMO:
        codigo = demo.sms.ultimo_codigo()  # troca pelo codigo real emitido pelo Login
    r2 = demo.auth.confirmar_segundo_fator(cpf, codigo)
    print(f"  Segundo fator: {r2.status} - {r2.mensagem}")
    return r1, r2


def etapa_saldo(demo, cpf_n):
    titulo(f"Saldo inicial da demo: {formatar_reais(SALDO_INICIAL_DEMO)}")
    print("  (parametro da demo; o cadastro nasce com saldo zero)")
    demo.pix.cadastrar_conta(cpf_n, CONTA_ORIGEM, SALDO_INICIAL_DEMO)
    demo.extrato.cadastrar_conta(cpf_n, CONTA_ORIGEM, Decimal("0.00"))
    demo.extrato.registrar_lancamento(CONTA_ORIGEM, datetime.now(), CREDITO, SALDO_INICIAL_DEMO,
                                      "credito inicial (demo)")
    print(f"  Saldo disponivel: {formatar_reais(demo.pix.saldo(CONTA_ORIGEM))}")


def etapa_pix(demo, cpf_n, cpf_destino_n):
    titulo(f"PIX de {formatar_reais(VALOR_PIX)}")
    demo.pix.cadastrar_conta(cpf_destino_n, CONTA_DESTINO, Decimal("0.00"))
    demo.pix.cadastrar_chave(CHAVE_DESTINO, CONTA_DESTINO)
    demo.extrato.cadastrar_conta(cpf_destino_n, CONTA_DESTINO, Decimal("0.00"))
    r = demo.pix.transferir(cpf_n, CONTA_ORIGEM, CHAVE_DESTINO, VALOR_PIX)
    print(f"  Resultado: {r.status} - {r.mensagem}")
    if r.status == CONCLUIDA:  # o integrador (esta demo) registra no Extrato
        agora = datetime.now()
        demo.extrato.registrar_lancamento(CONTA_ORIGEM, agora, DEBITO, VALOR_PIX, "pix enviado")
        demo.extrato.registrar_lancamento(CONTA_DESTINO, agora, CREDITO, VALOR_PIX, "pix recebido")
    print(f"  Saldo disponivel: {formatar_reais(demo.pix.saldo(CONTA_ORIGEM))}")
    return r


def etapa_extrato(demo, cpf_n):
    titulo("Extrato de hoje")
    hoje = date.today()
    r = demo.extrato.gerar_extrato(cpf_n, CONTA_ORIGEM, hoje, hoje)
    print(f"  Resultado: {r.status} - {r.mensagem}")
    if r.status == GERADO:
        print(f"  Saldo inicial: {formatar_reais(r.saldo_inicial)}")
        for l in r.lancamentos:
            sinal = "+" if l.tipo == CREDITO else "-"
            valor = sinal + formatar_reais(l.valor)
            print(f"  {l.data:%H:%M:%S}  {l.tipo:<8} {valor:>15}  {l.descricao}")
        print(f"  Saldo final:   {formatar_reais(r.saldo_final)}")
    return r


def executar(auto, entrada=input):
    """Roda o fluxo completo e devolve a Demonstracao (servicos + resultados)."""
    demo = Demonstracao()
    print("NextBank - DEMONSTRACAO (memoria, SMS falso, dados ficticios)")
    titulo("Cadastro (modo automatico)" if auto else "Cadastro: informe seus dados")
    if auto:
        dados = dict(DADOS_AUTO, confirmacao=DADOS_AUTO["senha"])
    else:
        dados = coletar_dados(entrada)
    demo.res_cadastro = etapa_cadastro(demo, dados)
    if demo.res_cadastro.status != CONTA_CRIADA:
        return demo
    if auto:
        titulo("Tentativa de cadastro com CPF duplicado")
        demo.res_duplicado = etapa_cadastro(demo, dados)
        entrada = lambda _prompt: demo.sms.ultimo_codigo()  # noqa: E731 - "le" o SMS
    titulo("Conta de destino do PIX")
    etapa_cadastro_destino(demo)
    demo.res_login, demo.res_fator = etapa_login(demo, dados["cpf"], dados["senha"], entrada, auto)
    if demo.res_fator is None or demo.res_fator.status != ACESSO_LIBERADO:
        return demo
    cpf_n = normalizar_cpf(dados["cpf"])
    etapa_saldo(demo, cpf_n)
    demo.res_pix = etapa_pix(demo, cpf_n, normalizar_cpf(DESTINO["cpf"]))
    demo.res_extrato = etapa_extrato(demo, cpf_n)
    print("\nFim da demonstracao.")
    return demo


def principal(argumentos=None, entrada=input):
    parser = argparse.ArgumentParser(description="Demonstracao NextBank")
    parser.add_argument("--auto", action="store_true", help="usa dados fixos, sem input()")
    args = parser.parse_args(argumentos)
    demo = executar(args.auto, entrada)
    ok = demo.res_extrato is not None and demo.res_extrato.status == GERADO
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(principal())
