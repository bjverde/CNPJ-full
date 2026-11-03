[← Voltar ao README](../README.md)

# Download dos arquivos da Receita

O script `cnpj_full/download.py` baixa os dados abertos do CNPJ direto do servidor da Receita Federal (RF), sem precisar abrir o navegador.

```bash
python3 cnpj_full/download.py                         # competência mais recente, para dados/AAAA-MM/
python3 cnpj_full/download.py --listar                # só mostra a competência e os arquivos
python3 cnpj_full/download.py --competencia 2026-09   # uma competência específica
python3 cnpj_full/download.py --destino D:\cnpj       # outra pasta de destino (Windows)
python3 cnpj_full/download.py --filtro "Cnaes|Paises" # só alguns arquivos (expressão regular)
python3 cnpj_full/download.py https://outro.servidor/index.php/s/TOKEN   # outra URL
```

Para ver a ajuda com todos os argumentos: `python cnpj_full/download.py --help`. Sem argumentos o script não mostra a ajuda: ele já baixa a competência mais recente com as configurações padrão.

Argumento | Descrição | Padrão
--------- | --------- | ------
`url` | Endereço do compartilhamento da RF | `CNPJ_RF_URL` do `.env`, ou `https://arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9`
`--destino` | Pasta onde salvar. Os arquivos vão para `<destino>/<AAAA-MM>/` | `CNPJ_PASTA_DOWNLOAD` do `.env`, ou `dados`
`--competencia AAAA-MM` | Baixa essa competência em vez da mais recente | a mais recente
`--listar` | Mostra a competência escolhida e os arquivos com o tamanho, sem baixar |
`--filtro REGEX` | Baixa só os arquivos cujo nome casa com a expressão (sem diferenciar maiúsculas) | todos

Usa só a biblioteca padrão do Python (não precisa instalar nada além do `requirements.txt`), e funciona igual no Windows, no Linux e no Docker.

## Como a competência é escolhida

A RF publica os dados em um compartilhamento público do Nextcloud, com uma pasta por competência (ex: `2026-10/`). O script lista as pastas pelo WebDAV público do Nextcloud (`public.php/webdav`, usando o token do link como usuário) e:

1. entre as pastas com nome de data, entra na mais recente: primeiro as do tipo ano-mês (`2026-10`, `2026_10`, `202610`); se não houver, a do ano mais recente (`2026`) e, dentro dela, a do último mês (`10`, `10 - Outubro`, `Outubro`);
2. ignora as pastas que não têm nome de data (ex: `temp`, `regime_tributario`);
3. quando chega numa pasta sem subpastas de data, baixa **todos os arquivos** dela.

Também aceita:
* link do Nextcloud com subpasta: `https://host/index.php/s/TOKEN?dir=/Dados/Cadastros/CNPJ`;
* listagem de diretório comum (Apache/nginx), como a antiga `https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/`.

## Pode rodar de novo à vontade

* Arquivo já baixado com o mesmo tamanho do servidor (e, se for ZIP, legível) é pulado.
* O download é gravado primeiro como `<arquivo>.part` e só é renomeado quando termina. Se cair a conexão ou você interromper (Ctrl+C), rode o mesmo comando: ele continua de onde parou (pedido HTTP `Range`). Se o servidor não aceitar continuar, recomeça aquele arquivo.
* Falhas de rede são tentadas de novo até 5 vezes, esperando 2, 4, 8 e 16 segundos.
* Cada ZIP é conferido ao final (o diretório interno do ZIP precisa ser legível). ZIP corrompido é apagado e o script avisa para rodar de novo.

São cerca de 7 GB compactados por competência. Reserve espaço para os ZIPs e para o banco gerado.

## Depois do download

O script mostra no fim o comando de carga, por exemplo:

```bash
python3 cnpj_full/carga.py dados/2026-10 sqlite saida --dir      # SQLite
python3 cnpj_full/carga.py dados/2026-10 postgres --dir           # PostgreSQL (docs/postgresql.md)
```

## Proxy

O script usa o proxy das variáveis `HTTPS_PROXY`/`HTTP_PROXY` (e `NO_PROXY`), se estiverem definidas, como qualquer programa Python.
