# Resumo TDD — módulo Login (meta M2)

Requisitos cobertos: RF-01, RF-02, RS-01, RS-02, RS-06, RS-07 (Plano de Testes, seção 4.3.1).
Casos: CT-L01 a CT-L10 = 14 testes PyTest (CT-L08 tem 4 regras da tabela de decisão; CT-L09 tem 2 payloads).

| Fase | Resultado | Evidência |
|---|---|---|
| Red | 14 falharam (NotImplementedError) | red/evidencias/pytest_red.txt |
| Green | 14 passaram | green/evidencias/pytest_green.txt |
| Refactor | 14 passaram, testes sem alteração | refactor/evidencias/pytest_refactor.txt |

## Métricas (alimentam o Relatório de Métricas, Parte 3)
| Métrica | Green | Refactor |
|---|---|---|
| Cobertura de instruções + ramos (pytest-cov) | 97% | 99% |
| Complexidade ciclomática média (radon) | 2,88 (A) | 1,91 (A) |
| Maior complexidade em um método | 7 (B) | 3 (A) |
| Linhas de código (SLOC) | 75 | 118 |

Observações:
- Única linha sem cobertura no Refactor: CPF com formato válido, mas não cadastrado (retorna "credenciais inválidas"). Sugestão: novo teste CT-L11 em ciclo futuro.
- O Refactor trocou SHA-256 simples por PBKDF2 com sal e comparação em tempo constante (RS-06), separou ServicoToken, validação de CPF e mensagens; o comportamento externo não mudou.
- Os pontos de decisão do Plano: bloqueio na 5ª tentativa e token válido até 2 min foram testados nos limites (4ª/5ª tentativa; 1 min 59 s e 2 min 01 s).
