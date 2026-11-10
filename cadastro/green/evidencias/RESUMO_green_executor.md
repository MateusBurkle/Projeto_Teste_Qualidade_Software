# RESUMO - Validacao da fase GREEN do Cadastro (M8) - executor de testes (09/11/2026)

Ambiente: Python 3.14.2, pytest 9.1.1, pytest-cov 7.1.0 (coverage 7.17.2), radon 6.0.1 (todos disponiveis).

## Resultado
- Testes: 135 coletados, 135 aprovados, 0 falhas (pytest_green_executor.txt).
- tests/test_cadastro.py identico a cadastro/red (diff -r sem diferencas). SHA-256 ambos: 8e3c4f412968e5805fddde9dc4adf38c3f36f780f7d2ca4ad1e2ae3502e05d1b
- nextbank/login.py identico a login/refactor. SHA-256 ambos: 11ff0889bcf9e756b368247bd176b0dea6fc81722305dff7909ff16bdfee2c75

## Cobertura (cobertura_green_executor.txt; --cov=nextbank --cov-branch)
- cadastro.py: 65 instrucoes, 0 perdidas; 24 ramos, 0 parciais -> 100% instrucoes e 100% ramos. Sem linhas descobertas.
- login.py (na suite): 73% (25 perdidas de 112; 84-90, 93, 110-111, 116, 125-132, 135, 138, 147-148, 158-159); fora do escopo do M8, ja validado em login.
- TOTAL do pacote: 84%.
- Criterio de saida (instr >= 80%, decisoes >= 70%) atendido para cadastro.py.

## Complexidade ciclomatica (cadastro.py; complexidade_green_executor.txt)
- 7 blocos; media 5,71 (B); maxima 22 (D) em CadastroService.cadastrar; CadastroService classe B (9); _cpf_dv_ok A (5); demais A (1).
- Observacao: cadastrar com CC 22 (D) e ponto de atencao para a fase refactor.

## Tamanho (tamanho_green_executor.txt)
- LOC 114, LLOC 80, SLOC 75, comentarios 0, linhas simples de comentario 1, multi (docstrings) 22, brancas 16.
- Indice de manutenibilidade: A (61,64).

## Testes por ID (todos PASSED)
| ID | Testes | Resultado |
|---|---|---|
| CT-C01 | 3 | 3 aprovados |
| CT-C02 | 4 | 4 aprovados |
| CT-C03 | 3 | 3 aprovados |
| CT-C04 | 7 | 7 aprovados |
| CT-C05 | 2 | 2 aprovados |
| CT-C06 | 1 | 1 aprovado |
| CT-C07 | 1 | 1 aprovado |
| CT-C08 | 1 | 1 aprovado |
| CT-C09 | 28 | 28 aprovados |
| CT-C10 | 5 | 5 aprovados |
| CT-C11 | 1 | 1 aprovado |
| CT-C12 | 42 | 42 aprovados |
| CT-C13 | 37 | 37 aprovados |
| Total | 135 | 135 aprovados |
(Contagem por nome do teste test_ct_cNN_*, incluindo parametrizacoes.)

## Veredito: GREEN VALIDO. Nenhum incidente.
Nenhum teste ou codigo foi alterado; pytest_green.txt do desenvolvedor preservado; sem .coverage/__pycache__/.pytest_cache no projeto.
