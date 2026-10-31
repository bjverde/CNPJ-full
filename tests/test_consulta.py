import os
import json

import pandas as pd
import pytest

from cnpj_full import config, consulta
from cnpj_full.rede_cnpj import RedeCNPJ


@pytest.fixture
def rede(banco):
    return RedeCNPJ(banco, nivel_max=3, qualificacoes=config.QUALIFICACOES)


def test_filial_liga_na_matriz(rede):
    rede.insere_pessoa(1, '11111111000272')
    G = rede.G
    assert G.has_edge('11111111000272', '11111111000191')
    assert G.edges['11111111000272', '11111111000191']['tipo'] == 'filial'
    assert G.nodes['11111111000272']['nivel'] == 0
    assert G.nodes['11111111000191']['nome'] == 'ALFA'
    assert G.nodes['11111111000191']['municipio_descricao'] == 'BRASILIA'


def test_socios_da_matriz(rede):
    rede.insere_pessoa(1, '11111111000191')
    G = rede.G
    # socio PF (com apostrofo no nome) e socio PJ
    assert G.has_edge("***123456**JOAO D'AVILA", '11111111000191')
    assert G.edges["***123456**JOAO D'AVILA", '11111111000191']['qualificacao'] == 'Sócio-Administrador'
    assert G.has_edge('22222222000130', '11111111000191')
    # socio estrangeiro da BETA, no nivel seguinte
    assert G.has_edge('JOHN SMITH', '22222222000130')
    assert G.nodes['JOHN SMITH']['tipo_pessoa'] == 3


def test_nome_fantasia_nao_possui(rede):
    rede.insere_pessoa(1, '33333333000147')
    assert rede.G.nodes['33333333000147']['nome'] == 'GAMA COMÉRCIO EIRELI'


def test_busca_por_nome_e_cpf(rede):
    rede.insere_com_cpf_ou_nome(nome="JOAO D'AVILA")
    empresas = set(rede.G.successors("***123456**JOAO D'AVILA"))
    assert empresas == {'11111111000191', '33333333000147'}

    outra = RedeCNPJ(rede._RedeCNPJ__conBD, nivel_max=1)
    outra.insere_com_cpf_ou_nome(cpf=consulta.mascara_cpf('00012345600'))
    assert "***123456**JOAO D'AVILA" in outra.G


def test_empresa_inexistente(rede):
    with pytest.raises(KeyError):
        rede.insere_pessoa(1, '99999999000100')


def test_consulta_gera_saidas(zips, banco, tmp_path, monkeypatch):
    # roda de outra pasta para garantir que o template e achado pelo caminho do modulo
    monkeypatch.chdir(str(tmp_path))
    caminho_bd = banco.execute('PRAGMA database_list').fetchone()[2]
    saida = str(tmp_path / 'resultado')

    consulta.consulta('cnpj', '11.111.111/0002-72', config.QUALIFICACOES, caminho_bd, 3, saida,
                      csv=True, colunas_csv=config.COLUNAS_CSV, csv_sep=config.SEP_CSV,
                      graphml=True, gexf=True, viz=True)

    for arquivo in ['pessoas.csv', 'vinculos.csv', 'rede.graphml', 'rede.gexf', 'grafo.html']:
        assert os.path.exists(os.path.join(saida, arquivo)), arquivo

    pessoas = pd.read_csv(os.path.join(saida, 'pessoas.csv'), sep=config.SEP_CSV, dtype=str)
    assert list(pessoas.columns) == ['id'] + config.COLUNAS_CSV
    assert len(pessoas) == 7

    with open(os.path.join(saida, 'grafo.html'), encoding='utf-8') as f:
        html = f.read()
    inicio = html.index('<script type="application/json" id="grafo">') + len('<script type="application/json" id="grafo">')
    grafo = json.loads(html[inicio:html.index('</script>', inicio)])
    assert 'links' in grafo and len(grafo['links']) == 6
