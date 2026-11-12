# Projeto de Teste e Qualidade de Software

Linguagem: Python 3. Ferramentas: PyTest, pytest-cov, radon (e Locust a partir da meta M5).

## Estrutura
```
Parte4_TDD/
  login/            <- meta M2 (CT-L01 a CT-L10)  [concluída]
    red/            teste escrito primeiro + stub  -> testes FALHAM
    green/          código mínimo                  -> testes PASSAM
    refactor/       código reorganizado            -> testes PASSAM (testes inalterados)
      (em cada fase) nextbank/  tests/  evidencias/  pytest.ini
  pix/              <- meta M3 (pendente)
  extrato/          <- meta M4 (pendente)
```
Os testes são idênticos nas três fases (como pede a Aula 8: o teste não muda no Refactor).

## Como executar uma fase
```
cd login/red && python -m pytest -v          # esperado: 14 failed
cd login/green && python -m pytest -v        # esperado: 14 passed
cd login/refactor && python -m pytest -v     # esperado: 14 passed
cd login/refactor && python -m pytest --cov=nextbank --cov-branch --cov-report=term-missing
python -m radon cc nextbank/login.py -s -a   # complexidade ciclomática
```
Instalar dependências: `pip install -r requirements.txt`.
