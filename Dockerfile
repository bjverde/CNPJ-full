# Imagem para rodar o CNPJ-full (carga, consultas e grafo) em Docker.
#
# O codigo NAO e copiado para a imagem: ele entra pelo volume (bind mount) da
# pasta do projeto em /app (veja docker-compose.yml e docs/ambientes.md).
# Assim a mesma imagem serve para Docker no Windows e no Linux, e alteracoes
# no codigo valem sem rebuild. A imagem so tem o Python e as bibliotecas.
#
# As bibliotecas ficam instaladas na imagem (fora do volume). Nao crie a .venv
# dentro do volume: venv criada no Windows nao funciona no Linux do container.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt

WORKDIR /app

# Sem argumentos, mostra a ajuda da consulta
CMD ["python", "cnpj_full/consulta.py"]
