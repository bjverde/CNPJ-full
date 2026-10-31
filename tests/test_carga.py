import os
import sqlite3

import pandas as pd
import pytest

import cnpj
from amostra import gera_amostra
from conftest import carrega


def contagem(con, tabela):
    return con.execute('SELECT COUNT(*) FROM {}'.format(tabela)).fetchone()[0]


def test_identifica_tabela():
    assert cnpj.identifica_tabela('K3241.K03200Y0.D40210.EMPRECSV') == cnpj.EMPRESA
    assert cnpj.identifica_tabela('K3241.K03200Y0.D40210.ESTABELE') == cnpj.ESTABELECIMENTO
    assert cnpj.identifica_tabela('K3241.K03200Y0.D40210.SOCIOCSV') == cnpj.SOCIOS
    assert cnpj.identifica_tabela('F.K03200$W.SIMPLES.CSV.D40210') == cnpj.SIMPLES
    assert cnpj.identifica_tabela('F.K03200$Z.D40210.QUALSCSV') == cnpj.QUALIFICACAO
    assert cnpj.identifica_tabela('Estabelecimentos3.zip') == cnpj.ESTABELECIMENTO
    assert cnpj.identifica_tabela('Qualificacoes.zip') == cnpj.QUALIFICACAO
    assert cnpj.identifica_tabela('LEIAME.txt') is None


def test_quantidades(banco):
    esperado = {'empresa': 4, 'estabelecimento': 5, 'socios': 6, 'simples': 2,
                'cnae': 5, 'moti': 2, 'munic': 3, 'natju': 4, 'pais': 2, 'quals': 8}
    for tabela, qtd in esperado.items():
        assert contagem(banco, tabela) == qtd, tabela


def test_tratamentos(banco):
    capital, porte = banco.execute(
        "SELECT capital_social, porte_empresa FROM empresa WHERE cnpj_basico = '22222222'").fetchone()
    assert capital == 5000000.5
    # Porte e situacao com 2 digitos, como no dicionario de dados
    assert porte == '05'
    situacao = banco.execute(
        "SELECT situacao_cadastral FROM estabelecimento WHERE cnpj_basico = '22222222'").fetchone()[0]
    assert situacao == '02'

    # Codigos de dominio como inteiro (join independente de zeros a esquerda)
    municipio = banco.execute(
        "SELECT m.descricao FROM estabelecimento e JOIN munic m ON m.codigo = e.municipio "
        "WHERE e.cnpj_ordem = '0002'").fetchone()[0]
    assert municipio == 'GUAJARA-MIRIM'

    # Datas zeradas viram NULL
    simples = banco.execute(
        "SELECT data_exclusao_simples, data_opcao_mei FROM simples WHERE cnpj_basico = '11111111'").fetchone()
    assert simples == (None, None)

    # Representante legal inexistente vira NULL; existente e mantido
    repres = dict(banco.execute("SELECT nome_socio_razao_social, representante_legal FROM socios").fetchall())
    assert repres["JOAO D'AVILA"] is None
    assert repres['JOHN SMITH'] == '***111222**'

    # Acentos (latin-1) preservados
    assert banco.execute("SELECT razao_social FROM empresa WHERE cnpj_basico = '33333333'").fetchone()[0] \
        == 'GAMA COMÉRCIO EIRELI'


def test_indices(banco):
    indices = set(r[0] for r in banco.execute("SELECT name FROM sqlite_master WHERE type = 'index'"))
    for nome, _, _ in cnpj.INDICES:
        assert cnpj.PREFIXO_INDICE + nome in indices


def test_journal_volta_ao_normal(banco):
    assert banco.execute('PRAGMA journal_mode').fetchone()[0] == 'delete'


def test_controle_carga_ok(banco):
    linhas = banco.execute('SELECT status, registros_gravados, fim FROM controle_carga').fetchall()
    assert len(linhas) == 13
    assert all(status == 'OK' and fim for status, _, fim in linhas)
    assert sum(r for _, r, _ in linhas) == 41


def test_controle_carga_divergente(tmp_path):
    zips = gera_amostra(str(tmp_path / 'zips'), linhas_ruins=True)
    con = sqlite3.connect(carrega(zips, str(tmp_path / 'saida'), indices=False))
    linha = con.execute(
        "SELECT linhas_arquivo, registros_lidos, registros_descartados, registros_gravados, status "
        "FROM controle_carga WHERE arquivo = 'Socios1.zip'").fetchone()
    # 2 linhas boas + 1 descartada + 1 registro em 2 linhas fisicas = 5 linhas
    assert linha == (5, 3, 1, 3, 'DIVERGENTE')
    assert con.execute("SELECT COUNT(*) FROM controle_carga WHERE status = 'OK'").fetchone()[0] == 12


def test_saida_csv(zips, tmp_path):
    saida = str(tmp_path / 'csv')
    carrega(zips, saida, tipo='csv')
    empresa = pd.read_csv(os.path.join(saida, 'empresa.csv'), dtype=str)
    assert len(empresa) == 4
    assert list(empresa.columns) == [c[0] for c in cnpj.COLUNAS[cnpj.EMPRESA]]
    socios = pd.read_csv(os.path.join(saida, 'socios.csv'), dtype=str)
    assert len(socios) == 6


@pytest.mark.parametrize('modo', [cnpj.MODO_SEGURO, cnpj.MODO_RAPIDO])
def test_interrupcao_e_continuar(zips, tmp_path, monkeypatch, modo):
    saida = str(tmp_path / 'saida')
    original = cnpj.le_arquivo

    def le_arquivo_falha(tabela, caminho, membro, estatisticas=None):
        for bloco in original(tabela, caminho, membro, estatisticas):
            yield bloco
            if tabela == cnpj.SOCIOS:
                raise KeyboardInterrupt('interrupcao simulada')

    monkeypatch.setattr(cnpj, 'le_arquivo', le_arquivo_falha)
    with pytest.raises(KeyboardInterrupt):
        carrega(zips, saida, modo=modo, indices=False)
    monkeypatch.setattr(cnpj, 'le_arquivo', original)

    if modo == cnpj.MODO_RAPIDO:
        # No modo rapido nao ha como desfazer a gravacao parcial
        with pytest.raises(SystemExit):
            carrega(zips, saida, modo=modo, continuar=True)
        return

    con = sqlite3.connect(os.path.join(saida, cnpj.NOME_ARQUIVO_SQLITE))
    assert contagem(con, 'socios') == 0
    con.close()

    carrega(zips, saida, modo=modo, continuar=True)
    con = sqlite3.connect(os.path.join(saida, cnpj.NOME_ARQUIVO_SQLITE))
    assert contagem(con, 'socios') == 6
    assert contagem(con, 'empresa') == 4  # nao duplicou o que ja estava gravado
    assert con.execute("SELECT COUNT(*) FROM controle_carga WHERE status = 'OK'").fetchone()[0] == 13
    con.close()


def test_continuar_sem_carga_anterior(zips, tmp_path):
    with pytest.raises(SystemExit):
        carrega(zips, str(tmp_path / 'vazio'), continuar=True)
