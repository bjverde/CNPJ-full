import os
import sqlite3

import pytest

from cnpj_full import cnpj, modelo

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TABELA_DA_CARGA = {
    'empresa': cnpj.EMPRESA, 'estabelecimento': cnpj.ESTABELECIMENTO, 'simples': cnpj.SIMPLES,
    'socios': cnpj.SOCIOS, 'cnae': cnpj.CNAE, 'moti': cnpj.MOTIVO, 'munic': cnpj.MUNICIPIO,
    'natju': cnpj.NATUREZA, 'pais': cnpj.PAIS, 'quals': cnpj.QUALIFICACAO,
}


def test_scripts_do_repositorio_estao_atualizados(tmp_path):
    # os .sql de modelo_banco/ tem que ser exatamente o que o gerador produz
    for gerado in modelo.gerar_arquivos(tmp_path):
        relativo = os.path.relpath(str(gerado), str(tmp_path))
        with open(os.path.join(RAIZ, 'modelo_banco', relativo), 'rb') as f:
            no_repositorio = f.read()
        with open(str(gerado), 'rb') as f:
            assert f.read() == no_repositorio, \
                '{} desatualizado: rode python3 cnpj_full/modelo.py'.format(relativo)


def test_modelo_tem_as_colunas_da_carga():
    # o modelo e a carga do CNPJ-full precisam ter as mesmas colunas, na mesma ordem
    for tabela in modelo.TABELAS:
        colunas = [c[0] for c in tabela['colunas'] if c[1] != 'id']
        chave = TABELA_DA_CARGA[tabela['nome']]
        da_carga = [c[0] for c in cnpj.COLUNAS.get(chave, cnpj.COLUNAS_DOMINIO)]
        assert colunas == da_carga, tabela['nome']


def test_script_sqlite_cria_as_tabelas():
    con = sqlite3.connect(':memory:')
    con.executescript(modelo.gerar_sqlite())
    tabelas = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {t['nome'] for t in modelo.TABELAS} <= tabelas


@pytest.mark.parametrize('sgbd', sorted(modelo.SGBDS))
def test_sgbd_na_tela(sgbd, capsys):
    modelo.main(['--sgbd', sgbd])
    assert 'CREATE TABLE' in capsys.readouterr().out


def test_fk_na_tela(capsys):
    modelo.main(['--sgbd', 'pgsql', '--fk'])
    assert 'FOREIGN KEY' in capsys.readouterr().out
