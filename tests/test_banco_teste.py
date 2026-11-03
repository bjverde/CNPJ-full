'''Banco de teste versionado (dados_teste/cnpj_teste.db) e configuracao pelo .env.'''
import importlib
import os
import sqlite3
import subprocess
import sys

import pytest

from conftest import RAIZ
from cnpj_full import config, consulta
from cnpj_full.rede_cnpj import RedeCNPJ

sys.path.insert(0, os.path.join(RAIZ, 'dados_teste'))
import gerar_banco_teste  # noqa: E402

BANCO_TESTE = os.path.join(RAIZ, 'dados_teste', 'cnpj_teste.db')
HOLDING = '10000001000190'
BRAVO = '20000001000143'
TABELAS = ['empresa', 'estabelecimento', 'socios', 'simples',
           'cnae', 'moti', 'munic', 'natju', 'pais', 'quals']


def contagens(caminho):
    con = sqlite3.connect(caminho)
    try:
        return {t: con.execute('SELECT COUNT(*) FROM {}'.format(t)).fetchone()[0] for t in TABELAS}
    finally:
        con.close()


def test_cnpjs_do_roteiro_sao_validos():
    assert gerar_banco_teste.cnpj_completo('10000001') == HOLDING
    assert gerar_banco_teste.cnpj_completo('20000001') == BRAVO


def test_banco_versionado_igual_ao_gerador(tmp_path):
    '''Se o gerador mudar, o .db versionado tem que ser gerado de novo.'''
    novo = gerar_banco_teste.gera_banco(str(tmp_path / 'novo.db'))
    assert contagens(novo) == contagens(BANCO_TESTE)


def test_grafo_do_grupo_alfa():
    con = sqlite3.connect(BANCO_TESTE)
    try:
        rede = RedeCNPJ(con, nivel_max=3, qualificacoes=config.QUALIFICACOES)
        rede.insere_pessoa(1, HOLDING)
        G = rede.G
        # controladas da holding e a controlada da controlada
        for basico in ['10000002', '10000003', '10000004', '10000005', '10000006']:
            assert gerar_banco_teste.cnpj_completo(basico) in G
        assert G.has_edge('GLOBAL ALFA INVESTMENTS LLC', HOLDING)
        assert G.number_of_nodes() > 30
    finally:
        con.close()


def test_consulta_sem_base_usa_banco_teste(tmp_path):
    '''Sem --base e sem .env, o consulta.py usa o banco de teste, de qualquer pasta.'''
    env = dict(os.environ)
    env.pop('CNPJ_DB_ARQUIVO', None)
    saida = tmp_path / 'resultado'
    r = subprocess.run([sys.executable, os.path.join(RAIZ, 'cnpj_full', 'consulta.py'),
                        'cnpj', BRAVO, str(saida), '--viz', '--csv'],
                       cwd=str(tmp_path), env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    if not os.path.exists(os.path.join(RAIZ, '.env')):
        assert os.path.normcase(BANCO_TESTE) in os.path.normcase(r.stdout)
    for arquivo in ['grafo.html', 'pessoas.csv', 'vinculos.csv']:
        assert (saida / arquivo).is_file()


def test_consulta_no_banco_do_cnpjrfb(tmp_path):
    saida = tmp_path / 'resultado'
    consulta.consulta('cnpj', '00000007000103', config.QUALIFICACOES,
                      os.path.join(RAIZ, 'dados_teste', 'cnpjrfb.db'), 3, str(saida),
                      csv=True, colunas_csv=config.COLUNAS_CSV, csv_sep=config.SEP_CSV, viz=True)
    assert (saida / 'grafo.html').is_file()
    assert 'ADVOCACIA BERGANTIN' in (saida / 'pessoas.csv').read_text(encoding='utf-8')


def test_consulta_base_inexistente(tmp_path):
    env = dict(os.environ, CNPJ_DB_ARQUIVO=str(tmp_path / 'nao_existe.db'))
    r = subprocess.run([sys.executable, os.path.join(RAIZ, 'cnpj_full', 'consulta.py'),
                        'cnpj', BRAVO, str(tmp_path / 'r')],
                       env=env, capture_output=True, text=True)
    assert r.returncode != 0
    assert 'banco SQLite nao encontrado' in r.stdout
    assert not (tmp_path / 'nao_existe.db').exists()


@pytest.fixture
def config_recarregado(monkeypatch):
    def recarrega(valor):
        if valor is None:
            monkeypatch.delenv('CNPJ_DB_ARQUIVO', raising=False)
        else:
            monkeypatch.setenv('CNPJ_DB_ARQUIVO', valor)
        return importlib.reload(config)
    yield recarrega
    monkeypatch.undo()
    importlib.reload(config)


def test_caminho_relativo_do_env_parte_da_raiz(config_recarregado, tmp_path, monkeypatch):
    monkeypatch.chdir(str(tmp_path))
    cfg = config_recarregado(os.path.join('saida', 'CNPJ_full.db'))
    assert cfg.PATH_BD == os.path.join(RAIZ, 'saida', 'CNPJ_full.db')


def test_caminho_absoluto_do_env(config_recarregado, tmp_path):
    caminho = str(tmp_path / 'base.db')
    assert config_recarregado(caminho).PATH_BD == caminho
