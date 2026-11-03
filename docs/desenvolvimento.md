[← Voltar ao README](../README.md)

# Estrutura do projeto

```
cnpj_full/              Código Python
  download.py           Download dos arquivos da RF (competência mais recente)
  carga.py              Carga dos arquivos da RF para SQLite, CSV ou SGBD
  sgbd/                 Carga em SGBDs (postgres.py; um módulo por SGBD)
  ambiente.py           Leitura do .env da raiz do projeto
  consulta.py           Consultas por linha de comando e geração do grafo
  rede_cnpj.py          Classe RedeCNPJ (navegação no banco e montagem do grafo)
  config.py             Configurações das consultas
  viz/template.html     Template da visualização interativa (d3.js)
  viz/d3.v7.min.js      d3.js v7.9.0 embutido no grafo.html (funciona sem internet)
  viz/LICENSE-d3.txt    Licença do d3.js (ISC)
  extra_csv/            Scripts para separar o estabelecimento.csv por UF ou município
dados_teste/            Banco de teste versionado (dados fictícios)
  cnpj_teste.db         Banco SQLite pequeno, padrão das consultas sem --base
  gerar_banco_teste.py  Gera os ZIPs no formato da RF e recria o cnpj_teste.db
docs/                   Documentação (índice no README) e imagens
tests/                  Testes automáticos (pytest) e amostra sintética
.github/workflows/      GitHub Actions (testes em Ubuntu, Windows e Docker a cada PR)
Dockerfile              Imagem com Python e bibliotecas (o código entra pelo volume)
docker-compose.yml      Serviço cnpj-full com a pasta do projeto montada em /app
.env.example            Exemplo do .env (caminho do banco e outras configurações)
```

Os scripts podem ser rodados de qualquer pasta, como arquivo (`python cnpj_full/carga.py ...`) ou como módulo a partir da raiz do projeto (`python -m cnpj_full.carga ...`).

# Testes

Os testes usam uma amostra sintética no formato oficial da RF (`tests/amostra.py`) e o banco de teste (`dados_teste/cnpj_teste.db`). Cobrem a carga, a verificação das quantidades, a retomada com `--continuar`, as consultas do grafo, a escolha do banco pelo `.env`, se o banco de teste versionado está igual ao que o gerador produz e o download (com um servidor local que imita o Nextcloud da RF, `tests/test_download.py`). Eles rodam no GitHub Actions a cada PR, em Ubuntu e Windows (Python 3.13, a versão mínima) e no Docker. Para rodar localmente:

```bash
pip install pytest
python -m pytest tests
```

Se mudar o `dados_teste/gerar_banco_teste.py` (ou a carga), recrie o banco de teste com `python dados_teste/gerar_banco_teste.py` e faça commit do `dados_teste/cnpj_teste.db`; o teste `test_banco_versionado_igual_ao_gerador` falha se os dois ficarem diferentes.

Os testes do PostgreSQL (`tests/test_postgres.py`) só rodam se houver um PostgreSQL de teste, informado em `CNPJ_TESTE_PG_HOST` (e, se preciso, `CNPJ_TESTE_PG_PORTA`, `CNPJ_TESTE_PG_USUARIO`, `CNPJ_TESTE_PG_SENHA`, `CNPJ_TESTE_PG_NOME`, padrão `cnpj_teste`). Sem isso são pulados. No GitHub Actions eles rodam com um container `postgres:16`. Localmente, com Docker:

```bash
docker run -d --name pg-teste -e POSTGRES_PASSWORD=teste -e POSTGRES_DB=cnpj_teste -p 5432:5432 postgres:16
CNPJ_TESTE_PG_HOST=localhost CNPJ_TESTE_PG_SENHA=teste python -m pytest tests
```

Para gerar só a amostra (útil para experimentar sem baixar os arquivos da RF):

```bash
python tests/amostra.py amostra
python cnpj_full/carga.py amostra sqlite saida_amostra --dir
python cnpj_full/consulta.py cnpj 11111111000272 resultado --base saida_amostra/CNPJ_full.db --viz
```

# Roteiro

Melhorias planejadas:

* Tabela própria para os CNAEs secundários (uma linha por CNAE), para buscar empresas por atividade secundária.
* Carga direta em MySQL/MariaDB, SQL Server e Oracle (PostgreSQL já existe), usando os modelos do cnpjrfb.
* Consultas e grafo lendo do PostgreSQL.
* Trocar a leitura manual de argumentos por `argparse`.
* Tabela de tempo e tamanho da carga completa, a partir de uma carga real.
