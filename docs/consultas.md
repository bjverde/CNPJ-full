[← Voltar ao README](../README.md)

# Consultas e grafo de relacionamentos

As consultas trazem empresas e sócios específicos e a rede de relacionamentos até a profundidade desejada. Funcionam sobre o banco SQLite gerado pelo `cnpj_full/cnpj.py`.

Como funciona a rede no layout novo:
* Os sócios são vinculados ao **CNPJ básico** (8 primeiros dígitos). No grafo, a empresa é representada pelo estabelecimento **matriz**.
* Uma filial consultada aparece ligada à sua matriz (vínculo do tipo `filial`).
* Os nós são de três tipos: `1` pessoa jurídica (id = CNPJ de 14 dígitos), `2` pessoa física e `3` estrangeiro (id = CPF mascarado + nome).

```
python3 cnpj_full/consulta.py <tipo consulta> <item|arquivo input> <pasta saída> [--base <arquivo sqlite>]
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
`--base` | Arquivo SQLite. Se omitido, usa `PATH_BD` do `cnpj_full/config.py`
`--nivel` | Profundidade em "pulos". `--nivel 1` traz o item e os diretamente relacionados. Se omitido, usa `NIVEL_MAX_DEFAULT`
`--csv` | Gera `pessoas.csv` e `vinculos.csv` (padrão se nenhuma saída for escolhida)
`--graphml` | Gera `rede.graphml`
`--gexf` | Gera `rede.gexf`, que pode ser aberto no [Gephi](https://gephi.org/)
`--viz` | Gera `grafo.html`, um grafo interativo para abrir no navegador. Se `PATH_NAVEGADOR` estiver no `cnpj_full/config.py`, o navegador abre sozinho
`--conexoes` | Arquivo com pares de pessoas (CNPJ ou CPF mascarado + nome), um par por linha, separados por `;`. Gera `conexoes.csv` com o caminho entre cada par na rede encontrada, ou `SEM CONEXAO`

Exemplos:

```bash
python3 cnpj_full/consulta.py cnpj 00000000000191 resultado --nivel 1 --viz
python3 cnpj_full/consulta.py file entrada.csv resultado --csv --gexf
python3 cnpj_full/consulta.py nome_socio "FULANO DE TAL" resultado --graphml --viz
python3 cnpj_full/consulta.py cnpj 00000000000191 resultado --nivel 3 --conexoes pares.csv
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

## Configuração (`cnpj_full/config.py`)

Variável | Descrição
-------- | ---------
`PATH_BD` | Banco SQLite padrão (pode ser trocado com `--base`)
`NIVEL_MAX_DEFAULT` | Profundidade padrão (pode ser trocada com `--nivel`)
`PATH_NAVEGADOR` | Caminho do navegador para abrir o `grafo.html` automaticamente. Vazio só gera o arquivo
`SEP_CSV` | Separador dos CSVs de saída e do arquivo de entrada do tipo `file`
`COLUNAS_CSV` | Colunas do `pessoas.csv`
`QUALIFICACOES` | Qualificações de sócio consideradas nos vínculos, com a descrição que aparece no grafo. Uma qualificação fora da lista é ignorada (ex: um procurador não vira vínculo se o código `17` for removido). Use `'TODAS'` para considerar qualquer qualificação

## Trabalhando direto com a classe RedeCNPJ

O `cnpj_full/consulta.py` é uma "casca" de linha de comando para a classe `RedeCNPJ`, de `cnpj_full/rede_cnpj.py`. É ela que navega pelo banco e monta o grafo com o `networkx`, além de converter a rede em DataFrames pandas e nos formatos de grafo.

```python
import sqlite3
from cnpj_full.rede_cnpj import RedeCNPJ  # rodando da raiz do projeto

con = sqlite3.connect('saida/CNPJ_full.db')
rede = RedeCNPJ(con, nivel_max=2)
rede.insere_pessoa(1, '00000000000191')         # PJ pelo CNPJ
rede.insere_com_cpf_ou_nome(nome='FULANO DE TAL')

print(rede.dataframe_pessoas())
print(rede.dataframe_vinculos())
rede.gera_gexf('rede.gexf')
```

O atributo `rede.G` é o grafo `networkx`, que pode ser enriquecido com outras fontes e analisado com os algoritmos da biblioteca (caminhos, centralidade, detecção de ciclos etc.).

## Sobre o CPF dos sócios e a LGPD

Por determinação legal, a RF publica o CPF dos sócios pessoas físicas **mascarado**: os três primeiros e os dois últimos dígitos são ocultados (ex: `***123456**`). Isso tem duas consequências:

* A busca por `cpf` compara só os 6 dígitos visíveis, então pode trazer pessoas diferentes. Para identificar uma pessoa, use `cpf_nome`.
* No grafo, a pessoa física é identificada pelo par CPF mascarado + nome.

Os dados são públicos, mas incluem dados pessoais (nomes de sócios, faixa etária). Use-os de acordo com a Lei Geral de Proteção de Dados (Lei 13.709/2018), com finalidade legítima e sem expor as pessoas indevidamente.

