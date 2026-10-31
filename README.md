# Dados Públicos CNPJ - Conversão para CSV/SQLite e Consultas

[![Testes](https://github.com/bjverde/CNPJ-full/actions/workflows/testes.yml/badge.svg)](https://github.com/bjverde/CNPJ-full/actions/workflows/testes.yml)

Utilitário em Python para carregar a base completa de CNPJ [disponibilizada pela Receita Federal](https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj) (RF) e transformá-la em um banco SQLite ou em arquivos CSV tratados. Processa empresas, estabelecimentos, sócios, Simples/MEI e as tabelas de domínio (CNAEs, municípios, países, naturezas jurídicas, qualificações e motivos).

Também permite consultar empresas ou sócios e gerar a rede de relacionamentos em CSV ou em grafo (GraphML, GEXF ou HTML interativo).

![Grafo](img/grafo.png?raw=true "Grafo")

Projeto irmão: o [cnpjrfb](https://github.com/bjverde/cnpjrfb) é um sistema web em PHP para consultar esses dados. Os dois usam o mesmo modelo de banco ([`modelo_banco`](https://github.com/bjverde/cnpjrfb/tree/master/modelo_banco)), com scripts para MySQL/MariaDB, PostgreSQL, SQLite, SQL Server e Oracle.

## Sumário

* [Início rápido](#início-rápido)
* [Instalação](#instalação)
* [Baixando os arquivos da Receita](#baixando-os-arquivos-da-receita)
* [Carga: conversão para SQLite ou CSV](#carga-conversão-para-sqlite-ou-csv)
* [Consultas e grafo de relacionamentos](#consultas-e-grafo-de-relacionamentos)
* [Separando o CSV por UF ou município](#separando-o-csv-por-uf-ou-município)
* [Sobre o CPF dos sócios e a LGPD](#sobre-o-cpf-dos-sócios-e-a-lgpd)
* [Testes](#testes)
* [Roteiro](#roteiro)

# Início rápido

```bash
# 1. Instalar (Python 3.9 ou superior)
git clone https://github.com/bjverde/CNPJ-full.git
cd CNPJ-full
python3 -m venv .venv
source .venv/bin/activate          # no Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Baixar todos os ZIPs de um mesmo mês para a pasta "dados" (veja abaixo)

# 3. Carregar no SQLite (gera saida/CNPJ_full.db, com índices)
python3 cnpj.py dados sqlite saida --dir

# 4. Consultar uma empresa e abrir o grafo no navegador
python3 consulta.py cnpj 00000000000191 resultado --base saida/CNPJ_full.db --nivel 2 --viz
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

# Baixando os arquivos da Receita

A RF publica os dados todo mês em `https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/`, com uma pasta por competência (ex: `2026-10/`). O acesso também está no [portal dados.gov.br](https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj).

Baixe **todos os ZIPs da mesma competência** para uma pasta dedicada, sem renomear e sem descompactar:

Arquivos | Tabela gerada | Conteúdo
-------- | ------------- | --------
`Empresas0.zip` a `Empresas9.zip` | `empresa` | Dados da empresa (CNPJ básico, razão social, natureza jurídica, capital social, porte...)
`Estabelecimentos0.zip` a `Estabelecimentos9.zip` | `estabelecimento` | Matriz e filiais (CNPJ completo = `cnpj_basico` + `cnpj_ordem` + `cnpj_dv`), endereço, situação, CNAEs
`Socios0.zip` a `Socios9.zip` | `socios` | Quadro societário, vinculado ao CNPJ básico
`Simples.zip` | `simples` | Opção pelo Simples e pelo MEI
`Cnaes.zip`, `Motivos.zip`, `Municipios.zip`, `Naturezas.zip`, `Paises.zip`, `Qualificacoes.zip` | `cnae`, `moti`, `munic`, `natju`, `pais`, `quals` | Tabelas de domínio (`codigo`, `descricao`)

Cada ZIP contém um CSV sem cabeçalho, separado por `;`, com campos entre aspas e encoding latin-1, conforme o dicionário de dados da RF (`cnpj-metadados.pdf`). O tipo de cada arquivo é reconhecido pelo nome (ex: `...EMPRECSV`, `...ESTABELE`, `...SOCIOCSV` ou `Empresas0.zip`).

São dezenas de GB descomprimidos, então reserve espaço em disco para os ZIPs e, pelo menos, o mesmo tanto para o banco gerado.

# Carga: conversão para SQLite ou CSV

```
python3 cnpj.py <caminho entrada> <sqlite|csv> <pasta saída> [--dir] [--noindex] [--seguro] [--continuar]
```

Argumento | Descrição
--------- | ---------
`<caminho entrada>` | Pasta com os ZIPs (com `--dir`) ou um único arquivo
`<sqlite\|csv>` | `sqlite` gera `CNPJ_full.db`; `csv` gera um CSV tratado por tabela (`empresa.csv`, `estabelecimento.csv`...)
`<pasta saída>` | Onde os arquivos são gerados (é criada se não existir)
`--dir` | Lê todos os ZIPs (ou CSVs já extraídos) da pasta de entrada
`--noindex` | Só sqlite: **não** cria os índices no fim. Os índices são essenciais para as consultas
`--seguro` | Só sqlite: grava no modo normal do SQLite (veja abaixo)
`--continuar` | Só sqlite: retoma uma carga interrompida

Exemplos:

```bash
python3 cnpj.py dados sqlite saida --dir
python3 cnpj.py dados csv saida --dir
python3 cnpj.py dados/Empresas0.zip sqlite saida --noindex
python3 cnpj.py dados sqlite saida --dir --seguro
python3 cnpj.py dados sqlite saida --dir --seguro --continuar
```

O script mostra no terminal o progresso de cada arquivo, em blocos de 200.000 linhas, e no fim um resumo da verificação das quantidades. A carga completa leva horas, dependendo do disco e do processador.

Os nomes de tabelas e colunas seguem o modelo de banco do [cnpjrfb](https://github.com/bjverde/cnpjrfb/tree/master/modelo_banco).

## Tratamentos feitos na carga

* Datas zeradas (`0` ou `00000000`) viram vazio (NULL).
* `capital_social` é convertido de `1000,00` para número.
* Representante legal inexistente (`***000000**`) vira vazio.
* No SQLite, códigos de domínio (município, país, CNAE, natureza, qualificação, motivo etc.) são gravados como inteiros, para que os joins funcionem independentemente de zeros à esquerda. CNPJ, CPF, CEP e telefones continuam como texto.
* `situacao_cadastral` e `porte_empresa` são texto de 2 dígitos (ex: `02`, `05`), como no dicionário de dados da RF e no modelo do cnpjrfb.
* O campo `cnae_fiscal_secundaria` é mantido como no arquivo original (códigos separados por vírgula).

## Modo rápido x modo seguro (saída sqlite)

Cada arquivo da RF (ex: `Estabelecimentos3.zip`) é gravado em uma única transação e, ao terminar, registrado na tabela `controle_carga`, que também serve de verificação das quantidades (veja [Verificação da carga](#verificação-da-carga)).

Modo | Como ativar | Como grava | Vantagens | Desvantagens
---- | ----------- | ---------- | --------- | ------------
**Rápido** | padrão | Sem journal e sem sincronização em disco (`PRAGMA journal_mode=OFF`, `synchronous=OFF`) | Menos escrita em disco e nenhuma espera por `fsync`. A carga e a criação de índices ficam mais rápidas, principalmente em HD/SSD comum | Se o processo for interrompido (queda de energia, Ctrl+C, erro), o banco pode ficar corrompido e a carga precisa ser refeita do zero
**Seguro** | `--seguro` | Modo normal do SQLite: journal (`journal_mode=DELETE`) e sincronização em disco a cada transação (`synchronous=FULL`) | Uma interrupção desfaz apenas o arquivo que estava sendo gravado. O banco nunca fica corrompido, e a carga pode ser retomada com `--continuar` | Mais lento: cada página é gravada duas vezes (journal + banco) e o SQLite espera o disco confirmar a gravação

Em ambos os modos, ao final da carga o journal volta ao modo normal, para o uso do banco nas consultas.

Use o modo rápido quando a máquina for estável e você puder simplesmente rodar de novo em caso de falha. Use o `--seguro` em máquinas sujeitas a quedas de energia ou quando a carga demorar muitas horas.

### Retomando uma carga interrompida

`python3 cnpj.py PASTA_COM_ZIPS sqlite PASTA_DE_SAIDA --dir --seguro --continuar`

Com `--continuar`, o script não recria as tabelas e pula os arquivos já concluídos na `controle_carga`. O arquivo que estava sendo gravado na interrupção é carregado de novo desde o início.

Se a carga interrompida estava no modo rápido, o `--continuar` recusa retomar, porque a gravação parcial não pode ser desfeita. Nesse caso, rode a carga do zero.

## Verificação da carga

Como os CSVs novos da RF não trazem um total de registros, o script confere cada arquivo com três contagens independentes:

Coluna da `controle_carga` | O que conta
-------------------------- | -----------
`linhas_arquivo` | Linhas físicas do arquivo (quebras de linha), contadas durante a própria leitura
`registros_lidos` | Registros interpretados pelo leitor de CSV
`registros_descartados` | Linhas mal formadas (com mais campos que o layout) que foram ignoradas
`registros_gravados` | Registros deste arquivo efetivamente gravados no banco, contados com `SELECT COUNT(*)` antes do commit

O `status` fica `OK` quando `registros_gravados = registros_lidos`, não há descartados e `registros_lidos + registros_descartados = linhas_arquivo`. Caso contrário, fica `DIVERGENTE`, e a coluna `observacao` explica o motivo. Uma divergência é um aviso para investigar e não interrompe a carga. Por exemplo, um campo com quebra de linha dentro das aspas conta como 2 linhas físicas e 1 registro.

Ao final da carga é impresso um resumo com o status de cada arquivo. A qualquer momento, também é possível consultar:

```sql
SELECT arquivo, tabela, linhas_arquivo, registros_lidos, registros_descartados,
       registros_gravados, status, observacao
FROM controle_carga;
```

Na saída csv a mesma verificação é feita e impressa no resumo, mas não é gravada em tabela.

## Índices

Ao final da carga sqlite (a menos que se use `--noindex`), são criados índices em `cnpj_basico` de `empresa`, `estabelecimento` (junto com `cnpj_ordem` e `cnpj_dv`), `simples` e `socios`, em `cpf_cnpj_socio` e `nome_socio_razao_social` de `socios`, e no `codigo` das tabelas de domínio. Sem eles, as consultas ficam inviáveis.

# Consultas e grafo de relacionamentos

As consultas trazem empresas e sócios específicos e a rede de relacionamentos até a profundidade desejada. Funcionam sobre o banco SQLite gerado pelo `cnpj.py`.

Como funciona a rede no layout novo:
* Os sócios são vinculados ao **CNPJ básico** (8 primeiros dígitos). No grafo, a empresa é representada pelo estabelecimento **matriz**.
* Uma filial consultada aparece ligada à sua matriz (vínculo do tipo `filial`).
* Os nós são de três tipos: `1` pessoa jurídica (id = CNPJ de 14 dígitos), `2` pessoa física e `3` estrangeiro (id = CPF mascarado + nome).

```
python3 consulta.py <tipo consulta> <item|arquivo input> <pasta saída> [--base <arquivo sqlite>]
                    [--nivel <int>] [--csv] [--graphml] [--gexf] [--viz] [--conexoes <arquivo>]
```

## Tipos de consulta

Tipo | Busca
---- | -----
`cnpj` | Empresa pelo CNPJ, com ou sem pontuação (ex: `11.111.111/0001-91`)
`nome_socio` | Sócios pelo nome completo (maiúsculas e minúsculas tanto faz)
`cpf` | Sócios pelo CPF. Como a RF só publica 6 dígitos, pode trazer pessoas diferentes
`cpf_nome` | Sócio pelo CPF seguido do nome, sem espaço (ex: `***123456**FULANO DE TAL`)
`file` | Vários itens de um arquivo. Com uma coluna, cada linha é um CNPJ. Com duas colunas separadas por `;`, a primeira é o tipo acima e a segunda, o item

## Argumentos opcionais

Argumento | Descrição
--------- | ---------
`--base` | Arquivo SQLite. Se omitido, usa `PATH_BD` do `config.py`
`--nivel` | Profundidade em "pulos". `--nivel 1` traz o item e os diretamente relacionados. Se omitido, usa `NIVEL_MAX_DEFAULT`
`--csv` | Gera `pessoas.csv` e `vinculos.csv` (padrão se nenhuma saída for escolhida)
`--graphml` | Gera `rede.graphml`
`--gexf` | Gera `rede.gexf`, que pode ser aberto no [Gephi](https://gephi.org/)
`--viz` | Gera `grafo.html`, um grafo interativo para abrir no navegador. Se `PATH_NAVEGADOR` estiver no `config.py`, o navegador abre sozinho
`--conexoes` | Arquivo com pares de pessoas (CNPJ ou CPF mascarado + nome), um par por linha, separados por `;`. Gera `conexoes.csv` com o caminho entre cada par na rede encontrada, ou `SEM CONEXAO`

Exemplos:

```bash
python3 consulta.py cnpj 00000000000191 resultado --nivel 1 --viz
python3 consulta.py file entrada.csv resultado --csv --gexf
python3 consulta.py nome_socio "FULANO DE TAL" resultado --graphml --viz
python3 consulta.py cnpj 00000000000191 resultado --nivel 3 --conexoes pares.csv
```

**Atenção:** use a profundidade com moderação. Dependendo das empresas ou pessoas, a quantidade de relacionados cresce exponencialmente e gera muitas consultas no banco. Nível 3 é um bom parâmetro.

## Arquivos gerados

Arquivo | Conteúdo
------- | --------
`pessoas.csv` | Um nó por linha: coluna `id` mais as colunas de `COLUNAS_CSV` (tipo de pessoa, nível, CNPJ/CPF, nome, dados cadastrais e descrições de município, CNAE, natureza jurídica etc.)
`vinculos.csv` | Uma aresta por linha: `source` (sócio ou filial), `target` (empresa ou matriz), `tipo` (`socio` ou `filial`), `cod_qualificacao`, `qualificacao` e `data_entrada`
`rede.graphml` / `rede.gexf` | O grafo completo, com todos os atributos dos nós e vínculos
`grafo.html` | Visualização interativa (d3.js). Empresas inativas aparecem esmaecidas, e o item consultado tem borda vermelha
`conexoes.csv` | Só com `--conexoes`: pessoa A, pessoa B e o caminho entre elas

## Configuração (`config.py`)

Variável | Descrição
-------- | ---------
`PATH_BD` | Banco SQLite padrão (pode ser trocado com `--base`)
`NIVEL_MAX_DEFAULT` | Profundidade padrão (pode ser trocada com `--nivel`)
`PATH_NAVEGADOR` | Caminho do navegador para abrir o `grafo.html` automaticamente. Vazio só gera o arquivo
`SEP_CSV` | Separador dos CSVs de saída e do arquivo de entrada do tipo `file`
`COLUNAS_CSV` | Colunas do `pessoas.csv`
`QUALIFICACOES` | Qualificações de sócio consideradas nos vínculos, com a descrição que aparece no grafo. Uma qualificação fora da lista é ignorada (ex: um procurador não vira vínculo se o código `17` for removido). Use `'TODAS'` para considerar qualquer qualificação

## Trabalhando direto com a classe RedeCNPJ

O `consulta.py` é uma "casca" de linha de comando para a classe `RedeCNPJ`, de `rede_cnpj.py`. É ela que navega pelo banco e monta o grafo com o `networkx`, além de converter a rede em DataFrames pandas e nos formatos de grafo.

```python
import sqlite3
from rede_cnpj import RedeCNPJ

con = sqlite3.connect('saida/CNPJ_full.db')
rede = RedeCNPJ(con, nivel_max=2)
rede.insere_pessoa(1, '00000000000191')         # PJ pelo CNPJ
rede.insere_com_cpf_ou_nome(nome='FULANO DE TAL')

print(rede.dataframe_pessoas())
print(rede.dataframe_vinculos())
rede.gera_gexf('rede.gexf')
```

O atributo `rede.G` é o grafo `networkx`, que pode ser enriquecido com outras fontes e analisado com os algoritmos da biblioteca (caminhos, centralidade, detecção de ciclos etc.).

# Separando o CSV por UF ou município

Depois de gerar o `estabelecimento.csv` (saída `csv`), é possível dividi-lo por UF ou por município. O arquivo de cada cidade recebe o código do município da RF (veja a tabela `munic`).

1. Crie um arquivo `.env` (há um exemplo em `.env.example`) com a pasta onde está o `estabelecimento.csv`, **terminando com `/`**:

   ```
   FILES_LOCATION=/media/Arquivos/
   ```

2. Rode os scripts **de dentro da pasta `extra_csv`**:

   ```bash
   cd extra_csv
   python3 separar_csv_por_uf.py       # gera UFs/<UF>.csv
   python3 separar_csv_por_cidade.py   # gera UFs/<UF>/<codigo_municipio>.csv
   ```

# Sobre o CPF dos sócios e a LGPD

Por determinação legal, a RF publica o CPF dos sócios pessoas físicas **mascarado**: os três primeiros e os dois últimos dígitos são ocultados (ex: `***123456**`). Isso tem duas consequências:

* A busca por `cpf` compara só os 6 dígitos visíveis, então pode trazer pessoas diferentes. Para identificar uma pessoa, use `cpf_nome`.
* No grafo, a pessoa física é identificada pelo par CPF mascarado + nome.

Os dados são públicos, mas incluem dados pessoais (nomes de sócios, faixa etária). Use-os de acordo com a Lei Geral de Proteção de Dados (Lei 13.709/2018), com finalidade legítima e sem expor as pessoas indevidamente.

# Testes

Os testes usam uma amostra sintética no formato oficial da RF (`tests/amostra.py`) e cobrem a carga, a verificação das quantidades, a retomada com `--continuar` e as consultas do grafo. Eles rodam no GitHub Actions a cada PR. Para rodar localmente:

```bash
pip install pytest
python3 -m pytest tests
```

Para gerar só a amostra (útil para experimentar sem baixar os arquivos da RF):

```bash
python3 tests/amostra.py amostra
python3 cnpj.py amostra sqlite saida_amostra --dir
python3 consulta.py cnpj 11111111000272 resultado --base saida_amostra/CNPJ_full.db --viz
```

# Roteiro

Melhorias planejadas:

* Script para baixar automaticamente os ZIPs da competência mais recente.
* Tabela própria para os CNAEs secundários (uma linha por CNAE), para buscar empresas por atividade secundária.
* Carga direta em MySQL/MariaDB e PostgreSQL, usando os modelos do cnpjrfb.
* Trocar a leitura manual de argumentos por `argparse`.
* Atualizar o d3.js da visualização (hoje na versão 4).
* Tabela de tempo e tamanho da carga completa, a partir de uma carga real.
