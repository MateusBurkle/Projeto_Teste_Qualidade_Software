# Testes de desempenho com Locust (meta M5)

Casos do Plano de Testes (Word, secao 4) que ficaram fora do TDD: CT-P12, CT-P13, CT-P15, CT-P16 (PIX) e CT-E05, CT-E06, CT-E09 (Extrato).
Alvo: `pix/refactor/nextbank/pix.py` e `extrato/refactor/nextbank/extrato.py`.

## Abordagem

O NextBank e Python puro em memoria, sem servidor HTTP. Cada usuario virtual e um `locust.User` que chama
`PixService` / `ExtratoService` direto, mede o tempo e registra com `environment.events.request.fire`.
O Locust faz o resto (usuarios, taxa de entrada, media, P95, falhas). Servicos externos sao fakes e os dados sao ficticios.
Ao final, o script imprime um VEREDITO com `[OK]`, `[FALHA]` ou `[INFO]` por criterio e sai com codigo 1 se algum falhar.

Atencao: como tudo e em memoria, os tempos medidos sao de microssegundos (aparecem como 0 ms) e sempre cumprem 2 s / 3 s.
Os resultados validam logica, consistencia e taxa de sucesso, nao o desempenho do ambiente real.

## Instalar

```
pip install -r requirements.txt
```

## Executar (rodar dentro desta pasta)

Variavel `NB_ESCALA_TEMPO` multiplica todas as duracoes dos cenarios (1 = valores completos; 0.05 = teste rapido).
Nao grave cache: defina `PYTHONDONTWRITEBYTECODE=1`.

| Caso | Cenario | Rapido (escala 0.05) | Completo |
| --- | --- | --- | --- |
| CT-P12 | carga: 100 usuarios (5 min) | `NB_ESCALA_TEMPO=0.05 locust -f locustfile.py,cenario_carga.py PixUser --headless` | sem `NB_ESCALA_TEMPO` |
| CT-P13 | pico: 10x (1.000 usuarios) e recuperacao | `NB_ESCALA_TEMPO=0.05 locust -f locustfile.py,cenario_pico.py PixUser --headless` | idem |
| CT-P15 | estresse: degraus 5x, 10x, 15x, 20x e recuperacao em 2 min | `NB_ESCALA_TEMPO=0.05 locust -f locustfile.py,cenario_estresse.py PixUser --headless` | idem |
| CT-P16 | resistencia: 100 usuarios por 30 min | `NB_ESCALA_TEMPO=0.05 locust -f locustfile.py,cenario_resistencia.py PixUser --headless` | idem |
| CT-E05, E06, E09 | extrato: 1.000 requisicoes | `locust -f locustfile.py ExtratoUser -u 100 -r 20 --headless` (ja leva segundos) | idem |

No PowerShell, defina a variavel antes: `$env:NB_ESCALA_TEMPO="0.05"; $env:PYTHONDONTWRITEBYTECODE="1"; locust ...`.
Para guardar evidencias, acrescente `--csv evidencias/<cenario> --html evidencias/<cenario>.html`.

## Criterios (Plano)

- CT-P12 (RD-01, RC-04): media <= 2 s, P95 <= 3 s, sucesso >= 99,9% com 100 usuarios.
- CT-P13 (RD-02): erro < 1% no pico de 10x; volta ao normal (RD-01) na janela de recuperacao.
- CT-P15 (RD-03): degraus ate 20x; volta ao normal em ate 2 min; nenhuma transacao confirmada perdida ou duplicada (saldo de cada conta = esperado pelas transferencias confirmadas). A degradacao por degrau e so informativa.
- CT-P16 (RD-04, RC-04): media final nao cresce mais de 20% sobre a inicial; erro < 1%; memoria (tracemalloc) amostrada e informada.
- CT-E09 (RC-01, RC-04): exatamente 1.000 requisicoes, sucesso >= 99,9%. CT-E05 (RF-06): saldo final = inicial + creditos - debitos. CT-E06 (RC-03): exatamente N lancamentos, sem duplicar.

## Parametros que NAO estao no Plano (hipoteses; ver perguntas ao usuario)

Duracao da carga normal (5 min), duracoes e degraus do pico/estresse, espera entre acoes (1 a 3 s: `NB_PENSAR_MIN/MAX`),
janelas de inicio/fim da resistencia (10% cada), piso de ruido de 1 ms (`NB_PISO_MS`), 50 lancamentos por conta (`NB_LANCAMENTOS`).

## Arquivos

- `locustfile.py`: usuarios `PixUser` e `ExtratoUser`, avaliacao dos criterios.
- `cenario_carga.py`, `cenario_pico.py`, `cenario_estresse.py`, `cenario_resistencia.py`: forma da carga (um por arquivo).
- `comum.py`: parametros e carga dos modulos.
