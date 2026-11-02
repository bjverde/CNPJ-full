import os
import json

import pytest

from cnpj_full import config, consulta


@pytest.fixture
def caminho_bd(banco):
    return banco.execute('PRAGMA database_list').fetchone()[2]


def roda(caminho_bd, saida, cnpj='11111111000272', nivel=3, cache=True, **saidas):
    saidas = saidas or {'viz': True, 'csv': True}
    return consulta.consulta('cnpj', cnpj, config.QUALIFICACOES, caminho_bd, nivel, saida,
                             colunas_csv=config.COLUNAS_CSV, csv_sep=config.SEP_CSV,
                             cache=cache, **saidas)


def proibe_consulta_no_banco(monkeypatch):
    def falha(*args, **kwargs):
        raise AssertionError('consultou o banco mesmo com o cache valido')
    monkeypatch.setattr(consulta, 'RedeCNPJ', falha)


def test_mesma_consulta_usa_o_cache(caminho_bd, tmp_path, monkeypatch):
    saida = str(tmp_path / 'grafo')
    assert roda(caminho_bd, saida) is False
    with open(os.path.join(saida, 'cache.json'), encoding='utf-8') as f:
        gravado = json.load(f)
    assert gravado['chave']['nivel'] == 3
    assert gravado['chave']['objeto_consulta'] == '11111111000272'
    assert gravado['chave']['base'].startswith('carga:')
    assert sorted(gravado['arquivos']) == ['grafo.html', 'pessoas.csv', 'vinculos.csv']

    mtime = os.path.getmtime(os.path.join(saida, 'grafo.html'))
    proibe_consulta_no_banco(monkeypatch)
    # CNPJ com mascara e a mesma consulta
    assert roda(caminho_bd, saida, cnpj='11.111.111/0002-72') is True
    assert os.path.getmtime(os.path.join(saida, 'grafo.html')) == mtime


def test_outro_nivel_refaz(caminho_bd, tmp_path):
    saida = str(tmp_path / 'grafo')
    roda(caminho_bd, saida, nivel=3)
    assert roda(caminho_bd, saida, nivel=1) is False
    assert roda(caminho_bd, saida, nivel=1) is True


def test_outras_saidas_refaz(caminho_bd, tmp_path):
    saida = str(tmp_path / 'grafo')
    roda(caminho_bd, saida, viz=True, csv=True)
    assert roda(caminho_bd, saida, viz=True) is False
    # o CSV da consulta anterior nao fica misturado com o resultado novo
    assert not os.path.exists(os.path.join(saida, 'pessoas.csv'))


def test_nova_carga_da_base_refaz(banco, caminho_bd, tmp_path):
    saida = str(tmp_path / 'grafo')
    roda(caminho_bd, saida)
    banco.execute("UPDATE controle_carga SET fim = '2099-01-01 00:00:00'")
    banco.commit()
    assert roda(caminho_bd, saida) is False


def test_arquivo_apagado_refaz(caminho_bd, tmp_path):
    saida = str(tmp_path / 'grafo')
    roda(caminho_bd, saida)
    os.remove(os.path.join(saida, 'grafo.html'))
    assert roda(caminho_bd, saida) is False
    assert os.path.exists(os.path.join(saida, 'grafo.html'))


def test_sem_cache_sempre_refaz(caminho_bd, tmp_path):
    saida = str(tmp_path / 'grafo')
    roda(caminho_bd, saida, cache=False)
    assert not os.path.exists(os.path.join(saida, 'cache.json'))
    assert roda(caminho_bd, saida, cache=False) is False


def test_base_sem_controle_carga_usa_o_arquivo(banco, caminho_bd, tmp_path):
    banco.execute('DROP TABLE controle_carga')
    banco.commit()
    saida = str(tmp_path / 'grafo')
    roda(caminho_bd, saida)
    with open(os.path.join(saida, 'cache.json'), encoding='utf-8') as f:
        assert json.load(f)['chave']['base'].startswith('arquivo:')
    assert roda(caminho_bd, saida) is True


def test_base_inexistente_nao_cria_arquivo(tmp_path):
    caminho = str(tmp_path / 'nao_existe.db')
    assert roda(caminho, str(tmp_path / 'grafo')) is False
    assert not os.path.exists(caminho)
