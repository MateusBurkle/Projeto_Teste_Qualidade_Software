# Teste geral depois da correcao INC-S01/INC-S02 - veredito

**Veredito: NAO APROVADO para fechamento. 2 testes legados do PIX (CT-P11, CT-P17) falham com o pix.py corrigido.**

| Item | Esperado | Obtido |
|---|---|---|
| login/refactor | 14 | 14 passed |
| pix/refactor (pix.py antigo local) | 20 | 20 passed |
| extrato/refactor | 7 | 7 passed |
| sistema | 5 | 5 passed |
| seguranca | 19 | 19 passed |
| Prova de nao-regressao: 20 CT-P contra pix.py corrigido | 20 | **18 passed, 2 failed (CT-P11, CT-P17)** |
| CT-R01 (L01, L04, L06, P01, P06, P08) | 6/6 | 6/6 passed |
| Consolidado 41 unitarios (sistema/nextbank) | 41/41 | **39/41** |
| Cobertura consolidada (41 testes) | 99% | 99% (pix.py 98%, linha 95 nao coberta so por eles) |
| Cobertura com sistema+seguranca (65 testes) | - | 100% (63 passed, 2 failed) |

## Causa
CT-P11 e CT-P17 afirmam `registro.usuario == USUARIO_A` (CPF em claro). Com INC-S01 (RS-05) o pix.py grava o usuario mascarado (`***_a`, `***05`). E conflito entre teste legado desatualizado e a correcao, nao falha funcional do PIX. Nada foi alterado (so relato).

## Observacao (nao corrigida)
`sistema/nextbank/pix.py` DIFERE de `pix/refactor/nextbank/pix.py`: (1) `from nextbank.login import mascarar`; (2) `_valor_valido` (rejeita bool/nao numerico, RS-07) no lugar de `valor <= 0`; (3) auditoria com `mascarar(usuario)`. Tambem diferem em fim de linha (CRLF x LF). Ha duas versoes do PIX no projeto.

## Regressao vs teste_geral_final anterior (41/41, 6/6, 99%)
- Regrediu: 41/41 -> 39/41 (CT-P11, CT-P17), contra o codigo corrigido. CT-R01 6/6 e cobertura 99% mantidos.

## Recomendacao
Atualizar CT-P11/CT-P17 em pix/refactor/tests para esperar `mascarar(usuario)` (decisao do dono) e sincronizar pix/refactor/nextbank/pix.py com sistema; depois repetir. Incidente a registrar (secao 4.1.8): INC-S03, teste legado desalinhado com RS-05, severidade media.
Detalhes: teste_geral_depois.txt.
