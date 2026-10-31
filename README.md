# Dados Públicos CNPJ - Conversão para CSV/SQLITE e Consultas
Utilitário em Python para carregar a base completa de CNPJ [disponibilizada pela Receita Federal](https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj) e transformá-la em arquivos csv ou sqlite para fácil consumo. Processa dados de empresas, estabelecimentos, sócios, Simples/MEI e tabelas de domínio (CNAEs, municípios, países, naturezas jurídicas, qualificações e motivos).
Possibilita também fazer consultas de empresas ou sócios e gravar resultados em CSV ou em grafo de relacionamentos.

![Grafo](img/grafo.png?raw=true "Grafo")

**Layout novo (a partir de março de 2021)**

A Receita Federal passou a disponibilizar os dados em vários arquivos ZIP, cada um com um CSV sem cabeçalho, separado por `;` e em encoding latin-1. Os scripts deste repositório foram atualizados para esse layout, conforme o dicionário de dados da RF (`cnpj-metadados.pdf`).

Os nomes de tabelas e colunas gerados seguem o modelo de banco do projeto [cnpjrfb](https://github.com/bjverde/cnpjrfb/tree/master/modelo_banco):

Tabela | Arquivos da RF | Conteúdo
------ | -------------- | --------
`empresa` | `Empresas*.zip` | Dados da empresa (CNPJ básico, razão social, natureza jurídica, capital social, porte...)
`estabelecimento` | `Estabelecimentos*.zip` | Matriz e filiais (CNPJ completo = `cnpj_basico` + `cnpj_ordem` + `cnpj_dv`), endereço, situação, CNAEs
`socios` | `Socios*.zip` | Quadro societário, vinculado ao CNPJ básico
`simples` | `Simples.zip` | Opção pelo Simples e pelo MEI
`cnae`, `moti`, `munic`, `natju`, `pais`, `quals` | `Cnaes.zip`, `Motivos.zip`, `Municipios.zip`, `Naturezas.zip`, `Paises.zip`, `Qualificacoes.zip` | Tabelas de domínio (`codigo`, `descricao`)

Tratamentos feitos na carga:
* Datas zeradas (`0` ou `00000000`) viram vazio (NULL).
* `capital_social` é convertido de `1000,00` para número.
* Representante legal inexistente (`***000000**`) vira vazio.
* No SQLite, códigos de domínio (município, país, CNAE, natureza, qualificação, motivo etc.) são gravados como inteiros, para que os joins funcionem independentemente de zeros à esquerda. CNPJ, CPF, CEP e telefones continuam como texto.
* `situacao_cadastral` e `porte_empresa` são texto de 2 dígitos (ex: `02`, `05`), como no dicionário de dados da RF e no modelo do cnpjrfb.
* O campo `cnae_fiscal_secundaria` é mantido como no arquivo original (códigos separados por vírgula).

# Conversão para CSV ou SQLITE

A forma recomendada de fazer a carga é: baixar todos os arquivos zip de uma mesma competência para uma pasta dedicada (sem renomear) e executar:

`python3 cnpj.py PASTA_COM_ZIPS sqlite PASTA_DE_SAIDA --dir`

ou

`python3 cnpj.py PASTA_COM_ZIPS csv PASTA_DE_SAIDA --dir`

## Configurações prévias
Para executar o script, é necessário que seu sistema contenha essas instalações:

## Python
Versão mais atual, caso não consiga executar usando somente o comando `python`. Para isso, execute no terminal (se estiver usando sistemas GNU/Linux derivados do Debian):

` $ sudo apt upgrade python3`

## Gerenciador de Pacotes do Python (Pip)
A versão mais atual. Se estiver usando Python3:

`$ python3 -m pip install --upgrade pip`

## Instalar Pré-Requisitos:

`$ pip install -r requirements.txt`

Esse comando instalará as seguintes bibliotecas:

#### Pandas
A versão mais atual da biblioteca [Pandas](https://pandas.pydata.org) para Python. 

#### NumPy
A princípio, não é necessário. O script neste repositório usa funções da biblioteca [Pandas](https://pandas.pydata.org), que utiliza uma extensão de NumPy chamada [NumExpr](#numexpr). Então, **caso** seu terminal retorne erros por ausência do pacote [NumPy](https://pypi.org/project/numpy/), esse é o motivo. 

#### NumExpr
O [Pandas](https://pandas.pydata.org) usa. É uma extensão que melhora a velocidade de análise no pacote [NumPy](#pacote-numpy).


## Antes de executar
Atente para o fato de que os arquivos disponibilizados pela RF são muito grandes (dezenas de GB descomprimidos).
Portanto, é bastante provável que seu computador dedique tempo considerável a essa execução.

O script informa no terminal o parcial do processamento de cada arquivo, em blocos de 200.000 linhas. O tipo de cada arquivo é identificado pelo nome (ex: `...EMPRECSV`, `...ESTABELE`, `...SOCIOCSV` ou `Empresas0.zip`), então os ZIPs podem ser lidos diretamente, sem descompactar.

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

## Como executar
`python3 cnpj.py <caminho entrada> <tipo de saída:csv ou sqlite> <pasta saída> [--dir] [--noindex] [--seguro] [--continuar]`

Para processar todos os arquivos, salvar em uma pasta, usá-la como `<caminho entrada>` e especificar o argumento `--dir`. Sem `--dir`, apenas o arquivo informado é carregado.

O argumento opcional `--noindex`, aplicável somente para saída sqlite, indica que **não** devem ser gerados índices automaticamente.
A criação de índices é muito recomendada e essencial para a funcionalidade de consultas.

Os argumentos opcionais `--seguro` e `--continuar`, aplicáveis somente para saída sqlite, estão explicados em [Modo rápido x modo seguro](#modo-rápido-x-modo-seguro-saída-sqlite).

## Exemplos
`python3 cnpj.py "data" sqlite "output" --dir`

`python3 cnpj.py "data" csv "output" --dir`

`python3 cnpj.py "data/Empresas0.zip" sqlite "output" --noindex`

`python3 cnpj.py "data" sqlite "output" --dir --seguro`

`python3 cnpj.py "data" sqlite "output" --dir --seguro --continuar`

## Separando arquivos CSV por estado ou municipio

Após ter gerado o arquivo `estabelecimento.csv` (saída csv), é possível dividir por estado, ou por cidade (o arquivo de cada cidade recebe o código do município da RF, ver tabela `munic`)

### Requisitos

`$ python3 -m pip install python-dotenv`

Para ambos os scripts é necessário informar a localização do arquivo `estabelecimento.csv` no arquivo `.env`

`FILES_LOCATION=/media/Arquivos`

Após isso basta executar os scripts:

#### Para separar por UF:

`python3 separar_csv_por_uf.py`

#### Para separar por cidade:

`python3 separar_csv_por_cidade.py`

# Consultas

**Novidade!** Agora é possível fazer consultas que além de trazer empresas e sócios específicos, traz a rede de relacionamentos na profundidade desejada. Os resultados podem ser salvos em formato tabular e/ou em formatos variados de grafos de relacionamento, que podem ser visualizados de forma interativa no navegador ou abertos em softwares que suportem os formatos especificados, como o [Gephi](https://gephi.org/).

Essa funcionalidade é exclusiva para a base sqlite gerada usando o `cnpj.py`. No entanto, pode ser relativamente simples adaptar o código para funcionar com outros SGBDs ou arquivos sqlite gerados usando outra nomenclatura.

## Configurações prévias
Para executar o script de consulta, é necessário que seu sistema contenha as instalações especificadas acima e, além disso, é necessário:

#### Networkx 2.x (pacote de criação, manipulação e análise de grafos/redes)

É **IMPRESCINDÍVEL** que índices sejam criados no `cnpj_basico` das tabelas `empresa`, `estabelecimento`, `simples` e `socios`, e nos campos `nome_socio_razao_social` e `cpf_cnpj_socio` da tabela `socios`. Do contrário, as consultas se tornam insuportavelmente lentas ou até mesmo inviáveis dependendo da profundidade. O script de carga (cnpj.py) foi atualizado para opcionalmente gerar os índices mais importantes automaticamente ao final da carga.

## Instruções Básicas:

Uso: `python consulta.py <tipo consulta> <item|arquivo input> <caminho output> [--base <arquivo sqlite>]`
`[--nivel <int>] [--csv] [--graphml] [--gexf] [--viz]`

#### Argumentos obrigatórios:

`<tipo consulta>`: Especifica o tipo de item a ser procurado. Opções:
* **cnpj:** Busca empresa pelo número do CNPJ.

* **nome_socio:** Busca sócios pelo nome completo.

* **cpf:** Busca sócios pelo número do CPF.
      (Pode trazer vários sócios, uma vez que apenas seis dígitos são fornecidos pela RF)

No novo layout os sócios são vinculados ao CNPJ básico (8 primeiros dígitos). No grafo, a empresa é representada pelo estabelecimento matriz, e cada filial consultada aparece ligada à sua matriz.
      
* **cpf_nome:** Busca sócios pelo número do CPF seguido (sem espaço) do nome completo.

* **file:** Arquivo que contem mais de um item a ser buscado.
        Caso o arquivo tenha apenas um dado por linha, será tratado como número de CNPJ.
        Caso o arquivo tenha mais de um dado separado por `;`, o primeiro
        indica um dos tipos acima, e o segundo o item a ser buscado.
        (outro separador pode ser definido em `SEP_CSV` no `config.py`) 

`<item|arquivo input>`: Item a ser procurado, de acordo com `<tipo consulta>`.
  
`<caminho output>`: Pasta onde serão salvos os arquivos gerados.

#### Argumentos opcionais:

`--base`: Especifica o arquivo do banco de dados de CNPJ em formato sqlite.
           Caso não seja especificado, usa o `PATH_BD` definido no `config.py`

`--nivel`: Especifica a profundidade da consulta em número de "pulos".
            Exemplo: Caso seja especificado `--nivel 1`, busca o item e as empresas ou pessoas diretamente relacionadas.
            Caso não seja especificado, usa o `NIVEL_MAX_DEFAULT` no `config.py`

`--csv`: Para gerar o resultado em arquivos csv.
          São gerados dois arquivos, `pessoas.csv` e `vinculos.csv`.

`--graphml`: Para gerar o resultado em grafo no formato GRAPHML.

`--gexf`: Para gerar o resultado em grafo no formato GEXF. 
           Pode ser aberto com o software [Gephi](https://gephi.org/)

 `--viz`: Para gerar um HTML interativo com o resultado em grafo.
          Para abrir automaticamente o navegador, informar o `PATH_NAVEGADOR` 
          no `config.py`. Do contrário, basta abrir o arquivo `grafo.html` gerado 
          em `<caminho output>` com o navegador de preferência.

#### Exemplos:

`python consulta.py cnpj 00000000000191 folder --nivel 1 --viz`

`python consulta.py file data/input.csv pasta --csv --gexf`

`python consulta.py nome_socio "FULANO SICRANO" output --graphml --viz`

#### Atenção:

Especifique o nível de profundidade da rede com moderação, uma vez que, dependendo das empresas ou pessoas buscadas, a quantidade de relacionados pode crescer exponencialmente, atingindo facilmente centenas ou milhares de registros, o que resulta na execução intensiva de queries no BD. Nível 3 é um bom parâmetro.

#### Configuração

No `config.py`, as seguintes configurações são definidas:

`PATH_BD`: Caminho para o arquivo de banco de dados da Receita Federal convertido em sqlite. 
Pode ser sobrescrito em tempo de execução usando o argumento `--base`.

`NIVEL_MAX_DEFAULT`: Nível máximo default para a profundidade das buscas.
Pode ser sobrescrito em tempo de execução usando o argumento `--nivel <num>`

`PATH_NAVEGADOR`: Caminho completo para o executável do navegador preferido se desejar que a visualização seja automaticamente apresentada ao final da execução da consulta (se argumento `--viz` for utilizado). Caso vazio, apenas gera o html na pasta de saída.

`SEP_CSV`: Especifica o separador a ser considerado tanto para os arquivos csv de saída (caso seja utilizado o argumento `--csv`), quanto para o arquivo de entrada no caso do uso de `file` como `<tipo consulta>`.

`COLUNAS_CSV`: Especifica a lista de colunas a serem incluídas no arquivo `pessoas.csv` quando usado o argumento `--csv`.

`QUALIFICACOES`: Especifica a lista de qualificações de sócios a serem consideradas na busca dos relacionamentos. Caso `TODAS`, qualquer relação de sociedade listada no BD é considerada.

## Trabalhando diretamente com a classe RedeCNPJ

O objetivo do `consulta.py` é disponibilizar uma interface por linha de comando para facilitar a extração/visualização da rede de relacionamentos de empresas e pessoas a partir da base de dados da RF convertida em sqlite. Ele é uma "casca" para a classe `RedeCNPJ` definida em `rede_cnpj.py`, onde fica a inteligência de navegação no BD e criação de rede/grafo usando o pacote `networkx`, além de métodos para conversão em DataFrames pandas e formatos diversos de representação de estruturas em grafo.

Em seu projeto você pode instanciar diretamente a `RedeCNPJ` especificando a conexão ao BD e o nível máximo de navegação nos relacionamentos, usar os métodos de inserção de empresas/pessoas para montar a rede (sem se preocupar com a navegação para as relacionadas), e usar os métodos para conversão da rede em DataFrame ou formatos diversos de representação de grafos.

E dessa forma você pode também usar o grafo gerado (atributo "G" da classe) para incrementá-lo a partir de outras fontes de dados de interesse para seu caso de uso e usar os diversos algoritmos disponibilizados pela biblioteca `networkx`, como por exemplo detecção de ciclos.

## TO DO

* Aprimorar a documentação do código (principalmente da classe RedeCNPJ) e as instruções neste README.
