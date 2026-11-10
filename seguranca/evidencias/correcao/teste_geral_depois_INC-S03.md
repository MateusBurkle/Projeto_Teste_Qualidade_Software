# Teste geral apos INC-S03 (2026-11-08)

**Veredito: APROVADO.** 65/65 testes, sem falhas e sem defeitos novos.

| Item | Resultado |
|---|---|
| login/refactor, pix/refactor, extrato/refactor | 14 + 20 + 7 = **41/41** |
| sistema, seguranca | 5/5, 19/19 |
| CT-R01 (L01, L04, L06, P01, P06, P08) | **6/6** (E05/E06 sao Locust, nao reexecutados) |
| Cobertura refactor (41 testes) | 99%: 263/265 instr, 52/54 ramos (faltam login.py:114 e pix.py:95) |
| Cobertura com sistema+seguranca (65) | 100%: 265/265 instr, 54/54 ramos |
| pix.py refactor x sistema; login.py (3 pastas) | identicos (ignorando fim de linha) |
| Evidencia `antes_INC-S03` | intacta (7 arquivos); antigo pix.py + teste antigo reexecutados: 20/20 |

**Comparacao**
- Baseline `teste_geral_final`: 41/41, 258/259 instr, 51/52 ramos, 99%.
- `teste_geral_depois` (antes de INC-S03): 39/41 (falhavam CT-P11 e CT-P17).
- Agora: 41/41, 263/265 instr, 52/54 ramos, 99%.
- O total subiu de 259 para 265 instr (pix.py de 82 para 88) por causa da correcao INC-S01/S02 (mascaramento na auditoria e validacao de valor). Desses acrescimos, so pix.py:95 nao e coberto pelos testes refactor; sistema/seguranca cobrem.
- 39 para 41: CT-P11 e CT-P17 alinhados ao CPF mascarado (RS-05/RS-06). Nenhum codigo de producao mudou nesta etapa.

Detalhes: `teste_geral_depois_INC-S03.txt`.
