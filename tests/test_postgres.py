# -*- encoding: utf-8 -*-
'''Testes da carga no PostgreSQL.

Precisam de um PostgreSQL de teste. Sao pulados se CNPJ_TESTE_PG_HOST nao
estiver definido. Exemplo (com Docker):

    docker run -d --name pg-teste -e POSTGRES_PASSWORD=teste -p 5432:5432 postgres:16
    CNPJ_TESTE_PG_HOST=localhost CNPJ_TESTE_PG_SENHA=teste python -m pytest tests/test_postgres.py

Cada teste usa um schema proprio, apagado no fim.
'''
import os
import uuid
import datetime
from decimal import Decimal

import pytest

from cnpj_full import cnpj

psycopg = pytest.importorskip('psycopg')

HOST = os.getenv('CNPJ_TESTE_PG_HOST')
pytestmark = pytest.mark.skipif(not HOST, reason='CNPJ_TESTE_PG_HOST nao definido')


def config(schema):
    return {
        'host': HOST,
        'porta': os.getenv('CNPJ_TESTE_PG_PORTA') or '5432',
        'nome': os.getenv('CNPJ_TESTE_PG_NOME') or 'cnpj_teste',
        'usuario': os.getenv('CNPJ_TESTE_PG_USUARIO') or 'postgres',
        'senha': os.getenv('CNPJ_TESTE_PG_SENHA') or '',
        'schema': schema,
    }


@pytest.fixture
def schema():
    nome = 'teste_' + uuid.uuid4().hex[:8]
    yield nome
    c = config(nome)
    with psycopg.connect(host=c['host'], port=int(c['porta']), dbname=c['nome'],
                         user=c['usuario'], password=c['senha'] or None, autocommit=True) as con:
        con.execute('DROP SCHEMA IF EXISTS {} CASCADE'.format(nome))


def carrega_pg(zips, schema, continuar=False, indices=True):
    from cnpj_full.sgbd import postgres
    entrada = sorted(os.path.join(zips, f) for f in os.listdir(zips) if f.endswith('.zip'))
    cnpj.cnpj_full(entrada, 'postgres', continuar=continuar,
                   destino=postgres.Destino(config(schema)))
    if indices:
        cnpj.cnpj_index_sgbd('postgres', destino=postgres.Destino(config(schema)))


@pytest.fixture
def con(schema):
    c = config(schema)
    con = psycopg.connect(host=c['host'], port=int(c['porta']), dbname=c['nome'],
                          user=c['usuario'], password=c['senha'] or None)
    yield con
    con.close()


def um(con, sql, *args):
    with con.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchone()


def test_carga_quantidades_e_tipos(zips, schema, con):
    carrega_pg(zips, schema)
    s = schema
    assert um(con, 'SELECT COUNT(*) FROM {}.empresa'.format(s))[0] == 4
    assert um(con, 'SELECT COUNT(*) FROM {}.estabelecimento'.format(s))[0] == 5
    assert um(con, 'SELECT COUNT(*) FROM {}.socios'.format(s))[0] == 6
    assert um(con, 'SELECT COUNT(*) FROM {}.cnae'.format(s))[0] == 5

    capital, porte = um(con, "SELECT capital_social, porte_empresa FROM {}.empresa "
                             "WHERE cnpj_basico = '22222222'".format(s))
    assert capital == Decimal('5000000.50')
    assert porte == '05'

    situacao, data, especial = um(con, "SELECT situacao_cadastral, data_situacao_cadastral, "
                                       "data_situacao_especial FROM {}.estabelecimento "
                                       "WHERE cnpj_basico = '11111111' AND cnpj_ordem = '0001'".format(s))
    assert situacao == '02'
    assert data == datetime.date(2020, 1, 1)
    assert especial is None

    # Join de dominio com codigo inteiro
    assert um(con, 'SELECT COUNT(*) FROM {0}.estabelecimento e JOIN {0}.munic m '
                   'ON m.codigo = e.municipio'.format(s))[0] >= 4

    # Representante legal inexistente vira NULL; socios tem id gerado
    assert um(con, 'SELECT COUNT(*) FROM {}.socios WHERE representante_legal IS NULL'.format(s))[0] >= 1
    assert um(con, 'SELECT MIN(id), MAX(id) FROM {}.socios'.format(s)) == (1, 6)


def test_controle_carga_e_indices(zips, schema, con):
    carrega_pg(zips, schema)
    assert um(con, "SELECT COUNT(*) FROM {}.controle_carga WHERE status = 'OK'".format(schema))[0] == 13
    assert um(con, "SELECT COUNT(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace "
                   "WHERE n.nspname = %s AND c.contype = 'p'", schema)[0] == 10
    assert um(con, "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = %s AND indexname = 'ix_socios_cpf_cnpj'",
              schema)[0] == 1


def test_interrupcao_e_continuar(zips, schema, con, monkeypatch):
    original = cnpj.le_arquivo

    def le_arquivo_falha(tabela, caminho, membro, estatisticas=None):
        for bloco in original(tabela, caminho, membro, estatisticas):
            yield bloco
            if tabela == cnpj.SOCIOS:
                raise KeyboardInterrupt('interrupcao simulada')

    monkeypatch.setattr(cnpj, 'le_arquivo', le_arquivo_falha)
    with pytest.raises(KeyboardInterrupt):
        carrega_pg(zips, schema, indices=False)
    monkeypatch.setattr(cnpj, 'le_arquivo', original)

    # O arquivo interrompido foi desfeito
    assert um(con, 'SELECT COUNT(*) FROM {}.socios'.format(schema))[0] == 0
    con.commit()

    carrega_pg(zips, schema, continuar=True)
    assert um(con, 'SELECT COUNT(*) FROM {}.socios'.format(schema))[0] == 6
    assert um(con, 'SELECT COUNT(*) FROM {}.empresa'.format(schema))[0] == 4
    assert um(con, "SELECT COUNT(*) FROM {}.controle_carga WHERE status = 'OK'".format(schema))[0] == 13


def test_continuar_sem_carga_anterior(zips, schema):
    with pytest.raises(SystemExit):
        carrega_pg(zips, schema, continuar=True)


def test_valores_invalidos_viram_null():
    import pandas as pd
    from cnpj_full.sgbd.postgres import Destino
    df = pd.DataFrame({
        'cnpj_basico': ['1', '2'], 'opcao_pelo_simples': ['S', 'N'],
        'data_opcao_simples': ['20241399', '20240131'], 'data_exclusao_simples': [None, None],
        'opcao_mei': ['N', 'N'], 'data_opcao_mei': [None, None], 'data_exclusao_mei': [None, None]})
    df = Destino.prepara_bloco(cnpj.SIMPLES, df)
    assert pd.isna(df['data_opcao_simples'][0])
    assert df['data_opcao_simples'][1] == '2024-01-31'
