# Dados Públicos CNPJ - Conversão para CSV/SQLite e Consultas

[![Testes](https://github.com/bjverde/CNPJ-full/actions/workflows/testes.yml/badge.svg)](https://github.com/bjverde/CNPJ-full/actions/workflows/testes.yml)

Utilitário em Python para carregar a base completa de CNPJ [disponibilizada pela Receita Federal](https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj) (RF) e transformá-la em um banco SQLite ou em arquivos CSV tratados. Processa empresas, estabelecimentos, sócios, Simples/MEI e as tabelas de domínio (CNAEs, municípios, países, naturezas jurídicas, qualificações e motivos).

Também permite consultar empresas ou sócios e gerar a rede de relacionamentos em CSV ou em grafo (GraphML, GEXF ou HTML interativo).

![Grafo](docs/img/grafo.png?raw=true "Grafo")

Projeto irmão: o [cnpjrfb](https://github.com/bjverde/cnpjrfb) é um sistema web em PHP para consultar esses dados. Os dois usam o mesmo modelo de banco ([`modelo_banco`](https://github.com/bjverde/cnpjrfb/tree/master/modelo_banco)), com scripts para MySQL/MariaDB, PostgreSQL, SQLite, SQL Server e Oracle.

## Documentação

* [Início rápido](#início-rápido) e [instalação](#instalação), logo abaixo
* [Carga](docs/carga.md): download dos arquivos da RF, conversão para SQLite/CSV, modos rápido e seguro, verificação da carga e separação por UF/município
* [Consultas e grafo](docs/consultas.md): tipos de consulta, arquivos gerados, configuração, uso da classe `RedeCNPJ` e CPF mascarado/LGPD
* [Desenvolvimento](docs/desenvolvimento.md): estrutura de pastas, testes e roteiro
* [Dicionário de dados da Receita Federal](docs/cnpj-metadados.pdf)

# Início rápido

```bash
# 1. Instalar (Python 3.9 ou superior)
git clone https://github.com/bjverde/CNPJ-full.git
cd CNPJ-full
python3 -m venv .venv
source .venv/bin/activate          # no Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Baixar todos os ZIPs de um mesmo mês para a pasta "dados"
#    (veja docs/carga.md, seção "Baixando os arquivos da Receita")

# 3. Carregar no SQLite (gera saida/CNPJ_full.db, com índices)
python3 cnpj_full/cnpj.py dados sqlite saida --dir

# 4. Consultar uma empresa e abrir o grafo no navegador
python3 cnpj_full/consulta.py cnpj 00000000000191 resultado --base saida/CNPJ_full.db --nivel 2 --viz
# abra resultado/grafo.html
```

# Instalação

Requisitos:
* **Python 3.9 ou superior.** Os testes automáticos rodam em Python 3.9, 3.12 e 3.13.
* As bibliotecas do `requirements.txt`: `pandas`, `numpy`, `numexpr`, `networkx` e `python-dotenv`.

É recomendado usar um ambiente virtual, para não misturar as bibliotecas do projeto com as do sistema:

```bash
python3 -m venv .venv
source .venv/bin/activate          # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

# Sobre o CPF dos sócios e a LGPD

A RF publica o CPF dos sócios mascarado (ex: `***123456**`), então a busca por CPF pode trazer pessoas diferentes. Os dados incluem dados pessoais: use-os de acordo com a LGPD (Lei 13.709/2018). Detalhes em [Consultas e grafo](docs/consultas.md#sobre-o-cpf-dos-sócios-e-a-lgpd).
