# Teste de sistema (meta M6) - Login -> PIX -> Extrato

Fluxo ponta a ponta em PyTest (ST-01 a ST-05), em `tests/test_sistema.py`.

- `nextbank/` contem copia identica de `login/refactor`, `pix/refactor` e `extrato/refactor`
  (login.py, pix.py, extrato.py). Copia, e nao sys.path, porque os tres pacotes se chamam `nextbank`.
- PIX e Extrato sao independentes (decisao aprovada): o teste registra no Extrato os
  lancamentos de PIX concluido; PIX retido em analise nao gera lancamento.
- SMS, antifraude e relogio sao fakes.

Executar:
```
cd sistema
PYTHONDONTWRITEBYTECODE=1 python -m pytest -v -p no:cacheprovider
```
