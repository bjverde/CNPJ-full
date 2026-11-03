[← Voltar ao README](../README.md)

# Estrutura do projeto

```
cnpj_full/              Código Python
  download.py           Download dos arquivos da RF (competência mais recente)
  cnpj.py               Carga dos arquivos da RF para SQLite, CSV ou SGBD
  sgbd/                 Carga em SGBDs (postgres.py; um módulo por SGBD)
  ambiente.py           Leitura do .env da raiz do projeto
  consulta.py           Consultas por linha de comando e geração do grafo
  rede_cnpj.py          Classe RedeCNPJ (navegação no banco e montagem do grafo)
  config.py             Configurações das consultas
  viz/template.html     Template da visualização interativa (d3.js)
  viz/d3.v7.min.js      d3.js v7.9.0 embutido no grafo.html (funciona sem internet)
  viz/LICENSE-d3.txt    Licença do d3.js (ISC)
  extra_csv/            Scripts para separar o estabelecimento.csv por UF ou município
docs/                   Documentação
  cache.md              Exemplos do cache do grafo (--cache)
  download.md           Download dos arquivos da RF
  carga.md              Arquivos da RF e carga (SQLite/CSV)
  postgresql.md         Carga no PostgreSQL
  consultas.md          Consultas, grafo e CPF/LGPD
  desenvolvimento.md    Estrutura, testes e roteiro
  cnpj-metadados.pdf    Dicionário de dados da Receita Federal
  img/                  Imagens da documentação
tests/                  Testes automáticos (pytest) e amostra sintética
.github/workflows/      GitHub Actions (roda os testes a cada PR)
```

Os scripts podem ser rodados de qualquer pasta, como arquivo (`python3 cnpj_full/cnpj.py ...`) ou como módulo a partir da raiz do projeto (`python3 -m cnpj_full.cnpj ...`).

# Testes

Os testes usam uma amostra sintética no formato oficial da RF (`tests/amostra.py`) e cobrem a carga, a verificação das quantidades, a retomada com `--continuar` e as consultas do grafo. O download é testado com um servidor local que imita o Nextcloud da RF (`tests/test_download.py`). Eles rodam no GitHub Actions a cada PR. Para rodar localmente:

```bash
pip install pytest
python3 -m pytest tests
```

Os testes do PostgreSQL (`tests/test_postgres.py`) só rodam se houver um PostgreSQL de teste, informado em `CNPJ_TESTE_PG_HOST` (e, se preciso, `CNPJ_TESTE_PG_PORTA`, `CNPJ_TESTE_PG_USUARIO`, `CNPJ_TESTE_PG_SENHA`, `CNPJ_TESTE_PG_NOME`, padrão `cnpj_teste`). Sem isso são pulados. No GitHub Actions eles rodam com um container `postgres:16`. Localmente, com Docker:

```bash
docker run -d --name pg-teste -e POSTGRES_PASSWORD=teste -e POSTGRES_DB=cnpj_teste -p 5432:5432 postgres:16
CNPJ_TESTE_PG_HOST=localhost CNPJ_TESTE_PG_SENHA=teste python3 -m pytest tests
```

Para gerar só a amostra (útil para experimentar sem baixar os arquivos da RF):

```bash
python3 tests/amostra.py amostra
python3 cnpj_full/cnpj.py amostra sqlite saida_amostra --dir
python3 cnpj_full/consulta.py cnpj 11111111000272 resultado --base saida_amostra/CNPJ_full.db --viz
```

# Roteiro

Melhorias planejadas:

* Tabela própria para os CNAEs secundários (uma linha por CNAE), para buscar empresas por atividade secundária.
* Carga direta em MySQL/MariaDB, SQL Server e Oracle (PostgreSQL já existe), usando os modelos do cnpjrfb.
* Consultas e grafo lendo do PostgreSQL.
* Trocar a leitura manual de argumentos por `argparse`.
* Tabela de tempo e tamanho da carga completa, a partir de uma carga real.
