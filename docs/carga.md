[← Voltar ao README](../README.md)

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

Cada ZIP contém um CSV sem cabeçalho, separado por `;`, com campos entre aspas e encoding latin-1, conforme o [dicionário de dados da RF](cnpj-metadados.pdf). O tipo de cada arquivo é reconhecido pelo nome (ex: `...EMPRECSV`, `...ESTABELE`, `...SOCIOCSV` ou `Empresas0.zip`).

São dezenas de GB descomprimidos, então reserve espaço em disco para os ZIPs e, pelo menos, o mesmo tanto para o banco gerado.

# Carga: conversão para SQLite ou CSV

```
python3 cnpj_full/cnpj.py <caminho entrada> <sqlite|csv> <pasta saída> [--dir] [--noindex] [--seguro] [--continuar]
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
python3 cnpj_full/cnpj.py dados sqlite saida --dir
python3 cnpj_full/cnpj.py dados csv saida --dir
python3 cnpj_full/cnpj.py dados/Empresas0.zip sqlite saida --noindex
python3 cnpj_full/cnpj.py dados sqlite saida --dir --seguro
python3 cnpj_full/cnpj.py dados sqlite saida --dir --seguro --continuar
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

`python3 cnpj_full/cnpj.py PASTA_COM_ZIPS sqlite PASTA_DE_SAIDA --dir --seguro --continuar`

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

## Separando o CSV por UF ou município

Depois de gerar o `estabelecimento.csv` (saída `csv`), é possível dividi-lo por UF ou por município. O arquivo de cada cidade recebe o código do município da RF (veja a tabela `munic`).

1. Crie um arquivo `.env` (há um exemplo em `.env.example`) com a pasta onde está o `estabelecimento.csv`, **terminando com `/`**:

   ```
   FILES_LOCATION=/media/Arquivos/
   ```

   O `.env` pode ficar na raiz do projeto.

2. Rode os scripts:

   ```bash
   python3 cnpj_full/extra_csv/separar_csv_por_uf.py       # gera UFs/<UF>.csv
   python3 cnpj_full/extra_csv/separar_csv_por_cidade.py   # gera UFs/<UF>/<codigo_municipio>.csv
   ```

