# Parte 4 — Casos de teste automatizados em TDD (NextBank)

Linguagem: Python 3. 

## Ferramentas utilizadas

| Ferramenta | O que faz | Onde aparece no projeto |
|---|---|---|
| **PyTest** | Framework de testes para Python. Descobre e executa os testes automaticamente e mostra quais passaram ou falharam. | Todas as fases do TDD (Red, Green, Refactor) |
| **pytest-cov** | Plugin do PyTest que mede a cobertura de código, ou seja, quanto do código foi executado pelos testes (linhas e ramificações). | Relatório de cobertura na fase Refactor |
| **radon** | Analisa o código sem executá-lo e calcula métricas, como a complexidade ciclomática, que indica quantos caminhos de decisão uma função tem. Quanto maior, mais difícil de testar e manter. | Análise de `nextbank/login.py` |
| **Locust** | Ferramenta de teste de carga e desempenho. Simula muitos usuários acessando o sistema ao mesmo tempo para medir tempo de resposta e pontos de falha. | A partir da meta M5 |

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
