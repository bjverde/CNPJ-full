[← Voltar ao README](../README.md)

# Instalação e teste nos 4 ambientes

Este guia mostra como instalar e testar o CNPJ-full em:

1. [Somente Windows](#1-somente-windows) (Python instalado no Windows)
2. [Somente Linux](#2-somente-linux) (Python instalado no Linux)
3. [Docker com volume no Windows](#3-docker-com-volume-no-windows) (Docker Desktop)
4. [Docker com volume no Linux](#4-docker-com-volume-no-linux) (Docker Engine)

Nos quatro casos o teste é o mesmo: consultar uma empresa no **banco de teste** que já vem no repositório e abrir o grafo no navegador. Não é preciso baixar nada da Receita Federal para isso.

* [Banco de teste](#banco-de-teste)
* [Arquivo .env: onde fica o banco](#arquivo-env-onde-fica-o-banco)
* [Roteiro de teste](#roteiro-de-teste) (os mesmos comandos em todos os ambientes)
* [Usando outra imagem Docker (ex.: Debian 13 do cnpjrfb)](#usando-outra-imagem-docker-ex-debian-13-do-cnpjrfb)
* [Problemas comuns](#problemas-comuns)

---

# Banco de teste

O arquivo [`dados_teste/cnpj_teste.db`](../dados_teste) é um banco SQLite pequeno (cerca de 200 KB) com o mesmo modelo da base completa (o mesmo do [cnpjrfb](https://github.com/bjverde/cnpjrfb)). Ele é versionado no git, então funciona logo depois do `git clone`.

**Todos os dados são fictícios**: nomes de empresas e pessoas são inventados e os CPFs seguem o formato mascarado da RF (`***123456**`). Só as tabelas de domínio (CNAEs, municípios, naturezas jurídicas, qualificações, países e motivos) usam códigos reais. Assim o banco pode ficar no repositório sem problema de LGPD.

Conteúdo: 202 empresas, 236 estabelecimentos, 311 sócios e 96 optantes do Simples. Há quatro grupos econômicos montados para o grafo ter ligações até o nível 3, além de cerca de 180 empresas avulsas cujos sócios aparecem em várias empresas.

Consultas de exemplo (o nível padrão é 3). A coluna "nós" é o número de empresas e pessoas no grafo com `--nivel 1`, `2` e `3`:

Consulta | O que mostra | Nós (nível 1 / 2 / 3)
-------- | ------------ | ---------------------
`cnpj 10000001000190` | **ALFA HOLDING**: 4 controladas ativas e 1 baixada, controlada de controlada, filiais, sócio estrangeiro, administradora comum a várias empresas | 9 / 11 / 13
`cnpj 50000001000104` | **CHARLIE PARTICIPACOES**: cadeia holding > indústria > distribuidora > logística, com a logística no nível 3 | 4 / 7 / 9
`cnpj 50000004000148` | **CHARLIE LOGISTICA**: a mesma cadeia vista de baixo para cima, até a holding | 3 / 4 / 7
`cnpj 60000001000168` | **PADARIA DELTA**: empresas de uma família ligadas só por pessoas, sem holding; uma sócia também é sócia do restaurante do presidente do grupo ALFA | 4 / 6 / 8
`cnpj 20000001000143` | **BRAVO SERVICOS**: grupo menor, controlada de controlada e sócio PJ que não está na base | 4 / 5 / 6
`cnpj 40000006000183` | **CONTABILIDADE ESTRELA LUAR**: empresa avulsa; os sócios estão em muitas empresas, rede grande | 4 / 22 / 32
`nome_socio "ANA TEIXEIRA HENRIQUES"` | Busca por pessoa: filho da família DELTA, sócio de duas empresas | 3 / 5 / 8

Exemplo: `python cnpj_full/consulta.py cnpj 50000001000104 resultado --nivel 3 --viz`.

O banco é gerado pelo script [`dados_teste/gerar_banco_teste.py`](../dados_teste/gerar_banco_teste.py), que cria ZIPs no formato da RF e carrega com o próprio `cnpj_full/cnpj.py`. A geração é determinística: rodar de novo gera os mesmos dados. Os testes automáticos conferem que o `.db` versionado está igual ao que o script gera.

```bash
python dados_teste/gerar_banco_teste.py                 # recria dados_teste/cnpj_teste.db
python dados_teste/gerar_banco_teste.py --zips dados    # também guarda os ZIPs em "dados" (para testar a carga)
```

# Arquivo .env: onde fica o banco

O `consulta.py` escolhe o banco nesta ordem:

Ordem | De onde vem | Caminho relativo é relativo a...
----- | ----------- | --------------------------------
1 | `--base <arquivo>` na linha de comando | pasta onde você roda o comando
2 | `CNPJ_DB_ARQUIVO` definido no ambiente (ex.: `docker run -e`) ou no arquivo `.env` | **raiz do projeto**
3 | Banco de teste `dados_teste/cnpj_teste.db` | raiz do projeto

Ou seja: **sem `.env` e sem `--base`, a consulta usa o banco de teste**, de qualquer pasta. O programa sempre mostra qual banco usou na primeira linha (`Banco: ...`).

O `.env` fica **na raiz do projeto**, ao lado do `README.md` (é lá que o programa procura, não na pasta onde você roda o comando). Para criar:

```bash
cp .env.example .env                 # Linux, macOS, Docker
copy .env.example .env               # Windows (cmd)
Copy-Item .env.example .env          # Windows (PowerShell)
```

Variáveis (o [`.env.example`](../.env.example) tem todas, comentadas):

Variável | Para que serve | Exemplo
-------- | -------------- | -------
`CNPJ_DB_TIPO` | Tipo de banco. Por enquanto as consultas usam só `sqlite` | `sqlite`
`CNPJ_DB_ARQUIVO` | Arquivo SQLite usado quando não se passa `--base` | `saida/CNPJ_full.db`
`CNPJ_NAVEGADOR` | Navegador aberto sozinho com o `grafo.html` (`--viz`). Vazio: só gera o arquivo | `C:/Program Files/Google/Chrome/Application/chrome.exe`
`CNPJ_UID`, `CNPJ_GID` | Só Docker no Linux: usuário que roda o container (veja o [ambiente 4](#4-docker-com-volume-no-linux)) | `1000`
`FILES_LOCATION` | Só scripts `extra_csv`: pasta do `estabelecimento.csv`, terminando com `/` | `saida/`

Outros SGBDs (PostgreSQL etc.) ainda não são usados pelas consultas. Quando a carga multi-SGBD entrar, as variáveis de conexão (`CNPJ_DB_HOST`, `CNPJ_DB_PORTA`, `CNPJ_DB_NOME`, `CNPJ_DB_USUARIO`, `CNPJ_DB_SENHA`) serão acrescentadas ao `.env.example`.

Cuidados com o caminho do banco:

* **Prefira caminho relativo** (ex.: `saida/CNPJ_full.db`). O mesmo `.env` serve no Windows, no Linux e dentro do Docker, porque no Docker a pasta do projeto vira `/app` e o caminho relativo continua valendo.
* Caminho absoluto do Windows (`D:/dados/...`) **não existe dentro do container**. Se usar Docker, monte a pasta em `/dados` e use `CNPJ_DB_ARQUIVO=/dados/CNPJ_full.db` (veja o [ambiente 3](#3-docker-com-volume-no-windows)).
* No Windows, escreva o caminho com barras normais (`D:/dados/CNPJ_full.db`), sem aspas ou com aspas simples (`'D:\dados\CNPJ_full.db'`). **Não use aspas duplas com barra invertida**: em `"D:\dados\novo.db"` o `\n` vira uma quebra de linha.

# Roteiro de teste

Os mesmos três passos em todos os ambientes. Rode na raiz do projeto. Nos ambientes Docker, coloque `docker compose run --rm cnpj-full` antes de cada comando.

```bash
# 1. Consulta no banco de teste e grafo (abra resultado/grafo.html no navegador)
python cnpj_full/consulta.py cnpj 10000001000190 resultado --nivel 3 --viz --csv

# 2. Carga: gera os ZIPs de teste no formato da RF e carrega com o cnpj.py
python dados_teste/gerar_banco_teste.py --saida saida_teste/cnpj_teste.db --zips dados_zips
python cnpj_full/cnpj.py dados_zips sqlite saida_carga --dir

# 3. Consulta na base recém-carregada
python cnpj_full/consulta.py cnpj 20000001000143 resultado2 --base saida_carga/CNPJ_full.db --viz
```

O que conferir:

* o passo 1 termina com `Consulta finalizada` e gera `resultado/grafo.html`, `pessoas.csv` e `vinculos.csv`;
* o grafo abre no navegador mesmo sem internet (o d3.js vem embutido) e mostra a holding ligada às controladas;
* o passo 2 mostra a `Verificacao das quantidades por arquivo` com todos os arquivos `OK` e `Indices criados com sucesso`;
* no Docker, os arquivos aparecem na pasta do projeto no seu computador.

Os testes automáticos (`python -m pytest tests`) rodam a cada PR no GitHub Actions em Ubuntu e Windows (Python 3.13, a versão mínima) e no Docker, incluindo os comandos acima.

Para limpar depois: apague as pastas `resultado`, `resultado2`, `saida_teste`, `saida_carga` e `dados_zips`.

---

# 1. Somente Windows

Requisitos: **Python 3.13 ou superior** instalado pelo [python.org](https://www.python.org/downloads/windows/) (marque *Add python.exe to PATH* na instalação) e o [Git](https://git-scm.com/download/win).

No Windows o comando costuma ser `python` ou `py` (o *Python Launcher*), e não `python3`. Os exemplos abaixo usam PowerShell.

```powershell
git clone https://github.com/bjverde/CNPJ-full.git
cd CNPJ-full

# Ambiente virtual na pasta do projeto
py -m venv .venv
.venv\Scripts\Activate.ps1          # no cmd: .venv\Scripts\activate.bat
python -m pip install -r requirements.txt

# Teste
python cnpj_full/consulta.py cnpj 10000001000190 resultado --viz
start resultado\grafo.html          # abre no navegador padrão
```

Se o PowerShell recusar o `Activate.ps1` (*a execução de scripts foi desabilitada neste sistema*), libere só para o seu usuário e tente de novo:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Observações:

* As barras podem ser `/` ou `\` nos comandos (`cnpj_full/consulta.py` ou `cnpj_full\consulta.py`).
* Base completa em outro disco: `--base D:\dados\cnpj\CNPJ_full.db`, ou no `.env`: `CNPJ_DB_ARQUIVO=D:/dados/cnpj/CNPJ_full.db`.
* Para o navegador abrir sozinho, ponha no `.env`: `CNPJ_NAVEGADOR=C:/Program Files/Google/Chrome/Application/chrome.exe`.
* Para usar a mesma pasta também no Docker, a `.venv` criada aqui **não serve dentro do container** (é um venv do Windows). Não tem problema deixá-la na pasta: a imagem Docker não usa a `.venv`.

# 2. Somente Linux

Requisitos: Python 3.13 ou superior com o módulo `venv`. O Debian 13 já vem com o 3.13:

```bash
sudo apt install python3 python3-venv git
python3 --version    # precisa ser 3.13 ou superior
```

Distribuições com Python mais antigo (ex.: Ubuntu 24.04 vem com 3.12, Debian 12 com 3.11) precisam instalar o 3.13 à parte (ex.: `pyenv` ou, no Ubuntu, o PPA deadsnakes) e criar o ambiente virtual com ele (`python3.13 -m venv .venv`), ou usar o Docker.

No Debian 12/13 e no Ubuntu 23.04 ou mais novo, `pip install` direto no Python do sistema dá o erro *externally-managed-environment* (PEP 668). Use sempre o ambiente virtual:

```bash
git clone https://github.com/bjverde/CNPJ-full.git
cd CNPJ-full

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Teste
python cnpj_full/consulta.py cnpj 10000001000190 resultado --viz
xdg-open resultado/grafo.html       # ou abra o arquivo no navegador
```

Dentro do venv ativado, `python` e `python3` são o mesmo. Sem ativar, use o caminho completo: `.venv/bin/python cnpj_full/consulta.py ...` (útil em cron e scripts).

# 3. Docker com volume no Windows

Requisitos: [Docker Desktop](https://www.docker.com/products/docker-desktop/) para Windows (com WSL 2) e o Git. Não precisa de Python no Windows.

O [`Dockerfile`](../Dockerfile) cria uma imagem só com o Python 3.13 e as bibliotecas. O código **não é copiado para a imagem**: o [`docker-compose.yml`](../docker-compose.yml) monta a pasta do projeto em `/app` (bind mount). Assim os resultados aparecem na pasta do projeto no Windows e mudanças no código valem sem refazer a imagem.

No PowerShell, na pasta do projeto:

```powershell
git clone https://github.com/bjverde/CNPJ-full.git
cd CNPJ-full

docker compose build
docker compose run --rm cnpj-full python cnpj_full/consulta.py cnpj 10000001000190 resultado --viz
start resultado\grafo.html
```

Base completa em outra pasta do Windows: acrescente o volume no `docker-compose.yml` e aponte o `.env` para o caminho **dentro do container**:

```yaml
    volumes:
      - ./:/app
      - D:/dados/cnpj:/dados
```

```
CNPJ_DB_ARQUIVO=/dados/CNPJ_full.db
```

Observações:

* No Windows não é preciso definir `CNPJ_UID`/`CNPJ_GID`: o Docker Desktop já grava os arquivos como seu usuário.
* **Não crie venv dentro da pasta do projeto pelo container.** Um venv criado no volume do Windows fica sem `pip` funcionando (o container acaba usando o pip do sistema e dá *externally-managed-environment*). As bibliotecas já estão na imagem, fora do volume, e não precisam de venv.
* Desempenho: arquivos no disco do Windows acessados pelo container (`C:\...`, `D:\...`) são bem mais lentos que no Linux. Para o banco de teste não faz diferença. Para a **carga da base completa** (dezenas de GB), prefira deixar o projeto e os dados dentro do WSL (ex.: `\\wsl$\Ubuntu\home\voce\CNPJ-full`) e rodar a partir de lá, que é o [ambiente 4](#4-docker-com-volume-no-linux).
* O `.gitattributes` mantém `Dockerfile` e `*.yml` com quebra de linha LF mesmo clonando no Windows.

# 4. Docker com volume no Linux

Requisitos: Docker Engine com o plugin `docker compose` (ou Docker Desktop no Linux) e o Git. Vale também para o WSL 2 com a pasta do projeto dentro do Linux do WSL.

```bash
git clone https://github.com/bjverde/CNPJ-full.git
cd CNPJ-full

# Seu usuário no container, para os arquivos gerados não ficarem do root
printf 'CNPJ_UID=%s\nCNPJ_GID=%s\n' "$(id -u)" "$(id -g)" >> .env

docker compose build
docker compose run --rm cnpj-full python cnpj_full/consulta.py cnpj 10000001000190 resultado --viz
ls -l resultado                       # arquivos com o seu usuário
```

Base completa em outra pasta: acrescente `- /srv/dados/cnpj:/dados` em `volumes` no `docker-compose.yml` e use `CNPJ_DB_ARQUIVO=/dados/CNPJ_full.db` no `.env`.

Observações:

* Sem `CNPJ_UID`/`CNPJ_GID`, o container roda como root e os arquivos gerados no volume ficam do root (para apagar, só com `sudo`). A pasta do projeto precisa ser gravável pelo seu usuário.
* Em distribuições com SELinux ativo (Fedora, RHEL, Rocky), acrescente `:z` ao volume (`- ./:/app:z`) se aparecer *Permission denied* dentro do container.
* Sem compose, o equivalente é:

  ```bash
  docker build -t cnpj-full .
  docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/app -w /app cnpj-full \
      python cnpj_full/consulta.py cnpj 10000001000190 resultado --viz
  ```

---

# Usando outra imagem Docker (ex.: Debian 13 do cnpjrfb)

Se o CNPJ-full rodar dentro de uma imagem que não é a deste repositório (por exemplo a imagem Debian 13 + PHP do cnpjrfb), o Python é o do sistema e vale a PEP 668: `pip install` direto dá *externally-managed-environment*. Crie o venv **fora do volume**, num caminho da imagem, por exemplo `/opt/cnpj-full-venv`:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv \
 && python3 -m venv /opt/cnpj-full-venv
COPY requirements.txt /tmp/requirements.txt
RUN /opt/cnpj-full-venv/bin/pip install -r /tmp/requirements.txt
```

E rode com o Python do venv: `/opt/cnpj-full-venv/bin/python /caminho/CNPJ-full/cnpj_full/consulta.py ...`.

Não crie o venv dentro da pasta montada do host (principalmente no Windows): ele fica sem `pip` e quebra a cada recriação do container.

# Problemas comuns

Sintoma | Causa e solução
------- | ---------------
`can't open file '.../consulta.py': No such file or directory` | O código fica na pasta `cnpj_full/`. Use `python cnpj_full/consulta.py ...` a partir da raiz do projeto (ou o caminho completo de qualquer pasta).
`ERRO: banco SQLite nao encontrado: ...` | O caminho do banco está errado. Veja o caminho mostrado, a [ordem de escolha do banco](#arquivo-env-onde-fica-o-banco) e o `CNPJ_DB_ARQUIVO` do `.env`. Lembre que no `.env` o caminho relativo parte da raiz do projeto.
`no such table: estabelecimento` | O arquivo existe mas está vazio ou não é uma base do CNPJ-full (ex.: um `.db` vazio criado por engano, ou o banco de outro sistema). Confira o caminho e, se o arquivo estiver vazio, apague-o.
`error: externally-managed-environment` | `pip install` no Python do sistema (Debian 12/13, Ubuntu 23.04+). Use um venv ([Linux](#2-somente-linux)) ou, em Docker, a imagem deste repositório ou um venv em `/opt` ([outra imagem](#usando-outra-imagem-docker-ex-debian-13-do-cnpjrfb)).
`No module named pip` / venv sem pip | venv criado no volume do Windows por dentro do container. Apague a pasta do venv e use a imagem deste repositório (sem venv) ou um venv em `/opt`.
`No module named 'pandas'` (ou `networkx`) | Bibliotecas não instaladas no Python usado. Ative o venv (`source .venv/bin/activate` ou `.venv\Scripts\Activate.ps1`) e rode `pip install -r requirements.txt`.
`python3` não encontrado no Windows | No Windows use `python` ou `py`.
Arquivos do `resultado` pertencem ao root (Linux) | Defina `CNPJ_UID` e `CNPJ_GID` no `.env` ([ambiente 4](#4-docker-com-volume-no-linux)).
`Permission denied` ao gravar no volume (Linux) | A pasta do projeto não é gravável pelo usuário do container, ou SELinux: use `:z` no volume.
Caminho do Windows no `.env` com caractere estranho | Aspas duplas com `\`. Use barras normais `D:/dados/x.db` ou aspas simples.
O grafo abre em branco | Abra o `grafo.html` direto do disco num navegador atual (Chrome, Edge, Firefox). Ele não precisa de internet nem de servidor web.
