# Banco de teste

`cnpj_teste.db` é um banco SQLite pequeno (cerca de 200 KB), com o mesmo modelo da base completa, para testar consultas e o grafo sem baixar os arquivos da Receita Federal. É o banco padrão do `consulta.py` quando não se informa `--base` nem `CNPJ_DB_ARQUIVO` no `.env`.

**Todos os dados são fictícios** (nomes inventados e CPFs mascarados). Só as tabelas de domínio usam códigos reais.

```bash
python cnpj_full/consulta.py cnpj 10000001000190 resultado --viz   # grupo ALFA
python cnpj_full/consulta.py cnpj 20000001000143 resultado --viz   # grupo BRAVO
```

Para recriar o banco (por exemplo, depois de mudar o gerador):

```bash
python dados_teste/gerar_banco_teste.py
python dados_teste/gerar_banco_teste.py --zips dados_zips   # guarda também os ZIPs no formato da RF
```

## cnpjrfb.db (dados reais)

`cnpjrfb.db` (3,4 MB) é uma cópia do banco de exemplo do [cnpjrfb](https://github.com/bjverde/cnpjrfb) (`www/cnpjrfb/app/database/cnpjrfb.db`), com dados reais da RF: 10.000 empresas, 9.993 estabelecimentos e 5.628 sócios. Bom para testar volume e nomes reais. Como foi montado com as primeiras linhas de cada arquivo, as tabelas quase não se cruzam e o grafo mostra no máximo a empresa e um sócio.

```bash
python cnpj_full/consulta.py cnpj 00000007000103 resultado --base dados_teste/cnpjrfb.db --viz
```

Detalhes em [docs/ambientes.md](../docs/ambientes.md).
