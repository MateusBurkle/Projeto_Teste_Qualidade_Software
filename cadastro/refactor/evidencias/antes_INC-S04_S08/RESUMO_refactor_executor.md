# RESUMO - Validacao da fase REFACTOR do Cadastro (M8) - executor (09/11/2026)

Ambiente: Python 3.14.2, pytest 9.1.1, pytest-cov e radon 6.0.1 disponiveis.

## Resultado
- 135 testes coletados, 135 aprovados, 0 falhas (pytest_refactor_executor.txt). pytest_refactor.txt do desenvolvedor preservado.
- tests/test_cadastro.py identico a cadastro/green e cadastro/red (diff -r sem diferencas). SHA-256 nos tres: 8e3c4f412968e5805fddde9dc4adf38c3f36f780f7d2ca4ad1e2ae3502e05d1b
- nextbank/login.py identico a login/refactor. SHA-256: 11ff0889bcf9e756b368247bd176b0dea6fc81722305dff7909ff16bdfee2c75

## Cobertura (--cov=nextbank --cov-branch)
- cadastro.py: 110 instrucoes, 0 perdidas; 20 ramos, 0 parciais -> 100% / 100%. Sem linhas descobertas.
- login.py (na suite): 73% (25 perdidas de 112; 84-90, 93, 110-111, 116, 125-132, 135, 138, 147-148, 158-159), fora do escopo do M8.
- TOTAL: 86%. Criterio (instr >= 80%, decisoes >= 70%) atendido.

## Complexidade ciclomatica (cadastro.py)
| Metrica | Green | Refactor |
|---|---|---|
| Blocos | 7 | 21 |
| Media | 5,71 (B) | 2,19 (A) |
| Maxima | 22 (D) cadastrar | 7 (B) _nome_ok |
Demais: _validar_dados 6 (B); _validar 4; _cpf_dv_ok, _senha_ok, CadastroService 3; cadastrar 2; restante 1-2 (A).

## Tamanho
| Metrica | Green | Refactor |
|---|---|---|
| LOC | 114 | 181 |
| LLOC | 80 | 125 |
| SLOC | 75 | 120 |
| Comentarios | 0 | 5 |
| Indice de manutenibilidade | A 61,64 | A 51,67 |
Observacao: SLOC aumentou (+45) e o MI caiu ~10 pontos (permanece classe A), por decomposicao em 21 blocos, constantes e mensagens nomeadas. Ganho claro em complexidade (max 22->7, media 5,71->2,19). Nao e criterio de saida.

## Equivalencia de comportamento (leitura do codigo, Green x Refactor)
Mesma ordem de validacao (ENTRADA, CPF, duplicado, NOME, CELULAR, EMAIL, SENHA, CONFIRMACAO); mesmos 9 status; todas as mensagens textualmente identicas; mesmos regex e limites (nome <=100, >=3 letras, inicio/fim letra; senha 8..64 + maiuscula/minuscula/digito/especial sem espaco); log warning de duplicado e info de criacao inalterados (CPF mascarado); celular normalizado so apos validacao; senha sem strip; saldo Decimal("0.00"); cadastrar_usuario so chamado no sucesso. Nenhuma mudanca observada.

## Testes por ID (todos PASSED)
CT-C01 3 | C02 4 | C03 3 | C04 7 | C05 2 | C06 1 | C07 1 | C08 1 | C09 28 | C10 5 | C11 1 | C12 42 | C13 37 | Total 135/135.

## Veredito: REFACTOR VALIDO. Nenhum incidente.
Nenhum teste/codigo alterado; sem .coverage/__pycache__/.pytest_cache no projeto.
