[← Voltar ao README](../README.md) · [← Consultas e grafo](consultas.md#cache)

# Cache do grafo: exemplos

Como o `--cache` do `consulta.py` funciona na prática e como os arquivos ficam no disco. As regras estão resumidas na seção [Cache de consultas.md](consultas.md#cache). Os exemplos foram rodados com a amostra sintética dos testes (`tests/amostra.py`), e as saídas são as que o programa imprimiu. Nos comandos, o `--base` foi omitido.

## 1. Primeira consulta: vai ao banco e grava o cache

```bash
python cnpj_full/consulta.py cnpj 11111111000272 graficos/11111111000272_n3 --nivel 3 --viz --cache
```
```
Consulta finalizada. Verifique o(s) arquivo(s) de saida na pasta "graficos/11111111000272_n3".
```

No disco:
```
graficos/
└── 11111111000272_n3/
    ├── grafo.html     (298 KB: o grafo, com o d3 embutido)
    └── cache.json     (900 bytes: a "etiqueta" do resultado)
```

O `cache.json` (lista de qualificações resumida):
```json
{
  "chave": {
    "versao_cache": 1,
    "tipo_consulta": "cnpj",
    "objeto_consulta": "11111111000272",
    "nivel": 3,
    "qualificacoes": ["05", "08", "10", "16", "...", "75"],
    "base": "carga:13:2026-11-02T04:17:52",
    "saidas": {"csv": false, "graphml": false, "gexf": false, "viz": true, "conexoes": null}
  },
  "arquivos": ["grafo.html"]
}
```

* `base` = quantidade de arquivos carregados e data de fim da última carga, lidas da `controle_carga`. É isso que amarra o cache à carga da base.
* `arquivos` = o que o cache entrega. O resultado é o próprio `grafo.html`; não existe um formato de cache à parte.

## 2. Mesma consulta de novo: não toca no banco

```bash
python cnpj_full/consulta.py cnpj 11.111.111/0002-72 graficos/11111111000272_n3 --nivel 3 --viz --cache
```
```
Resultado reaproveitado do cache na pasta "graficos/11111111000272_n3".
```
O CNPJ com máscara conta como a mesma consulta. O `grafo.html` continua o mesmo arquivo (nem é regravado).

## 3. Outro nível ou outra pessoa: outra pasta, outro cache

```bash
python cnpj_full/consulta.py cnpj 11111111000272 graficos/11111111000272_n1 --nivel 1 --viz --cache
python cnpj_full/consulta.py nome_socio "maria souza" graficos/socio_MARIA_SOUZA_n3 --nivel 3 --viz --csv --cache
```
No disco:
```
graficos/
├── 11111111000272_n1/
│   ├── cache.json
│   └── grafo.html
├── 11111111000272_n3/
│   ├── cache.json
│   └── grafo.html
└── socio_MARIA_SOUZA_n3/
    ├── cache.json
    ├── grafo.html
    ├── pessoas.csv      (pedido com --csv: também faz parte do cache)
    └── vinculos.csv
```
Cada pasta guarda **uma** consulta. Quem chama escolhe o nome da pasta, por exemplo `<cnpj>_n<nível>`. Se uma consulta diferente for gravada na mesma pasta (ex.: nível 1 em `..._n3`), ela substitui o resultado anterior: a chave não bate, os arquivos antigos são apagados e tudo é refeito.

## 4. A Receita publica dados novos e você recarrega a base

Depois da carga nova, a `controle_carga` muda (no exemplo, o fim passou a ser `2027-02-15 03:10:00`):

```bash
python cnpj_full/consulta.py cnpj 11111111000272 graficos/11111111000272_n3 --nivel 3 --viz --cache
# Consulta finalizada ...           <- base mudou: refaz e regrava o cache
python cnpj_full/consulta.py cnpj 11111111000272 graficos/11111111000272_n3 --nivel 3 --viz --cache
# Resultado reaproveitado do cache  <- vale de novo, agora para a base nova
```
O `cache.json` passa a ter `"base": "carga:13:2027-02-15 03:10:00"`. O cache não tem prazo em dias: ele vale até a próxima carga, seja ela mensal ou trimestral.

## 5. Consulta por `cpf_nome`

O item é o CPF seguido do nome, sem espaço. O CPF pode ir completo ou já mascarado, e o nome em maiúsculas ou minúsculas.

```bash
python cnpj_full/consulta.py cpf_nome "11165432100MARIA SOUZA" graficos/cpf_654321_MARIA_SOUZA_n3 --nivel 3 --viz --cache
# Consulta finalizada ...
python cnpj_full/consulta.py cpf_nome "***654321**maria souza" graficos/cpf_654321_MARIA_SOUZA_n3 --nivel 3 --viz --cache
# Resultado reaproveitado do cache ...
```

No `cache.json`, a chave fica com o CPF **sempre mascarado** e o nome em maiúsculas, como a RF publica:
```json
"tipo_consulta": "cpf_nome",
"objeto_consulta": "***654321**MARIA SOUZA",
"nivel": 3
```
Por isso as duas chamadas acima são a mesma consulta, e o CPF completo nunca é gravado em disco (LGPD).

No disco:
```
graficos/
└── cpf_654321_MARIA_SOUZA_n3/
    ├── cache.json
    └── grafo.html
```
Para o nome da pasta, use só os 6 dígitos do meio do CPF e troque espaços por `_`. Não use o `*`, porque ele não é aceito em nome de pasta no Windows.

O CPF sozinho não identifica o sócio, porque a RF só publica 6 dígitos. Por isso o `cpf_nome` é a forma certa de pedir o grafo de uma pessoa: `cpf` sozinho pode juntar pessoas diferentes, e `nome_socio` pode juntar homônimos.

## Quando o cache é refeito

| Mudou...                                  | Resultado        |
|-------------------------------------------|------------------|
| nada                                      | reaproveita      |
| máscara do CNPJ, CPF completo ou mascarado, maiúsc./minúsc. do nome | reaproveita |
| item pesquisado ou tipo de consulta       | refaz            |
| `--nivel`                                 | refaz            |
| `QUALIFICACOES` no `config.py`            | refaz            |
| saídas pedidas (`--csv`, `--gexf`...)     | refaz            |
| carga da base (`controle_carga`)          | refaz            |
| algum arquivo da pasta foi apagado        | refaz            |
| rodou sem `--cache`                       | sempre refaz     |

Para forçar uma consulta nova: apagar o `cache.json` (ou a pasta) ou rodar sem `--cache`.

## No cnpjrfb

A tela chamaria, por exemplo:
```
python cnpj_full/consulta.py cnpj 11111111000272 graficos/11111111000272_n3 --nivel 3 --viz --cache
```
e mostraria `graficos/11111111000272_n3/grafo.html` no iframe, como já faz hoje. Depois de uma carga nova, as pastas antigas continuam no disco até serem pedidas de novo (aí são refeitas). Se o espaço pesar, basta apagar `graficos/` junto com a carga.
