# CNPJ-full: grafo de relacionamentos entre empresas e sócios

[![Testes](https://github.com/bjverde/CNPJ-full/actions/workflows/testes.yml/badge.svg)](https://github.com/bjverde/CNPJ-full/actions/workflows/testes.yml)

Utilitário em Python que mostra **quem é sócio de quem** no Brasil, a partir dos dados públicos do CNPJ [publicados pela Receita Federal](https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj) (RF).

Você informa um CNPJ, o nome de um sócio ou um CPF e ele monta a rede de empresas e pessoas ligadas até o nível que você escolher: holdings e controladas, matriz e filiais, sócios em comum. O resultado sai como um grafo interativo para abrir no navegador (funciona sem internet), em CSV ou nos formatos GraphML e GEXF (Gephi).

![Grafo](docs/img/grafo.png?raw=true "Grafo")

Para isso o projeto também faz o trabalho pesado com os arquivos da RF: baixa a competência mais recente direto do servidor da Receita e carrega empresas, estabelecimentos, sócios, Simples/MEI e as tabelas de domínio em um banco SQLite ou PostgreSQL (ou em CSVs tratados).

## Experimente sem baixar nada

O repositório já traz um [banco de teste](docs/ambientes.md#banco-de-teste) pequeno, com dados fictícios, que é o banco padrão das consultas. Dá para ver o grafo funcionando logo depois do clone, sem baixar nada da Receita:

```bash
python cnpj_full/consulta.py cnpj 10000001000190 resultado --viz   # depois abra resultado/grafo.html
```

Antes é preciso instalar o Python 3.13 (ou usar Docker) e as bibliotecas: o [guia de uso](docs/ambientes.md) mostra como, no Windows, no Linux e no Docker.

## Documentação

O [**guia de uso**](docs/ambientes.md) segue o caminho completo, da instalação à consulta na base real:

1. [Instalação](docs/ambientes.md#1-instalação): Windows, Linux, Docker no Windows e Docker no Linux
2. [Teste do ambiente](docs/ambientes.md#2-teste-do-ambiente) com o [banco de teste](docs/ambientes.md#banco-de-teste): conteúdo, CNPJs de exemplo e como recriar
3. [Download dos arquivos da RF](docs/ambientes.md#3-download-dos-arquivos-da-receita)
4. [Carga no banco](docs/ambientes.md#4-carga-no-banco)
5. [Consulta com os dados reais](docs/ambientes.md#5-consulta-com-os-dados-reais)

Referência de cada parte:

* [Download](docs/download.md): argumentos do `download.py`, como a competência é escolhida, retomada e proxy
* [Carga](docs/carga.md): arquivos da RF, saída SQLite/CSV, modos rápido e seguro, verificação da carga e separação por UF/município
* [Carga no PostgreSQL](docs/postgresql.md): conexão no `.env`, modelo e como a carga funciona
* [Consultas e grafo](docs/consultas.md): tipos de consulta, arquivos gerados, configuração, classe `RedeCNPJ` e CPF mascarado/LGPD
* [Cache do grafo](docs/cache.md): exemplos do `--cache`
* [Desenvolvimento](docs/desenvolvimento.md): estrutura de pastas, testes e roteiro
* [Dicionário de dados da Receita Federal](docs/cnpj-metadados.pdf)

## Sobre o CPF dos sócios e a LGPD

A RF publica o CPF dos sócios mascarado (ex: `***123456**`), então a busca por CPF pode trazer pessoas diferentes. Os dados incluem dados pessoais: use-os de acordo com a LGPD (Lei 13.709/2018). Detalhes em [Consultas e grafo](docs/consultas.md#sobre-o-cpf-dos-sócios-e-a-lgpd).

## Origem e projetos irmãos

Este repositório é uma atualização do [CNPJ-full do Fabio Serpa](https://github.com/fabioserpa/CNPJ-full) para o layout novo da RF.

| Projeto | Linguagem | O que faz |
| --- | --- | --- |
| [bjverde/cnpjrfb](https://github.com/bjverde/cnpjrfb) | PHP | Sistema web para consultar esses dados. Usa o mesmo modelo de banco ([`modelo_banco`](https://github.com/bjverde/cnpjrfb/tree/master/modelo_banco)). |
| [aphonsoar/Receita_Federal_do_Brasil_-_Dados_Publicos_CNPJ](https://github.com/aphonsoar/Receita_Federal_do_Brasil_-_Dados_Publicos_CNPJ) | Python | Baixa os arquivos da RF e faz a carga no PostgreSQL. |
