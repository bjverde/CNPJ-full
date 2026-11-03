# Modelos de banco de dados

Scripts de criação do banco para os dados abertos do CNPJ da Receita Federal, conforme o
"Novo Layout para os DADOS ABERTOS do CNPJ" ([`docs/cnpj-metadados.pdf`](../docs/cnpj-metadados.pdf)).
É o mesmo modelo usado pelo [cnpjrfb](https://github.com/bjverde/cnpjrfb) (sistema web de consulta)
e pela carga do CNPJ-full.

Todos os scripts são **gerados** por [`cnpj_full/modelo.py`](../cnpj_full/modelo.py) a partir de uma
única definição do modelo, por isso as tabelas, colunas, tipos, chaves e índices são os mesmos em
todos os bancos. Não edite os `.sql` à mão: altere o gerador e rode de novo.

```bash
python3 cnpj_full/modelo.py                       # regrava todos os scripts desta pasta
python3 cnpj_full/modelo.py --sgbd pgsql          # mostra o script do PostgreSQL na tela
python3 cnpj_full/modelo.py --sgbd pgsql --fk     # mostra as chaves estrangeiras
python3 cnpj_full/modelo.py --saida /outra/pasta  # grava em outra pasta
```

O `--sgbd` usa os mesmos nomes do PDO (`DB_DRIVE`): `mysql`, `pgsql`, `sqlite`, `sqlsrv` e `oci`.

| Pasta | Script de criação | Chaves estrangeiras | Testado |
|---|---|---|---|
| `mysql/` | `modelo_mysql.sql` | `modelo_mysql_fk.sql` | MariaDB 10.11 |
| `postgresql/` | `modelo_postgres.sql` | `modelo_postgres_fk.sql` | PostgreSQL 16 |
| `sqlite/` | `modelo_sqlite.sql` | declaradas na própria tabela | SQLite 3 |
| `sqlserver/` | `modelo_sqlserver.sql` | `modelo_sqlserver_fk.sql` | só sintaxe (SQL Server 2016+) |
| `oracle/` | `modelo_oracle.sql` | `modelo_oracle_fk.sql` | só sintaxe (Oracle 12c+) |

## Ordem de uso

1. Rode o script de criação.
2. Faça a carga dos dados. Hoje a carga do CNPJ-full ([docs/carga.md](../docs/carga.md)) grava em
   SQLite ou CSV; a carga direta nos outros bancos está no roteiro
   ([docs/desenvolvimento.md](../docs/desenvolvimento.md)). Até lá, o cnpjrfb tem a carga em PHP
   (`www/cargabd`).
3. Opcional: rode o script `_fk.sql` para criar as chaves estrangeiras. Elas ficam separadas porque
   deixam a carga muito mais lenta e porque a carga grava `estabelecimento` e `socios` antes de `empresa`.

## Modelo

| Tabela | Chave primária | Observação |
|---|---|---|
| `empresa` | `cnpj_basico` | Uma linha por CNPJ básico (8 dígitos) |
| `estabelecimento` | `cnpj_basico`, `cnpj_ordem`, `cnpj_dv` | Matriz e filiais; FK para `empresa` |
| `simples` | `cnpj_basico` | FK para `empresa` |
| `socios` | `id` (gerado pelo banco) | Vários sócios por empresa; FK para `empresa` |
| `cnae`, `moti`, `munic`, `natju`, `pais`, `quals` | `codigo` | Tabelas de domínio |

Pontos de atenção na carga:

* `capital_social` é numérico (`DECIMAL(18,2)`). O arquivo usa vírgula decimal, que precisa ser trocada por ponto.
* Datas vêm como `AAAAMMDD`. Valores `0` ou `00000000` devem ser gravados como NULL.
* `situacao_cadastral` e `porte_empresa` são códigos de dois dígitos (`02`, `08`, `01`, `05`...).
