# -*- encoding: utf-8 -*-
'''
Gera uma amostra sintetica dos arquivos de dados abertos do CNPJ da RF,
no mesmo formato dos arquivos oficiais: ZIPs com um CSV sem cabecalho,
separado por ";", campos entre aspas e encoding latin-1.

A amostra cobre: matriz e filial, empresa sem nome fantasia ("NAO POSSUI"),
socio PF, socio PJ, socio estrangeiro, socio PJ que nao existe na base,
nome com apostrofo, acentos, datas zeradas e capital social com virgula.
'''
import os
import zipfile


def _zip(pasta, nome_zip, nome_csv, linhas, extra=b''):
    dados = ''.join(';'.join('"{}"'.format(v) for v in linha) + '\n' for linha in linhas)
    with zipfile.ZipFile(os.path.join(pasta, nome_zip), 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(nome_csv, dados.encode('latin-1') + extra)


def _estabelecimento(basico, ordem, dv, matriz_filial, fantasia, situacao, municipio, cnae, secundarias=''):
    return [basico, ordem, dv, matriz_filial, fantasia, situacao, '20200101', '00', '', '',
            '20100515', cnae, secundarias, 'RUA', 'DAS FLORES', '10', 'SALA 1', 'CENTRO',
            '70000000', 'DF', municipio, '61', '12345678', '', '', '', '', 'contato@x.com.br', '', '']


def gera_amostra(pasta, linhas_ruins=False):
    '''Cria os ZIPs da amostra em <pasta>. Com linhas_ruins=True, o arquivo
    Socios1 ganha uma linha com campo a mais (descartada) e um nome com
    quebra de linha dentro das aspas.'''
    os.makedirs(pasta, exist_ok=True)

    _zip(pasta, 'Empresas0.zip', 'K3241.K03200Y0.D40210.EMPRECSV', [
        ['11111111', 'EMPRESA ALFA LTDA', '2062', '49', '100000,00', '01', ''],
        ['22222222', 'BETA PARTICIPAÇÕES S.A.', '2054', '10', '5000000,50', '5', ''],
    ])
    _zip(pasta, 'Empresas1.zip', 'K3241.K03200Y1.D40210.EMPRECSV', [
        ['33333333', 'GAMA COMÉRCIO EIRELI', '2305', '65', '0,00', '03', ''],
        ['00394460', 'MUNICIPIO DE EXEMPLO', '1244', '10', '0,00', '05', 'EXEMPLO - SP'],
    ])
    _zip(pasta, 'Estabelecimentos0.zip', 'K3241.K03200Y0.D40210.ESTABELE', [
        _estabelecimento('11111111', '0001', '91', '1', 'ALFA', '02', '9701', '0111301', '6204000,6311900'),
        _estabelecimento('11111111', '0002', '72', '2', 'ALFA FILIAL', '08', '0001', '4711302'),
        _estabelecimento('22222222', '0001', '30', '1', '', '2', '9701', '6462000'),
    ])
    _zip(pasta, 'Estabelecimentos1.zip', 'K3241.K03200Y1.D40210.ESTABELE', [
        _estabelecimento('33333333', '0001', '47', '1', 'NAO POSSUI', '04', '7107', '4712100'),
        _estabelecimento('00394460', '0001', '11', '1', 'PREFEITURA', '02', '7107', '8411600'),
    ])
    _zip(pasta, 'Simples.zip', 'F.K03200$W.SIMPLES.CSV.D40210', [
        ['11111111', 'S', '20100515', '00000000', 'N', '00000000', '00000000'],
        ['33333333', 'S', '20150101', '0', 'S', '20150101', '0'],
    ])
    _zip(pasta, 'Socios0.zip', 'K3241.K03200Y0.D40210.SOCIOCSV', [
        ['11111111', '2', "JOAO D'AVILA", '***123456**', '49', '20100515', '', '***000000**', '', '00', '5'],
        ['11111111', '1', 'BETA PARTICIPAÇÕES S.A.', '22222222000130', '22', '20120101', '', '***000000**', '', '00', '0'],
        ['22222222', '2', 'MARIA SOUZA', '***654321**', '16', '20000101', '', '***000000**', '', '00', '6'],
        ['22222222', '3', 'JOHN SMITH', '', '37', '20050101', '249', '***111222**', 'PEDRO REPRESENTANTE', '17', '0'],
    ])

    extra = b''
    if linhas_ruins:
        extra = (b'"44444444";"2";"CAMPO A MAIS";"***111111**";"49";"20200101";"";"";"";"00";"5";"EXTRA"\n'
                 b'"44444444";"2";"NOME COM\nQUEBRA";"***222222**";"49";"20200101";"";"";"";"00";"5"\n')
    _zip(pasta, 'Socios1.zip', 'K3241.K03200Y1.D40210.SOCIOCSV', [
        ['33333333', '2', "JOAO D'AVILA", '***123456**', '65', '20150101', '', '***000000**', '', '00', '5'],
        ['33333333', '1', 'EMPRESA FORA DA BASE', '99999999000199', '22', '20150101', '', '***000000**', '', '00', '0'],
    ], extra)

    _zip(pasta, 'Cnaes.zip', 'F.K03200$Z.D40210.CNAECSV', [
        ['0111301', 'Cultivo de arroz'],
        ['4711302', 'Comércio varejista - supermercados'],
        ['6462000', 'Holdings de instituições não-financeiras'],
        ['4712100', 'Minimercados'],
        ['8411600', 'Administração pública em geral'],
    ])
    _zip(pasta, 'Motivos.zip', 'F.K03200$Z.D40210.MOTICSV', [
        ['00', 'SEM MOTIVO'], ['01', 'EXTINCAO POR ENCERRAMENTO LIQUIDACAO VOLUNTARIA']])
    _zip(pasta, 'Municipios.zip', 'F.K03200$Z.D40210.MUNICCSV', [
        ['0001', 'GUAJARA-MIRIM'], ['9701', 'BRASILIA'], ['7107', 'SAO PAULO']])
    _zip(pasta, 'Naturezas.zip', 'F.K03200$Z.D40210.NATJUCSV', [
        ['2062', 'Sociedade Empresária Limitada'], ['2054', 'Sociedade Anônima Fechada'],
        ['2305', 'EIRELI'], ['1244', 'Município']])
    _zip(pasta, 'Paises.zip', 'F.K03200$Z.D40210.PAISCSV', [['249', 'ESTADOS UNIDOS'], ['105', 'BRASIL']])
    _zip(pasta, 'Qualificacoes.zip', 'F.K03200$Z.D40210.QUALSCSV', [
        ['00', 'Não informada'], ['05', 'Administrador'], ['10', 'Diretor'], ['16', 'Presidente'],
        ['22', 'Sócio'], ['37', 'Sócio Pessoa Jurídica Domiciliado no Exterior'],
        ['49', 'Sócio-Administrador'], ['65', 'Titular Pessoa Física Residente ou Domiciliado no Brasil']])

    return pasta


if __name__ == '__main__':
    import sys
    destino = sys.argv[1] if len(sys.argv) > 1 else 'amostra'
    print('Amostra gerada em {}'.format(gera_amostra(destino)))
