# Banco de teste

`cnpj_teste.db` é um banco SQLite pequeno (cerca de 200 KB), com o mesmo modelo da base completa, para testar consultas e o grafo sem baixar os arquivos da Receita Federal. É o banco padrão do `consulta.py` quando não se informa `--base` nem `CNPJ_DB_ARQUIVO` no `.env`.

**Todos os dados são fictícios** (nomes inventados e CPFs mascarados). Só as tabelas de domínio usam códigos reais.

```bash
python cnpj_full/consulta.py cnpj 10000001000190 resultado --viz   # grupo ALFA: holding com controladas
python cnpj_full/consulta.py cnpj 50000001000104 resultado --viz   # grupo CHARLIE: cadeia de 3 níveis
python cnpj_full/consulta.py cnpj 60000001000168 resultado --viz   # grupo DELTA: família ligada por pessoas
python cnpj_full/consulta.py cnpj 20000001000143 resultado --viz   # grupo BRAVO: grupo menor
```

Todas as consultas de exemplo, com o tamanho do grafo em cada nível, estão em [docs/ambientes.md](../docs/ambientes.md#banco-de-teste).

Para recriar o banco (por exemplo, depois de mudar o gerador):

```bash
python dados_teste/gerar_banco_teste.py
python dados_teste/gerar_banco_teste.py --zips dados_zips   # guarda também os ZIPs no formato da RF
```
