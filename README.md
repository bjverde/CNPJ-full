# Dados Públicos CNPJ - Conversão para CSV/SQLite e Consultas

[![Testes](https://github.com/bjverde/CNPJ-full/actions/workflows/testes.yml/badge.svg)](https://github.com/bjverde/CNPJ-full/actions/workflows/testes.yml)

Utilitário em Python para carregar a base completa de CNPJ [disponibilizada pela Receita Federal](https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj) (RF) e transformá-la em um banco SQLite ou em arquivos CSV tratados. Processa empresas, estabelecimentos, sócios, Simples/MEI e as tabelas de domínio (CNAEs, municípios, países, naturezas jurídicas, qualificações e motivos).

Também permite consultar empresas ou sócios e gerar a rede de relacionamentos em CSV ou em grafo (GraphML, GEXF ou HTML interativo).

![Grafo](docs/img/grafo.png?raw=true "Grafo")

Este repositório é uma atualização do [CNPJ-full do Fabio Serpa](https://github.com/fabioserpa/CNPJ-full) para o layout novo da RF.

## Projetos irmãos

| Projeto | Linguagem | O que faz |
| --- | --- | --- |
| [bjverde/CNPJ-full](https://github.com/bjverde/CNPJ-full) | Python | Este projeto: atualização do [CNPJ-full do Fabio Serpa](https://github.com/fabioserpa/CNPJ-full). Carga para SQLite/CSV, consultas e grafo. |
| [bjverde/cnpjrfb](https://github.com/bjverde/cnpjrfb) | PHP | Sistema web para consultar esses dados, com carga para MySQL/MariaDB, PostgreSQL, SQLite, SQL Server e Oracle. Os dois projetos usam o mesmo modelo de banco ([`modelo_banco`](https://github.com/bjverde/cnpjrfb/tree/master/modelo_banco)). |
| [aphonsoar/Receita_Federal_do_Brasil_-_Dados_Publicos_CNPJ](https://github.com/aphonsoar/Receita_Federal_do_Brasil_-_Dados_Publicos_CNPJ) | Python | Baixa os arquivos da RF e faz a carga no PostgreSQL. |

## Documentação

* [Início rápido](#início-rápido) e [instalação](#instalação), logo abaixo
* [Instalação e teste nos 4 ambientes](docs/ambientes.md): Windows, Linux, Docker no Windows e Docker no Linux; banco de teste, arquivo `.env` e problemas comuns
* [Carga](docs/carga.md): download dos arquivos da RF, conversão para SQLite/CSV, modos rápido e seguro, verificação da carga e separação por UF/município
* [Consultas e grafo](docs/consultas.md): tipos de consulta, arquivos gerados, configuração, uso da classe `RedeCNPJ` e CPF mascarado/LGPD
* [Cache do grafo](docs/cache.md): exemplos do `--cache`, como o resultado fica no disco e quando é refeito
* [Desenvolvimento](docs/desenvolvimento.md): estrutura de pastas, testes e roteiro
* [Dicionário de dados da Receita Federal](docs/cnpj-metadados.pdf)

# Início rápido

O repositório já traz um [banco de teste](dados_teste/README.md) pequeno, com dados fictícios, que é o banco padrão das consultas. Dá para ver o grafo funcionando logo depois do clone, sem baixar nada da Receita:

```bash
# 1. Instalar (Python 3.9 ou superior)
git clone https://github.com/bjverde/CNPJ-full.git
cd CNPJ-full
python3 -m venv .venv
source .venv/bin/activate          # no Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Testar com o banco de teste e abrir resultado/grafo.html no navegador
python cnpj_full/consulta.py cnpj 10000001000190 resultado --viz
```

Ou com Docker, sem instalar Python:

```bash
docker compose build
docker compose run --rm cnpj-full python cnpj_full/consulta.py cnpj 10000001000190 resultado --viz
```

Passo a passo para Windows, Linux e Docker em cada um deles: [docs/ambientes.md](docs/ambientes.md).

Com a base completa da Receita:

```bash
# 3. Baixar todos os ZIPs de um mesmo mês para a pasta "dados"
#    (veja docs/carga.md, seção "Baixando os arquivos da Receita")

# 4. Carregar no SQLite (gera saida/CNPJ_full.db, com índices)
python cnpj_full/cnpj.py dados sqlite saida --dir

# 5. Consultar na base completa (ou ponha CNPJ_DB_ARQUIVO=saida/CNPJ_full.db no .env e omita o --base)
python cnpj_full/consulta.py cnpj 00000000000191 resultado --base saida/CNPJ_full.db --nivel 2 --viz
```

# Instalação

Requisitos:
* **Python 3.9 ou superior.** Os testes automáticos rodam em Python 3.9, 3.12 e 3.13.
* As bibliotecas do `requirements.txt`: `pandas`, `numpy`, `numexpr`, `networkx` e `python-dotenv`.

É recomendado usar um ambiente virtual, para não misturar as bibliotecas do projeto com as do sistema (no Debian 12/13 e Ubuntu recentes ele é obrigatório: o `pip` do sistema dá *externally-managed-environment*):

```bash
python3 -m venv .venv
source .venv/bin/activate          # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

O banco usado pelas consultas é configurado no arquivo `.env`, na raiz do projeto (veja o [`.env.example`](.env.example) e [docs/ambientes.md](docs/ambientes.md#arquivo-env-onde-fica-o-banco)).

# Sobre o CPF dos sócios e a LGPD

A RF publica o CPF dos sócios mascarado (ex: `***123456**`), então a busca por CPF pode trazer pessoas diferentes. Os dados incluem dados pessoais: use-os de acordo com a LGPD (Lei 13.709/2018). Detalhes em [Consultas e grafo](docs/consultas.md#sobre-o-cpf-dos-sócios-e-a-lgpd).
