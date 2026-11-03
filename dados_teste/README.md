[← Voltar ao README](../README.md) · [Guia de uso](../docs/ambientes.md#2-teste-do-ambiente)

# Banco de teste

`cnpj_teste.db` é um banco SQLite pequeno (cerca de 200 KB) com o mesmo modelo da base completa (o mesmo do [cnpjrfb](https://github.com/bjverde/cnpjrfb)). Ele é versionado no git, então funciona logo depois do `git clone`, e é o banco padrão do `consulta.py` quando não se informa `--base` nem `CNPJ_DB_ARQUIVO` no `.env` ([qual banco a consulta usa](../docs/ambientes.md#qual-banco-a-consulta-usa)).

**Todos os dados são fictícios**: nomes de empresas e pessoas são inventados e os CPFs seguem o formato mascarado da RF (`***123456**`). Só as tabelas de domínio (CNAEs, municípios, naturezas jurídicas, qualificações, países e motivos) usam códigos reais. Assim o banco pode ficar no repositório sem problema de LGPD.

Conteúdo: 202 empresas, 236 estabelecimentos, 311 sócios e 96 optantes do Simples. Há quatro grupos econômicos montados para o grafo ter ligações até o nível 3, além de cerca de 180 empresas avulsas cujos sócios aparecem em várias empresas.

## Consultas de exemplo

Exemplo: `python cnpj_full/consulta.py cnpj 50000001000104 resultado --nivel 3 --viz`. O nível padrão é 3. A coluna "nós" é o número de empresas e pessoas no grafo com `--nivel 1`, `2` e `3`:

Consulta | O que mostra | Nós (nível 1 / 2 / 3)
-------- | ------------ | ---------------------
`cnpj 10000001000190` | **ALFA HOLDING**: 4 controladas ativas e 1 baixada, controlada de controlada, filiais, sócio estrangeiro, administradora comum a várias empresas | 9 / 11 / 13
`cnpj 50000001000104` | **CHARLIE PARTICIPACOES**: cadeia holding > indústria > distribuidora > logística, com a logística no nível 3 | 4 / 7 / 9
`cnpj 50000004000148` | **CHARLIE LOGISTICA**: a mesma cadeia vista de baixo para cima, até a holding | 3 / 4 / 7
`cnpj 60000001000168` | **PADARIA DELTA**: empresas de uma família ligadas só por pessoas, sem holding; uma sócia também é sócia do restaurante do presidente do grupo ALFA | 4 / 6 / 8
`cnpj 20000001000143` | **BRAVO SERVICOS**: grupo menor, controlada de controlada e sócio PJ que não está na base | 4 / 5 / 6
`cnpj 40000006000183` | **CONTABILIDADE ESTRELA LUAR**: empresa avulsa; os sócios estão em muitas empresas, rede grande | 4 / 22 / 32
`nome_socio "ANA TEIXEIRA HENRIQUES"` | Busca por pessoa: filho da família DELTA, sócio de duas empresas | 3 / 5 / 8

Os testes automáticos (`tests/test_banco_teste.py`) conferem esses números.

## Recriando o banco

O banco é gerado pelo [`gerar_banco_teste.py`](gerar_banco_teste.py), que cria ZIPs no formato da RF e carrega com o próprio `cnpj_full/carga.py`. A geração é determinística: rodar de novo gera os mesmos dados. Os testes automáticos conferem que o `.db` versionado está igual ao que o script gera.

```bash
python dados_teste/gerar_banco_teste.py                       # recria dados_teste/cnpj_teste.db
python dados_teste/gerar_banco_teste.py --zips dados_zips     # guarda também os ZIPs (para testar a carga)
```
