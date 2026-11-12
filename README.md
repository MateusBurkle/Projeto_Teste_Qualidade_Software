# Parte 4 — Casos de teste automatizados em TDD (NextBank)

Linguagem: Python 3. Ferramentas: PyTest, pytest-cov, radon e Locust (ver a seção "Ferramentas utilizadas").

## Estrutura
```
Parte4_TDD/
  login/            <- meta M2 (CT-L01 a CT-L10)  [concluída, 14 testes]
    red/            teste escrito primeiro + stub  -> testes FALHAM
    green/          código mínimo                  -> testes PASSAM
    refactor/       código reorganizado            -> testes PASSAM (testes inalterados)
      (em cada fase) nextbank/  tests/  evidencias/  pytest.ini
  pix/              <- meta M3 (CT-P)             [concluída, 20 testes, mesma estrutura red/green/refactor]
  extrato/          <- meta M4 (CT-E)             [concluída, 7 testes, mesma estrutura red/green/refactor]
  cadastro/         <- meta M8 (CT-C)             [concluída, 135 testes, mesma estrutura red/green/refactor]
  locust/           <- meta M5: carga, pico, estresse e resistência (CT-P12, P13, P15, P16, E05, E06, E09)
  sistema/          <- meta M6: teste de sistema Login -> PIX -> Extrato (ST-01 a ST-05)
  seguranca/        <- testes de segurança (CT-S01 a CT-S24) e incidentes INC-S01 a INC-S10
  demo/             <- demonstração do fluxo completo no terminal (não é módulo de produção)
  teste_geral_final/<- evidências do teste geral final (cobertura, regressão CT-R01, integração, radon)
```
Os testes são idênticos nas três fases (como pede a Aula 8: o teste não muda no Refactor).
Há também `teste_geral/` dentro de `pix/`, `extrato/` e `cadastro/` com as evidências do teste geral de cada módulo.

## Como executar

Instalar dependências: `pip install -r requirements.txt`.

Cada pasta tem o seu `pytest.ini`, então rode o comando dentro da pasta indicada.

```
# TDD de um módulo (exemplo: login; vale para pix, extrato e cadastro)
cd login/red && python -m pytest -v          # esperado: 14 failed
cd login/green && python -m pytest -v        # esperado: 14 passed
cd login/refactor && python -m pytest -v     # esperado: 14 passed
cd login/refactor && python -m pytest --cov=nextbank --cov-branch --cov-report=term-missing
python -m radon cc nextbank/login.py -s -a   # complexidade ciclomática (rodar em refactor/)

# Resultados esperados na fase Red: pix 20 failed, extrato 7 failed, cadastro 135 failed.
# Green e Refactor: todos passam.

# Teste de sistema (M6)
cd sistema && python -m pytest -v -p no:cacheprovider

# Segurança
cd seguranca && python -m pytest -v -p no:cacheprovider                          # sistema (19 testes)
cd seguranca && python -m pytest -c pytest_cadastro.ini -v -p no:cacheprovider   # cadastro (109 testes)

# Demonstração
cd demo && python demo_nextbank.py --auto
cd demo && python -m pytest tests/test_demo.py -p no:cacheprovider

# Locust (M5, teste rápido; ver locust/README.md para os cenários completos)
cd locust && NB_ESCALA_TEMPO=0.05 locust -f locustfile.py,cenario_carga.py PixUser --headless
cd locust && locust -f locustfile.py ExtratoUser -u 100 -r 20 --headless
```
No PowerShell, defina a variável antes: `$env:NB_ESCALA_TEMPO="0.05"`.

## Ferramentas utilizadas

### Ferramentas externas (instaladas com `pip`)

| Ferramenta | Funcionalidade | Onde foi aplicado |
|---|---|---|
| **Python 3** | Linguagem de todo o código (`nextbank/`), dos testes e dos scripts. | Todas as pastas: `login`, `pix`, `extrato`, `cadastro`, `sistema`, `seguranca`, `demo`, `locust`. |
| **PyTest** | Framework de testes unitários: descobre e executa os testes e mostra passou/falhou. Usado no ciclo TDD (Red falha, Green e Refactor passam). | Testes de `login/`, `pix/`, `extrato/` e `cadastro/` (`red`, `green`, `refactor`); teste de sistema em `sistema/`; segurança em `seguranca/`; fumaça em `demo/tests`. |
| **pytest-cov** (coverage.py) | Mede a cobertura de código, com cobertura de ramos (`--cov-branch`) e linhas não cobertas (`term-missing`). | Arquivos `cobertura_*.txt` em `evidencias/` de cada fase `green` e `refactor`; cobertura consolidada em `teste_geral_final/` (41 testes, 99%); cobertura do cadastro em `cadastro/teste_geral_final_m8/`. |
| **radon** | Mede métricas do código: complexidade ciclomática (`radon cc`), tamanho LOC/LLOC/SLOC (`radon raw`) e índice de manutenibilidade (`radon mi`). Serve para comparar Green e Refactor. | Arquivos `complexidade_*.txt` e `tamanho_*.txt` em `evidencias/`; `teste_geral_final/05_radon_cc.txt`, `06_radon_raw_mi.txt` e `07_radon_green_comparacao.txt`. |
| **Locust** | Testes de desempenho: carga, pico, estresse e resistência. Cada usuário virtual chama `PixService` e `ExtratoService` direto (o sistema não tem servidor HTTP) e o Locust calcula média, P95 e taxa de falhas. | `locust/` (meta M5): CT-P12 (carga), CT-P13 (pico), CT-P15 (estresse), CT-P16 (resistência 30 min) e CT-E05, CT-E06, CT-E09 (extrato). Resultados em `locust/evidencias/` (CSV e HTML). |
| **gevent** (instalado com o Locust) | Concorrência cooperativa usada pelo Locust; no projeto serve para encerrar o teste e amostrar a memória durante a resistência. | `locust/locustfile.py`. |

### Recursos do PyTest usados

| Recurso | Funcionalidade | Onde foi aplicado |
|---|---|---|
| `@pytest.mark.parametrize` | Roda o mesmo teste com vários dados de entrada, sem repetir código (cerca de 150 usos). | Validação de CPF, senha, e-mail e celular; payloads maliciosos (SQL/XSS/Unicode) em `seguranca/`; valores inválidos no PIX. |
| `@pytest.fixture` | Monta o cenário de cada teste (serviços, relógio, contas) de forma reutilizável. | Todas as suítes (cerca de 44 fixtures). |
| `caplog` | Captura os logs gerados pelo código para verificar o que foi registrado. | Testes de CPF mascarado e de senha fora dos logs (CT-S06, CT-S09, CT-S10, RS-05 e RS-06). |
| `capsys` | Captura o que o código imprime no terminal. | `demo/tests/test_demo.py` (a senha nunca é impressa e o CPF aparece mascarado). |
| `pytest.ini` | Define `pythonpath` e `testpaths` de cada fase para o PyTest encontrar `nextbank/` e `tests/`. | Uma por fase (`red`, `green`, `refactor`), em `sistema/`, `seguranca/` (inclui `pytest_cadastro.ini`) e `demo/`. |

### Técnicas e bibliotecas padrão do Python

| Técnica / biblioteca | Funcionalidade | Onde foi aplicado |
|---|---|---|
| **Dublês de teste (fakes)** `RelogioFalso`, `SmsFalso`, `AntifraudeFalso` | Substituem relógio, SMS e antifraude para o teste ser rápido, repetível e sem serviço externo. Feitos à mão, sem biblioteca de mock. | Testes de `login/`, `pix/`, `extrato/`, `cadastro/`, `sistema/`, `seguranca/` e na `demo/`. |
| `decimal.Decimal` | Cálculo de dinheiro sem erro de arredondamento do `float`. | `pix.py`, `extrato.py` e `cadastro.py` (saldo, valores e limites). |
| `dataclasses` | Declara de forma curta as estruturas de dados (resultado de login, token, lançamento, registro de auditoria). | `login.py`, `pix.py`, `extrato.py`. |
| `hashlib`, `hmac`, `secrets` | Hash da senha com sal, comparação em tempo constante e código aleatório de 6 dígitos. | `login.py` (idêntico em `login`, `pix`, `extrato`, `cadastro`); testado em `seguranca/`. |
| `re` e `unicodedata` | Validação de CPF, e-mail, celular e senha com regex, e testes com dígitos Unicode. | `login.py`, `cadastro.py` e `seguranca/tests_cadastro/`. |
| `logging` | Registra eventos e auditoria, com CPF mascarado. | `login.py`, `pix.py`, `extrato.py`, `cadastro.py`. |
| `tracemalloc` | Amostra o consumo de memória ao longo do tempo. | `locust/locustfile.py` (CT-P16, resistência). |
| `argparse` | Define a opção `--auto` do script de demonstração. | `demo/demo_nextbank.py`. |
| `sha256` / `cmp` | Prova que o `login.py` é idêntico nas cópias de cada módulo. | `cadastro/teste_geral_final_m8/03_sha256_login.txt` e `seguranca/evidencias/cadastro/`. |

### Práticas de qualidade aplicadas com essas ferramentas

| Prática | Funcionalidade | Onde foi aplicado |
|---|---|---|
| **TDD (Red, Green, Refactor)** | Escrever o teste primeiro, depois o código mínimo, depois reorganizar sem mudar os testes. | `login/`, `pix/`, `extrato/`, `cadastro/` (pastas `red/`, `green/`, `refactor/`). |
| **Teste de regressão (CT-R01)** | Confere que o que já funcionava continua funcionando (CT-L01, L04, L06, P01, P06, P08). | `pix/teste_geral/`, `extrato/teste_geral/`, `teste_geral_final/03_regressao_CT_R01.txt`. |
| **Teste de integração** | Verifica que os módulos funcionam juntos (Login+PIX, Login+Extrato, Login+Cadastro). | `teste_geral_final/04_integracao_CT_P17_CT_E10.txt`, `cadastro/teste_geral_final_m8/04_integracao_login_cadastro.txt`. |
| **Teste de sistema (ST-01 a ST-05)** | Fluxo ponta a ponta Login, PIX e Extrato. | `sistema/tests/test_sistema.py` (meta M6). |
| **Teste de segurança (CT-S01 a CT-S24)** | Entradas maliciosas, força bruta, reuso de token, acesso a conta alheia e vazamento de dados. Incidentes INC-S01 a INC-S10, todos corrigidos. | `seguranca/` (19 testes do sistema, 109 do cadastro e 144 exploratórios, 272 no total). |
| **Teste de desempenho** | Carga, pico, estresse e resistência com Locust. | `locust/` (meta M5). |
| **Demonstração (teste de fumaça)** | Roda o fluxo completo no terminal e confere que não quebra. | `demo/` (`python demo_nextbank.py --auto`). |

> Observação: todos os testes são de lógica em memória, com fakes e dados fictícios. Não há servidor HTTP, banco de dados nem teste de invasão (pentest).
