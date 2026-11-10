# Demonstração NextBank (M8)

Script de **demonstração** do fluxo completo no terminal. **Não é um módulo de produção** e
não substitui os testes dos módulos.

Fluxo: criar conta (Cadastro) -> login com 2º fator (SMS falso imprime o código) -> crédito de
saldo inicial de R$ 1.000,00 (**parâmetro da demo**; o cadastro nasce com saldo zero) -> PIX de
R$ 250,00 -> Extrato.

## Como executar

```
python demo_nextbank.py --auto    # dados fixos de exemplo, sem input (apresentação/teste)
python demo_nextbank.py           # interativo: nome, CPF, celular, e-mail, senha, confirmação e código do SMS
```

O modo `--auto` também tenta cadastrar o mesmo CPF de novo e mostra a recusa (`CPF_JA_CADASTRADO`).
O CPF aparece mascarado e a senha nunca é impressa (no modo interativo, o que se digita aparece no terminal).

Teste de fumaça: `python -m pytest tests/test_demo.py -p no:cacheprovider`

## Código fixo no modo interativo

No modo interativo a demo imprime o aviso `Codigo de demonstracao (so nesta demo): 123456`. Se for
digitado `123456` (espaços nas pontas são ignorados), o script o troca pelo código real emitido pelo
SMS falso antes de chamar o Login. Qualquer outro valor segue a validação normal (código errado ou
de outra tentativa -> `NEGADO`). O `--auto` continua lendo o SMS falso.

Isso é **só facilidade de demonstração e NÃO existe no produto**: o Login real gera um código
aleatório de 6 dígitos, de uso único, válido por 2 minutos; o `AuthService` não foi alterado.
Observação: o Login compara o código exatamente, então espaço ou `` sobrando causa `NEGADO`;
a demo aplica `.strip()` para evitar isso.

## Como é ligado

Usa o código **refactor** de `cadastro`, `login`, `pix` e `extrato` sem alterá-lo (as pastas
`nextbank/` são somadas ao pacote via `sys.path`/`__path__`). PIX e Extrato continuam independentes
do Cadastro; a ligação é feita pelo script com o CPF normalizado, como no teste de sistema
(inclusive o registro do PIX concluído no Extrato).

## Limitações (as mesmas da integração)

Tudo em memória (nada persiste); SMS e antifraude são falsos; dados fictícios; sem sessão real;
a conta de destino do PIX é um segundo titular fictício criado pelo próprio script.
