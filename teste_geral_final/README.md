# Parte 4 — Casos de teste automatizados em TDD (NextBank)

Linguagem: Python 3. Ferramentas: PyTest, pytest-cov, radon (e Locust a partir da meta M5).

## Estrutura
```
Parte4_TDD/
  login/           
    red/            teste escrito primeiro + stub  -> testes FALHAM
    green/          código mínimo                  -> testes PASSAM
    refactor/       código reorganizado            -> testes PASSAM 
      (em cada fase) nextbank/  tests/  evidencias/  pytest.ini
  pix/              
  extrato/          
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

## Como executar a Demonstração
```
python demo_nextbank.py --auto    # automático
python demo_nextbank.py           # manual (interativo)

--auto
- Usa dados fixos de exemplo e não pede nada.
- Percorre o fluxo cadastro, login com 2º fator, crédito de R$ 1.000,00, PIX de R$ 250,00 e extrato.
- Tenta cadastrar o mesmo CPF de novo e mostra a recusa CPF_JA_CADASTRADO.

Manual (interativo)
- Pede nome, CPF, celular, e-mail, senha, confirmação da senha e o código do SMS.
- A demo imprime Codigo de demonstracao (so nesta demo): 123456. Digite 123456 quando ela pedir o código.
- A senha digitada aparece na tela neste modo.

Teste de fumaça da demo:
python -m pytest tests/test_demo.py -p no:cacheprovider -> Tudo fica em memória e nada persiste entre execuções.
```
