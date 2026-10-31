# -*- encoding: utf-8 -*-
'''
Carga dos dados abertos do CNPJ da Receita Federal (layout a partir de 2021).

A RF disponibiliza os dados em varios arquivos ZIP, cada um contendo um CSV
sem cabecalho, separado por ";", com campos entre aspas e encoding latin-1:
    Empresas0..9.zip, Estabelecimentos0..9.zip, Socios0..9.zip, Simples.zip,
    Cnaes.zip, Motivos.zip, Municipios.zip, Naturezas.zip, Paises.zip,
    Qualificacoes.zip

Este script converte esses arquivos em um banco SQLite (ou em CSVs
tratados), usando a mesma nomenclatura de tabelas e colunas do modelo
de banco do projeto cnpjrfb (modelo_banco/sqlite/modelo_sqlite.sql).
'''
import os
import re
import glob
import sys
import csv
import zipfile
import datetime

import pandas as pd

# CONSTANTES PARA DEFINICAO CENTRALIZADA DA NOMENCLATURA A SER UTILIZADA
# Nomes das tabelas/arquivos
EMPRESA = 'empresa'
ESTABELECIMENTO = 'estabelecimento'
SIMPLES = 'simples'
SOCIOS = 'socios'
CNAE = 'cnae'
MOTIVO = 'moti'
MUNICIPIO = 'munic'
NATUREZA = 'natju'
PAIS = 'pais'
QUALIFICACAO = 'quals'

# Colunas de cada tabela, na ordem em que aparecem nos arquivos da RF,
# com o tipo usado na criacao da tabela no SQLite.
# Codigos de dominio sao INTEGER para que o join funcione mesmo quando
# um lado vem com zeros a esquerda e o outro nao (ex: "0001" x "1").
# Campos com zeros a esquerda significativos (cnpj, cpf, cep...) sao TEXT.
# Situacao cadastral e porte da empresa seguem o dicionario de dados da RF
# (codigos de 2 digitos, ex: "02", "05"), como no modelo do cnpjrfb.
COLUNAS = {
    EMPRESA: [
        ('cnpj_basico', 'TEXT'),
        ('razao_social', 'TEXT'),
        ('natureza_juridica', 'INTEGER'),
        ('qualificacao_responsavel', 'INTEGER'),
        ('capital_social', 'REAL'),
        ('porte_empresa', 'TEXT'),
        ('ente_federativo_responsavel', 'TEXT'),
    ],
    ESTABELECIMENTO: [
        ('cnpj_basico', 'TEXT'),
        ('cnpj_ordem', 'TEXT'),
        ('cnpj_dv', 'TEXT'),
        ('identificador_matriz_filial', 'INTEGER'),
        ('nome_fantasia', 'TEXT'),
        ('situacao_cadastral', 'TEXT'),
        ('data_situacao_cadastral', 'TEXT'),
        ('motivo_situacao_cadastral', 'INTEGER'),
        ('nome_cidade_exterior', 'TEXT'),
        ('pais', 'INTEGER'),
        ('data_inicio_atividade', 'TEXT'),
        ('cnae_fiscal_principal', 'INTEGER'),
        ('cnae_fiscal_secundaria', 'TEXT'),
        ('tipo_logradouro', 'TEXT'),
        ('logradouro', 'TEXT'),
        ('numero', 'TEXT'),
        ('complemento', 'TEXT'),
        ('bairro', 'TEXT'),
        ('cep', 'TEXT'),
        ('uf', 'TEXT'),
        ('municipio', 'INTEGER'),
        ('ddd_1', 'TEXT'),
        ('telefone_1', 'TEXT'),
        ('ddd_2', 'TEXT'),
        ('telefone_2', 'TEXT'),
        ('ddd_fax', 'TEXT'),
        ('fax', 'TEXT'),
        ('correio_eletronico', 'TEXT'),
        ('situacao_especial', 'TEXT'),
        ('data_situacao_especial', 'TEXT'),
    ],
    SIMPLES: [
        ('cnpj_basico', 'TEXT'),
        ('opcao_pelo_simples', 'TEXT'),
        ('data_opcao_simples', 'TEXT'),
        ('data_exclusao_simples', 'TEXT'),
        ('opcao_mei', 'TEXT'),
        ('data_opcao_mei', 'TEXT'),
        ('data_exclusao_mei', 'TEXT'),
    ],
    SOCIOS: [
        ('cnpj_basico', 'TEXT'),
        ('identificador_socio', 'INTEGER'),
        ('nome_socio_razao_social', 'TEXT'),
        ('cpf_cnpj_socio', 'TEXT'),
        ('qualificacao_socio', 'INTEGER'),
        ('data_entrada_sociedade', 'TEXT'),
        ('pais', 'INTEGER'),
        ('representante_legal', 'TEXT'),
        ('nome_do_representante', 'TEXT'),
        ('qualificacao_representante_legal', 'INTEGER'),
        ('faixa_etaria', 'INTEGER'),
    ],
}

COLUNAS_DOMINIO = [('codigo', 'INTEGER'), ('descricao', 'TEXT')]
for _tabela in [CNAE, MOTIVO, MUNICIPIO, NATUREZA, PAIS, QUALIFICACAO]:
    COLUNAS[_tabela] = COLUNAS_DOMINIO

# Identificacao do tipo de arquivo. Primeiro pelo nome do arquivo dentro do
# zip (ex: K3241.K03200Y0.D40210.EMPRECSV), depois pelo nome do zip
# (ex: Empresas0.zip). A ordem importa.
PADROES_ARQUIVO = [
    (ESTABELECIMENTO, r'ESTABELE'),
    (EMPRESA, r'EMPRE'),
    (SOCIOS, r'SOCIO'),
    (SIMPLES, r'SIMPLES'),
    (CNAE, r'CNAE'),
    (MOTIVO, r'MOTI'),
    (MUNICIPIO, r'MUNIC'),
    (NATUREZA, r'NATJU|NATUREZA'),
    (PAIS, r'PAIS'),
    (QUALIFICACAO, r'QUALS|QUALIFICA'),
]

# Ordem de processamento (tabelas de dominio primeiro, por serem pequenas)
ORDEM_TABELAS = [CNAE, MOTIVO, MUNICIPIO, NATUREZA, PAIS, QUALIFICACAO,
                 EMPRESA, ESTABELECIMENTO, SIMPLES, SOCIOS]

COLUNAS_DATA = {
    ESTABELECIMENTO: ['data_situacao_cadastral', 'data_inicio_atividade',
                      'data_situacao_especial'],
    SIMPLES: ['data_opcao_simples', 'data_exclusao_simples',
              'data_opcao_mei', 'data_exclusao_mei'],
    SOCIOS: ['data_entrada_sociedade'],
}

# (<nome_do_indice>,<tabela>,<coluna(s)>)
INDICES = [
    ('empresa_cnpj_basico', EMPRESA, 'cnpj_basico'),
    ('estabelecimento_cnpj', ESTABELECIMENTO, 'cnpj_basico, cnpj_ordem, cnpj_dv'),
    ('simples_cnpj_basico', SIMPLES, 'cnpj_basico'),
    ('socios_cnpj_basico', SOCIOS, 'cnpj_basico'),
    ('socios_cpf_cnpj', SOCIOS, 'cpf_cnpj_socio'),
    ('socios_nome', SOCIOS, 'nome_socio_razao_social'),
] + [('{}_codigo'.format(t), t, 'codigo')
     for t in [CNAE, MOTIVO, MUNICIPIO, NATUREZA, PAIS, QUALIFICACAO]]

PREFIXO_INDICE = 'ix_'

CHUNKSIZE = 200000

ENCODING = 'latin-1'

NOME_ARQUIVO_SQLITE = 'CNPJ_full.db'

# Modos de gravacao do SQLite durante a carga e a criacao de indices.
#
# Rapido (padrao): sem journal e sem sync em disco. A gravacao fica bem mais
# rapida, mas se o processo for interrompido (queda de energia, Ctrl+C, erro)
# o arquivo pode ficar corrompido, e a carga precisa ser refeita do zero.
#
# Seguro (--seguro): modo normal do SQLite, com journal e sync em disco.
# Mais lento, mas uma interrupcao desfaz apenas o arquivo que estava sendo
# gravado, e a carga pode ser retomada com --continuar.
#
# Em ambos os modos, cada arquivo da RF e gravado em uma unica transacao e
# registrado na tabela de controle ao terminar.
PRAGMAS_COMUNS = [
    'cache_size = -262144',  # 256 MB de cache de paginas
]
PRAGMAS_RAPIDO = [
    'journal_mode = OFF',
    'synchronous = OFF',
    'locking_mode = EXCLUSIVE',
]
PRAGMAS_SEGURO = [
    'journal_mode = DELETE',
    'synchronous = FULL',
]

MODO_RAPIDO = 'rapido'
MODO_SEGURO = 'seguro'

# Tabela com os arquivos ja carregados, usada pelo --continuar
CONTROLE = 'controle_carga'


def conecta_sqlite(output_path, modo=MODO_RAPIDO):
    import sqlite3
    # isolation_level=None: as transacoes sao controladas explicitamente
    conBD = sqlite3.connect(os.path.join(output_path, NOME_ARQUIVO_SQLITE),
                            isolation_level=None)
    pragmas = PRAGMAS_COMUNS + (PRAGMAS_SEGURO if modo == MODO_SEGURO else PRAGMAS_RAPIDO)
    for pragma in pragmas:
        conBD.execute('PRAGMA ' + pragma)
    return conBD


def fecha_sqlite(conBD):
    # Volta o journal ao modo padrao para o uso normal do banco (consultas)
    conBD.execute('PRAGMA journal_mode = DELETE')
    conBD.close()


def identifica_tabela(nome):
    nome = os.path.basename(nome).upper()
    for tabela, padrao in PADROES_ARQUIVO:
        if re.search(padrao, nome):
            return tabela
    return None


def lista_arquivos(input_list):
    '''Retorna lista de (tabela, caminho, membro_zip) para cada arquivo de
    dados encontrado. membro_zip e None para arquivos ja descompactados.'''
    arquivos = []
    for caminho in input_list:
        if zipfile.is_zipfile(caminho):
            with zipfile.ZipFile(caminho) as zf:
                for membro in zf.namelist():
                    if membro.endswith('/'):
                        continue
                    tabela = identifica_tabela(membro) or identifica_tabela(caminho)
                    if tabela:
                        arquivos.append((tabela, caminho, membro))
                    else:
                        print('Arquivo ignorado (tipo nao identificado): {} [{}]'.format(caminho, membro))
        else:
            tabela = identifica_tabela(caminho)
            if tabela:
                arquivos.append((tabela, caminho, None))
            else:
                print('Arquivo ignorado (tipo nao identificado): {}'.format(caminho))

    arquivos.sort(key=lambda a: (ORDEM_TABELAS.index(a[0]), a[1], a[2] or ''))
    return arquivos


def le_arquivo(tabela, caminho, membro):
    '''Gerador de DataFrames (em blocos) de um arquivo da RF.'''
    nomes = [c[0] for c in COLUNAS[tabela]]

    if membro is None:
        handle = open(caminho, 'rb')
    else:
        zf = zipfile.ZipFile(caminho)
        handle = zf.open(membro)

    try:
        leitor = pd.read_csv(handle,
                             sep=';',
                             header=None,
                             names=nomes,
                             dtype=str,
                             quotechar='"',
                             keep_default_na=False,
                             na_values=[''],
                             encoding=ENCODING,
                             encoding_errors='replace',
                             on_bad_lines='warn',
                             chunksize=CHUNKSIZE)
        for bloco in leitor:
            yield trata_bloco(tabela, bloco)
    finally:
        handle.close()
        if membro is not None:
            zf.close()


def trata_bloco(tabela, df):
    # Remove espacos excedentes
    for col in df.columns:
        df[col] = df[col].str.strip()

    # Datas zeradas ("0" ou "00000000") viram vazio
    for col in COLUNAS_DATA.get(tabela, []):
        df[col] = df[col].mask(df[col].str.fullmatch(r'0*', na=False))

    if tabela == EMPRESA:
        # Capital social vem com virgula decimal (ex: "1000,00")
        df['capital_social'] = pd.to_numeric(
            df['capital_social'].str.replace(',', '.', regex=False),
            errors='coerce')

        # Porte com 2 digitos, como no dicionario de dados (00, 01, 03, 05)
        df['porte_empresa'] = df['porte_empresa'].str.zfill(2)

    elif tabela == ESTABELECIMENTO:
        # Situacao cadastral com 2 digitos (01, 02, 03, 04, 08)
        df['situacao_cadastral'] = df['situacao_cadastral'].str.zfill(2)

    elif tabela == SOCIOS:
        # Representante legal inexistente vem como cpf zerado
        sem_repres = df['representante_legal'].isin(['***000000**', '00000000000'])
        df['representante_legal'] = df['representante_legal'].mask(sem_repres)
        df['nome_do_representante'] = df['nome_do_representante'].mask(
            sem_repres | (df['nome_do_representante'] == 'CPF INVALIDO'))

    return df


def cria_tabelas_sqlite(conBD, tabelas):
    conBD.execute('BEGIN')
    for tabela in tabelas:
        colunas = ', '.join('{} {}'.format(nome, tipo) for nome, tipo in COLUNAS[tabela])
        conBD.execute('DROP TABLE IF EXISTS {}'.format(tabela))
        conBD.execute('CREATE TABLE {} ({})'.format(tabela, colunas))
    conBD.execute('DROP TABLE IF EXISTS {}'.format(CONTROLE))
    conBD.execute('''CREATE TABLE {} (
                        tabela TEXT,
                        arquivo TEXT,
                        membro TEXT,
                        modo TEXT,
                        registros INTEGER,
                        inicio TEXT,
                        fim TEXT)'''.format(CONTROLE))
    conBD.execute('COMMIT')


def id_arquivo(caminho, membro):
    # Identifica o arquivo pelo nome (sem a pasta), para que a carga possa
    # ser retomada mesmo se a pasta de entrada mudar de lugar.
    return os.path.basename(caminho), membro or ''


def prepara_continuacao(conBD, tabelas):
    '''Le a tabela de controle de uma carga anterior. Retorna o conjunto de
    arquivos ja concluidos e os totais de registros por tabela.'''
    existentes = set(r[0] for r in conBD.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"))

    if CONTROLE not in existentes:
        print(u'ERRO: Nao ha carga anterior para continuar neste banco. '
              u'Rode a carga sem --continuar.')
        sys.exit(-1)

    # Arquivo iniciado e nao concluido em modo rapido: nao ha como desfazer
    # a gravacao parcial, entao a carga precisa ser refeita do zero.
    incompletos = conBD.execute(
        'SELECT arquivo, membro, modo FROM {} WHERE fim IS NULL'.format(CONTROLE)).fetchall()
    for arquivo, membro, modo in incompletos:
        if modo != MODO_SEGURO:
            print(u'''ERRO: A carga anterior foi interrompida no arquivo {} [{}] no modo rapido.
Nesse modo a gravacao parcial nao pode ser desfeita e o banco pode estar
corrompido. Rode a carga do zero (sem --continuar), de preferencia com --seguro.'''.format(arquivo, membro))
            sys.exit(-1)

    # No modo seguro, o arquivo interrompido teve seus dados desfeitos pelo
    # SQLite; basta apagar o registro de controle e carregar de novo.
    conBD.execute('DELETE FROM {} WHERE fim IS NULL'.format(CONTROLE))

    for tabela in tabelas:
        if tabela not in existentes:
            colunas = ', '.join('{} {}'.format(nome, tipo) for nome, tipo in COLUNAS[tabela])
            conBD.execute('CREATE TABLE {} ({})'.format(tabela, colunas))

    concluidos = set()
    totais = {t: 0 for t in tabelas}
    for tabela, arquivo, membro, registros in conBD.execute(
            'SELECT tabela, arquivo, membro, registros FROM {}'.format(CONTROLE)):
        concluidos.add((arquivo, membro))
        if tabela in totais:
            totais[tabela] += registros

    return concluidos, totais


def grava_arquivo_sqlite(conBD, tabela, caminho, membro, modo, totais):
    arquivo, nome_membro = id_arquivo(caminho, membro)
    agora = lambda: datetime.datetime.now().isoformat(timespec='seconds')

    # Registra o inicio antes da transacao do arquivo, para saber depois
    # se ele foi interrompido no meio.
    conBD.execute('INSERT INTO {} (tabela, arquivo, membro, modo, inicio) '
                  'VALUES (?, ?, ?, ?, ?)'.format(CONTROLE),
                  (tabela, arquivo, nome_membro, modo, agora()))
    id_controle = conBD.execute('SELECT last_insert_rowid()').fetchone()[0]

    nomes = [c[0] for c in COLUNAS[tabela]]
    sql_insert = 'INSERT INTO {} ({}) VALUES ({})'.format(
        tabela, ', '.join(nomes), ', '.join('?' * len(nomes)))

    registros = 0
    conBD.execute('BEGIN')
    try:
        for i_bloco, df in enumerate(le_arquivo(tabela, caminho, membro)):
            linhas = df.astype(object).where(df.notna(), None).itertuples(index=False, name=None)
            conBD.executemany(sql_insert, linhas)

            registros += len(df)
            print('Bloco {}: {} registros de {} ate agora.'.format(
                i_bloco + 1, totais[tabela] + registros, tabela), end='\r')

        conBD.execute('UPDATE {} SET registros = ?, fim = ? WHERE rowid = ?'.format(CONTROLE),
                      (registros, agora(), id_controle))
        conBD.execute('COMMIT')
    except BaseException:
        # No modo rapido (sem journal) o SQLite nao consegue desfazer a
        # gravacao; o registro de controle fica sem "fim" e o --continuar
        # recusa retomar.
        if modo == MODO_SEGURO and conBD.in_transaction:
            conBD.execute('ROLLBACK')
        raise

    totais[tabela] += registros


def grava_arquivo_csv(output_path, tabela, caminho, membro, totais, csv_iniciados):
    nome_arquivo_csv = os.path.join(output_path, tabela + '.csv')
    for i_bloco, df in enumerate(le_arquivo(tabela, caminho, membro)):
        primeiro = tabela not in csv_iniciados
        df.to_csv(nome_arquivo_csv,
                  header=primeiro,
                  mode='w' if primeiro else 'a',
                  index=False,
                  quoting=csv.QUOTE_NONNUMERIC)
        csv_iniciados.add(tabela)

        totais[tabela] += len(df)
        print('Bloco {}: {} registros de {} ate agora.'.format(
            i_bloco + 1, totais[tabela], tabela), end='\r')


def cnpj_full(input_list, tipo_output, output_path, modo=MODO_RAPIDO, continuar=False):
    arquivos = lista_arquivos(input_list)

    if not arquivos:
        print(u'ERRO: Nenhum arquivo de dados da RF identificado.')
        sys.exit(-1)

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    tabelas = sorted(set(a[0] for a in arquivos), key=ORDEM_TABELAS.index)

    totais = {t: 0 for t in tabelas}
    concluidos = set()
    csv_iniciados = set()

    if tipo_output == 'sqlite':
        print(u'Modo de gravacao: {}'.format(modo))
        conBD = conecta_sqlite(output_path, modo)
        if continuar:
            concluidos, totais = prepara_continuacao(conBD, tabelas)
        else:
            cria_tabelas_sqlite(conBD, tabelas)

    for tabela, caminho, membro in arquivos:
        descricao = '{}{} -> {}'.format(caminho, ' [{}]'.format(membro) if membro else '', tabela)

        if id_arquivo(caminho, membro) in concluidos:
            print('Ja carregado, pulando: {}'.format(descricao))
            continue

        print('Processando arquivo: {}'.format(descricao))

        if tipo_output == 'csv':
            grava_arquivo_csv(output_path, tabela, caminho, membro, totais, csv_iniciados)
        elif tipo_output == 'sqlite':
            grava_arquivo_sqlite(conBD, tabela, caminho, membro, modo, totais)
        print()

    if tipo_output == 'sqlite':
        fecha_sqlite(conBD)

    print('\nConversao concluida. Total de registros por tabela:')
    for tabela in tabelas:
        print('  {}: {}'.format(tabela, totais[tabela]))

    if tipo_output == 'csv':
        print(u'Arquivos CSV gerados na pasta {}.'.format(output_path))

    elif tipo_output == 'sqlite':
        print(u'''
Arquivo SQLITE gerado: {}
OBS: Uso de índices altamente recomendado!
              '''.format(os.path.join(output_path, NOME_ARQUIVO_SQLITE)))


def cnpj_index(output_path, modo=MODO_RAPIDO):
    conBD = conecta_sqlite(output_path, modo)

    print(u'''
Criando índices...
Essa operaçao pode levar vários minutos.
    ''')

    cursorBD = conBD.cursor()
    tabelas_existentes = set(r[0] for r in cursorBD.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"))

    for nome, tabela, colunas in INDICES:
        if tabela not in tabelas_existentes:
            continue

        nome_indice = PREFIXO_INDICE + nome

        sql_stmt = 'CREATE INDEX IF NOT EXISTS {} ON {} ({});'.format(nome_indice, tabela, colunas)
        cursorBD.execute(sql_stmt)

        print(u'Index {} criado.'.format(nome_indice))

    print(u'Indices criados com sucesso.')

    fecha_sqlite(conBD)


def help():
    print('''
Uso: python cnpj.py <path_input> <output:csv|sqlite> <path_output> [--dir] [--noindex] [--seguro] [--continuar]
Argumentos opcionais:
 [--dir]: Indica que o <path_input> e uma pasta com os ZIPs (ou CSVs) da RF.
 [--noindex]: NAO gera indices automaticamente no sqlite ao final da carga.
 [--seguro]: Grava no modo normal do SQLite (com journal e sync em disco).
             Mais lento, mas uma interrupcao nao corrompe o banco e permite
             retomar a carga com --continuar. Sem ele, usa o modo rapido.
 [--continuar]: Retoma uma carga sqlite interrompida, pulando os arquivos
                ja concluidos. Use os mesmos arquivos de entrada.

Exemplos: python cnpj.py "data/Empresas0.zip" sqlite "output"
          python cnpj.py "data" sqlite "output" --dir
          python cnpj.py "data" sqlite "output" --dir --noindex
          python cnpj.py "data" csv "output" --dir
          python cnpj.py "data" sqlite "output" --dir --seguro
          python cnpj.py "data" sqlite "output" --dir --seguro --continuar
    ''')


def main():

    num_argv = len(sys.argv)
    if num_argv < 4:
        help()
        sys.exit(-1)
    else:
        input_path = sys.argv[1]
        tipo_output = sys.argv[2]
        output_path = sys.argv[3]

        gera_index = True
        modo = MODO_RAPIDO
        continuar = False
        input_list = [input_path]

        if num_argv > 4:
            for opcional in sys.argv[4:num_argv]:
                if (opcional == '--noindex'):
                    gera_index = False

                elif (opcional == '--seguro'):
                    modo = MODO_SEGURO

                elif (opcional == '--continuar'):
                    continuar = True

                elif (opcional == '--dir'):
                    input_list = glob.glob(os.path.join(input_path, '*.zip'))

                    if not input_list:
                        # caso nao ache zip, procura arquivos descompactados.
                        input_list = [f for f in glob.glob(os.path.join(input_path, '*'))
                                      if os.path.isfile(f) and identifica_tabela(f)]

                    if not input_list:
                        # caso nem assim ache, indica erro.
                        print(u'ERRO: Nenhum arquivo válido encontrado no diretório!')
                        sys.exit(-1)

                    input_list.sort()

                else:
                    print(u'ERRO: Argumento opcional inválido.')
                    help()
                    sys.exit(-1)

        if tipo_output not in ['csv', 'sqlite']:
            print('''
ERRO: tipo de output inválido.
Escolha um dos seguintes tipos de output: csv ou sqlite.
            ''')
            help()

        elif continuar and tipo_output != 'sqlite':
            print(u'ERRO: --continuar so pode ser usado com output sqlite.')
            sys.exit(-1)

        else:
            print('Iniciando processamento em {}'.format(datetime.datetime.now()))

            cnpj_full(input_list, tipo_output, output_path, modo, continuar)

            if (gera_index) and (tipo_output == 'sqlite'):
                cnpj_index(output_path, modo)

            print('Processamento concluido em {}'.format(datetime.datetime.now()))

if __name__ == "__main__":
    main()
