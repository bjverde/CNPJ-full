[← Voltar ao README](../README.md)

# Estrutura do projeto

```
cnpj_full/              Código Python
  cnpj.py               Carga dos arquivos da RF para SQLite ou CSV
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
docs/                   Documentação
  ambientes.md          Instalação e teste no Windows, Linux e Docker; .env
  cache.md              Exemplos do cache do grafo (--cache)
  carga.md              Download dos arquivos e carga
  consultas.md          Consultas, grafo e CPF/LGPD
  desenvolvimento.md    Estrutura, testes e roteiro
  cnpj-metadados.pdf    Dicionário de dados da Receita Federal
  img/                  Imagens da documentação
tests/                  Testes automáticos (pytest) e amostra sintética
.github/workflows/      GitHub Actions (testes em Ubuntu, Windows e Docker a cada PR)
Dockerfile              Imagem com Python e bibliotecas (o código entra pelo volume)
docker-compose.yml      Serviço cnpj-full com a pasta do projeto montada em /app
.env.example            Exemplo do .env (caminho do banco e outras configurações)
```

Os scripts podem ser rodados de qualquer pasta, como arquivo (`python3 cnpj_full/cnpj.py ...`) ou como módulo a partir da raiz do projeto (`python3 -m cnpj_full.cnpj ...`).

# Testes

Os testes usam uma amostra sintética no formato oficial da RF (`tests/amostra.py`) e o banco de teste (`dados_teste/cnpj_teste.db`). Cobrem a carga, a verificação das quantidades, a retomada com `--continuar`, as consultas do grafo, a escolha do banco pelo `.env` e se o banco de teste versionado está igual ao que o gerador produz. Eles rodam no GitHub Actions a cada PR, em Ubuntu e Windows (Python 3.9, 3.12 e 3.13) e no Docker. Para rodar localmente:

```bash
pip install pytest
python3 -m pytest tests
```

Se mudar o `dados_teste/gerar_banco_teste.py` (ou a carga), recrie o banco de teste com `python dados_teste/gerar_banco_teste.py` e faça commit do `dados_teste/cnpj_teste.db`; o teste `test_banco_versionado_igual_ao_gerador` falha se os dois ficarem diferentes.

Para gerar só a amostra (útil para experimentar sem baixar os arquivos da RF):

```bash
python3 tests/amostra.py amostra
python3 cnpj_full/cnpj.py amostra sqlite saida_amostra --dir
python3 cnpj_full/consulta.py cnpj 11111111000272 resultado --base saida_amostra/CNPJ_full.db --viz
```

# Roteiro

Melhorias planejadas:

* Script para baixar automaticamente os ZIPs da competência mais recente.
* Tabela própria para os CNAEs secundários (uma linha por CNAE), para buscar empresas por atividade secundária.
* Carga direta em MySQL/MariaDB e PostgreSQL, usando os modelos do cnpjrfb.
* Trocar a leitura manual de argumentos por `argparse`.
* Tabela de tempo e tamanho da carga completa, a partir de uma carga real.
