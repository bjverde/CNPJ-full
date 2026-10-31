[← Voltar ao README](../README.md)

# Estrutura do projeto

```
cnpj_full/              Código Python
  cnpj.py               Carga dos arquivos da RF para SQLite ou CSV
  consulta.py           Consultas por linha de comando e geração do grafo
  rede_cnpj.py          Classe RedeCNPJ (navegação no banco e montagem do grafo)
  config.py             Configurações das consultas
  viz/template.html     Template da visualização interativa (d3.js)
  extra_csv/            Scripts para separar o estabelecimento.csv por UF ou município
docs/                   Documentação
  carga.md              Download dos arquivos e carga
  consultas.md          Consultas, grafo e CPF/LGPD
  desenvolvimento.md    Estrutura, testes e roteiro
  cnpj-metadados.pdf    Dicionário de dados da Receita Federal
  img/                  Imagens da documentação
tests/                  Testes automáticos (pytest) e amostra sintética
.github/workflows/      GitHub Actions (roda os testes a cada PR)
```

Os scripts podem ser rodados de qualquer pasta, como arquivo (`python3 cnpj_full/cnpj.py ...`) ou como módulo a partir da raiz do projeto (`python3 -m cnpj_full.cnpj ...`).

# Testes

Os testes usam uma amostra sintética no formato oficial da RF (`tests/amostra.py`) e cobrem a carga, a verificação das quantidades, a retomada com `--continuar` e as consultas do grafo. Eles rodam no GitHub Actions a cada PR. Para rodar localmente:

```bash
pip install pytest
python3 -m pytest tests
```

Para gerar só a amostra (útil para experimentar sem baixar os arquivos da RF):

```bash
python3 tests/amostra.py amostra
python3 cnpj_full/cnpj.py amostra sqlite saida_amostra --dir
python3 cnpj_full/consulta.py cnpj 11111111000272 resultado --base saida_amostra/CNPJ_full.db --viz
```

# Roteiro

Melhorias planejadas:

* Script para baixar automaticamente os ZIPs da competência mais recente.
* Tabela própria para os CNAEs secundários (uma linha por CNAE), para buscar empresas por atividade secundária.
* Carga direta em MySQL/MariaDB e PostgreSQL, usando os modelos do cnpjrfb.
* Trocar a leitura manual de argumentos por `argparse`.
* Atualizar o d3.js da visualização (hoje na versão 4).
* Tabela de tempo e tamanho da carga completa, a partir de uma carga real.
