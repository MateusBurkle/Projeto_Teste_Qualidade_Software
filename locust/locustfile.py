"""Usuarios virtuais e avaliacao dos criterios do Plano (Quadros 10, 12 e 13).

Abordagem: o NextBank e Python puro em memoria (sem servidor HTTP). Cada usuario virtual e um
locust.User comum que chama PixService / ExtratoService (fase REFACTOR) diretamente, mede o tempo
da chamada e o registra com environment.events.request.fire. Assim o Locust gera a carga
(usuarios e taxa de entrada), as estatisticas (media, P95, taxa de falha) e o relatorio, sem criar
nenhuma API. Servicos externos (antifraude, relogio) sao fakes; todos os dados sao ficticios.

  PIX (CT-P12, P13, P15, P16): locust -f locustfile.py,cenario_<nome>.py PixUser --headless
  Extrato (CT-E05, E06, E09):  locust -f locustfile.py ExtratoUser --headless
"""
import itertools
import time
import tracemalloc
from datetime import date, datetime
from decimal import Decimal

import gevent
from locust import User, between, events, task

import comum
from comum import estado, extrato, pix

D = Decimal
SALDO_INICIAL = D("1000000.00")
VALOR_PIX = D("10.00")  # bem abaixo do alto valor (R$ 7.000,00): fluxo normal


class RelogioReal:
    def agora(self):
        return datetime.now()


class AntifraudeFalso:
    """Mock: nunca sinaliza padrao atipico (nao e o foco da carga)."""

    def analisar(self, usuario, valor, instante):
        return False


# ---- Estado dos servicos (um por processo) ----------------------------------------------------
servico_pix = pix.PixService(RelogioReal(), AntifraudeFalso())
servico_extrato = extrato.ExtratoService()
saldos_esperados = {}  # conta -> saldo esperado, calculado so com transferencias confirmadas
contas_pix = []
contadores = {"e09": 0, "e09_encerrando": False, "e05_falhas": 0, "e06_falhas": 0}
amostras_memoria = []
_ids = itertools.count(1)


def _nome(base):
    return f"{base} [{estado['fase']}]" if estado["cenario"] else base


def _disparar(environment, tipo, nome, duracao_ms, exc):
    environment.events.request.fire(
        request_type=tipo, name=nome, response_time=duracao_ms, response_length=0, exception=exc, context={},
    )


class PixUser(User):
    """CT-P12 (carga), CT-P13 (pico), CT-P15 (estresse), CT-P16 (resistencia): transferencia PIX."""

    wait_time = between(comum.PENSAR_MIN, comum.PENSAR_MAX)

    def on_start(self):
        n = next(_ids)
        self.usuario, self.origem, self.destino, self.chave = f"u{n}", f"O{n}", f"D{n}", f"chave{n}"
        servico_pix.cadastrar_conta(self.usuario, self.origem, SALDO_INICIAL)
        servico_pix.cadastrar_conta(f"d{n}", self.destino, SALDO_INICIAL)
        servico_pix.cadastrar_chave(self.chave, self.destino)
        saldos_esperados[self.origem] = SALDO_INICIAL
        saldos_esperados[self.destino] = SALDO_INICIAL
        contas_pix.extend([self.origem, self.destino])

    @task
    def transferir(self):
        inicio = time.perf_counter()
        resultado = servico_pix.transferir(self.usuario, self.origem, self.chave, VALOR_PIX)
        duracao_ms = (time.perf_counter() - inicio) * 1000
        exc = None if resultado.status == pix.CONCLUIDA else Exception(f"{resultado.status}: {resultado.mensagem}")
        _disparar(self.environment, "PIX", _nome("transferir"), duracao_ms, exc)
        if exc is None:  # so transferencias confirmadas entram no saldo esperado
            saldos_esperados[self.origem] -= VALOR_PIX
            saldos_esperados[self.destino] += VALOR_PIX


class ExtratoUser(User):
    """CT-E09 (taxa de sucesso, 1.000 requisicoes), CT-E05 (saldo) e CT-E06 (sem omissao/duplicidade)."""

    wait_time = between(comum.PENSAR_MIN, comum.PENSAR_MAX)

    def on_start(self):
        estado["cenario"] = estado["cenario"] or "extrato"
        n = next(_ids)
        self.usuario, self.conta = f"x{n}", f"X{n}"
        abertura = D("500.00")
        servico_extrato.cadastrar_conta(self.usuario, self.conta, abertura)
        self.descricoes, saldo = set(), abertura
        for i in range(comum.N_LANCAMENTOS):
            tipo = extrato.CREDITO if i % 2 == 0 else extrato.DEBITO
            valor = D("25.00") + i
            descricao = f"{self.conta}-{i}"
            data = datetime(2026, 11, 1 + i % 28, 10, i % 60)
            servico_extrato.registrar_lancamento(self.conta, data, tipo, valor, descricao)
            saldo += valor if tipo == extrato.CREDITO else -valor
            self.descricoes.add(descricao)
        self.saldo_final_esperado = saldo

    @task
    def gerar_extrato(self):
        if contadores["e09"] >= comum.LIMITE_E09:  # CT-E09: para exatamente apos 1.000 requisicoes
            if not contadores["e09_encerrando"]:
                contadores["e09_encerrando"] = True
                gevent.spawn(self.environment.runner.quit)
            return
        contadores["e09"] += 1
        inicio = time.perf_counter()
        r = servico_extrato.gerar_extrato(self.usuario, self.conta, date(2026, 11, 1), date(2026, 11, 30))
        duracao_ms = (time.perf_counter() - inicio) * 1000
        exc = None if r.status == extrato.GERADO else Exception(f"{r.status}: {r.mensagem}")
        if exc is None:
            if r.saldo_final != self.saldo_final_esperado:  # CT-E05
                contadores["e05_falhas"] += 1
            if len(r.lancamentos) != comum.N_LANCAMENTOS or {l.descricao for l in r.lancamentos} != self.descricoes:
                contadores["e06_falhas"] += 1  # CT-E06
        _disparar(self.environment, "EXTRATO", _nome("gerar"), duracao_ms, exc)


# ---- Memoria (CT-P16: "memoria estavel"), amostrada so no cenario de resistencia ----------------
def _amostrar_memoria():
    while True:
        amostras_memoria.append(tracemalloc.get_traced_memory()[0] / 1024)  # KiB
        gevent.sleep(max(1.0, 10 * comum.ESCALA_TEMPO))


@events.test_start.add_listener
def _iniciar(environment, **kw):
    if estado["cenario"] == "resistencia":
        tracemalloc.start()
        gevent.spawn(_amostrar_memoria)


# ---- Avaliacao dos criterios -------------------------------------------------------------------
def _linhas(environment, prefixo):
    return {n: s for (n, _m), s in environment.stats.entries.items() if n.startswith(prefixo)}


def _agregar(lista):
    """Devolve (requisicoes, falhas, media_ms, p95_ms) de uma lista de linhas de estatistica."""
    n = sum(s.num_requests for s in lista)
    falhas = sum(s.num_failures for s in lista)
    media = sum(s.avg_response_time * s.num_requests for s in lista) / n if n else 0.0
    p95 = max((s.get_response_time_percentile(0.95) or 0 for s in lista), default=0)
    return n, falhas, media, p95


def _fase(environment, prefixo, fase):
    return _agregar([s for n, s in _linhas(environment, prefixo).items() if n.endswith(f"[{fase}]")])


def _fmt(rotulo, ok, detalhe):
    marca = "INFO" if ok is None else "OK" if ok else "FALHA"
    return f"  [{marca}] {rotulo}: {detalhe}"


def _normal(n, falhas, media, p95):
    """'Normal' = RD-01 (media <= 2 s e P95 <= 3 s), com requisicoes no periodo."""
    return n > 0 and media <= comum.MEDIA_MAX_MS and p95 <= comum.P95_MAX_MS


def _conservacao():
    """CT-P15: nenhuma transacao confirmada perdida ou duplicada (saldo de cada conta = esperado)."""
    erros = [c for c in contas_pix if servico_pix.saldo(c) != saldos_esperados[c]]
    return not erros, f"{len(contas_pix)} contas conferidas, {len(erros)} divergentes"


def _avaliar_pix(environment, cenario, fases):
    n, falhas, media, p95 = _agregar(list(_linhas(environment, "transferir").values()))
    taxa_erro = falhas / n if n else 1
    res = [_fmt("requisicoes / falhas", None, f"{n} / {falhas} (erro {taxa_erro:.3%})")]
    if cenario == "carga":  # CT-P12 - RD-01, RC-04
        res += [
            _fmt("CT-P12 media <= 2 s", media <= comum.MEDIA_MAX_MS, f"{media:.3f} ms"),
            _fmt("CT-P12 P95 <= 3 s", p95 <= comum.P95_MAX_MS, f"{p95} ms"),
            _fmt("CT-P12 sucesso >= 99,9%", 1 - taxa_erro >= comum.SUCESSO_MIN, f"{1 - taxa_erro:.3%}"),
        ]
    if cenario in ("pico", "estresse"):
        r = _fase(environment, "transferir", "recuperacao")
        res.append(_fmt("recuperacao em ate 2 min (RD-01 no periodo)", _normal(*r), f"media {r[2]:.3f} ms, P95 {r[3]} ms, {r[0]} req"))
    if cenario == "pico":  # CT-P13 - RD-02
        p = _fase(environment, "transferir", "pico")
        erro = p[1] / p[0] if p[0] else 1
        res.append(_fmt("CT-P13 erro no pico < 1%", erro < comum.ERRO_PICO_MAX, f"{erro:.3%} ({p[0]} req)"))
    if cenario == "estresse":  # CT-P15 - RD-03
        for f in (f for f in fases if f.startswith("degrau")):
            d = _fase(environment, "transferir", f)
            erro = d[1] / d[0] if d[0] else 0
            res.append(_fmt(f"{f} (degradacao, informativo)", None, f"{d[0]} req, erro {erro:.3%}, media {d[2]:.3f} ms, P95 {d[3]} ms"))
        res.append(_fmt("CT-P15 sem perda/duplicidade", *_conservacao()))
    if cenario == "resistencia":  # CT-P16 - RD-04, RC-04
        ini, fim = _fase(environment, "transferir", "inicio"), _fase(environment, "transferir", "fim")
        cresc = (fim[2] - ini[2]) / ini[2] if ini[2] else 0
        ruido = abs(fim[2] - ini[2]) < comum.PISO_MS
        res.append(_fmt("CT-P16 media cresce <= 20% (fim x inicio)", cresc <= comum.CRESCIMENTO_MAX or ruido,
                        f"{ini[2]:.3f} ms -> {fim[2]:.3f} ms ({cresc:+.1%}; piso de ruido {comum.PISO_MS} ms)"))
        res.append(_fmt("CT-P16 erro < 1%", taxa_erro < comum.ERRO_PICO_MAX, f"{taxa_erro:.3%}"))
        if len(amostras_memoria) >= 3:
            t = len(amostras_memoria) // 3
            a, b = sum(amostras_memoria[:t]) / t, sum(amostras_memoria[-t:]) / t
            res.append(_fmt("CT-P16 memoria (informativo; sem limite no Plano)", None,
                            f"{a:.0f} KiB -> {b:.0f} KiB, {len(amostras_memoria)} amostras"))
        res.append(_fmt("conservacao de saldos", *_conservacao()))
    return res


def _avaliar_extrato(environment):
    n, falhas, media, p95 = _agregar(list(_linhas(environment, "gerar").values()))
    sucesso = 1 - falhas / n if n else 0
    return [
        _fmt("CT-E09 requisicoes executadas", n == comum.LIMITE_E09, f"{n} (esperado {comum.LIMITE_E09})"),
        _fmt("CT-E09 sucesso >= 99,9%", sucesso >= comum.SUCESSO_MIN, f"{sucesso:.3%} ({falhas} falhas)"),
        _fmt("CT-E05 saldo final = inicial + creditos - debitos", contadores["e05_falhas"] == 0,
             f"{contadores['e05_falhas']} inconsistencias"),
        _fmt("CT-E06 exatamente N lancamentos, sem duplicar", contadores["e06_falhas"] == 0,
             f"{contadores['e06_falhas']} inconsistencias (N={comum.N_LANCAMENTOS})"),
        _fmt("tempo (informativo)", None, f"media {media:.3f} ms, P95 {p95} ms"),
    ]


@events.test_stop.add_listener
def _avaliar(environment, **kw):
    cenario = estado["cenario"]
    if cenario is None:
        return
    fases = sorted({n.split("[")[-1].rstrip("]") for n in _linhas(environment, "transferir")})
    linhas = _avaliar_extrato(environment) if cenario == "extrato" else _avaliar_pix(environment, cenario, fases)
    print(f"\n=== VEREDITO NextBank - cenario '{cenario}' (escala de tempo {comum.ESCALA_TEMPO}) ===")
    print("\n".join(linhas))
    if any("[FALHA]" in linha for linha in linhas):
        environment.process_exit_code = 1
