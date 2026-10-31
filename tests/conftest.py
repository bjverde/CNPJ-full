import os
import sys
import glob
import sqlite3

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cnpj  # noqa: E402
from amostra import gera_amostra  # noqa: E402


def carrega(pasta_zips, pasta_saida, tipo='sqlite', modo=cnpj.MODO_RAPIDO, continuar=False, indices=True):
    entrada = sorted(glob.glob(os.path.join(pasta_zips, '*.zip')))
    cnpj.cnpj_full(entrada, tipo, pasta_saida, modo, continuar)
    if indices and tipo == 'sqlite':
        cnpj.cnpj_index(pasta_saida, modo)
    return os.path.join(pasta_saida, cnpj.NOME_ARQUIVO_SQLITE)


@pytest.fixture
def zips(tmp_path):
    return gera_amostra(str(tmp_path / 'zips'))


@pytest.fixture
def banco(zips, tmp_path):
    caminho = carrega(zips, str(tmp_path / 'saida'))
    con = sqlite3.connect(caminho)
    yield con
    con.close()
