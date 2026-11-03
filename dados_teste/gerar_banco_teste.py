# -*- encoding: utf-8 -*-
'''
Gera o banco de teste do CNPJ-full (dados_teste/cnpj_teste.db).

Todos os dados sao FICTICIOS: nomes de empresas e pessoas sao inventados e os
CPFs seguem o formato mascarado da RF (***999999**). So as tabelas de dominio
(CNAEs, municipios, naturezas juridicas, qualificacoes, paises e motivos) usam
codigos e descricoes reais.

O script:
  1. cria ZIPs no mesmo formato dos arquivos da Receita Federal (CSV sem
     cabecalho, separado por ";", campos entre aspas, encoding latin-1);
  2. carrega esses ZIPs com o proprio cnpj_full/cnpj.py (mesmo caminho da
     carga real) e cria os indices.

A geracao e deterministica (semente fixa): rodar de novo gera os mesmos dados.

Uso (a partir de qualquer pasta):
    python dados_teste/gerar_banco_teste.py                  # recria dados_teste/cnpj_teste.db
    python dados_teste/gerar_banco_teste.py --zips pasta     # tambem guarda os ZIPs em "pasta"
    python dados_teste/gerar_banco_teste.py --saida outro.db # grava em outro arquivo

Empresas para testar o grafo (CNPJ da matriz):
    10000001000190  ALFA HOLDING PARTICIPACOES S.A.  (grupo com controladas, socio estrangeiro e filiais)
    50000001000104  CHARLIE PARTICIPACOES S.A.       (cadeia holding > industria > distribuidora > logistica)
    60000001000168  PADARIA DELTA LTDA               (empresas de uma familia, ligadas por pessoas)
    20000001000143  BRAVO SERVICOS INTEGRADOS LTDA   (grupo menor, controlada de controlada)
'''
import os
import random
import shutil
import sys
import tempfile
import zipfile

PASTA = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(PASTA)
sys.path.insert(0, RAIZ)

from cnpj_full import cnpj  # noqa: E402

ARQUIVO_PADRAO = os.path.join(PASTA, 'cnpj_teste.db')
SEMENTE = 2026
PESSOAS_GRUPOS = 30  # pessoas reservadas para os grupos economicos
DATA_RF = 'D61011'  # sufixo dos nomes dos arquivos (so para imitar a RF)

# ---------------------------------------------------------------------------
# Tabelas de dominio (codigos reais da RF)
# ---------------------------------------------------------------------------
CNAES = [
    ('6462000', 'Holdings de instituições não-financeiras'),
    ('6204000', 'Consultoria em tecnologia da informação'),
    ('6311900', 'Tratamento de dados, provedores de serviços de aplicação e serviços de hospedagem na internet'),
    ('4711302', 'Comércio varejista de mercadorias em geral, com predominância de produtos alimentícios - supermercados'),
    ('4712100', 'Comércio varejista de mercadorias em geral, com predominância de produtos alimentícios - minimercados, mercearias e armazéns'),
    ('4120400', 'Construção de edifícios'),
    ('5611201', 'Restaurantes e similares'),
    ('4930202', 'Transporte rodoviário de carga, exceto produtos perigosos e mudanças, intermunicipal, interestadual e internacional'),
    ('6920601', 'Atividades de contabilidade'),
    ('8411600', 'Administração pública em geral'),
    ('4781400', 'Comércio varejista de artigos do vestuário e acessórios'),
    ('9602501', 'Cabeleireiros, manicure e pedicure'),
]
CNAES_COMUNS = [c for c, _ in CNAES if c not in ('6462000', '8411600')]

MUNICIPIOS = [  # codigo RF, nome, UF, CEP base
    ('9701', 'BRASILIA', 'DF', '70'),
    ('7107', 'SAO PAULO', 'SP', '01'),
    ('6001', 'RIO DE JANEIRO', 'RJ', '20'),
    ('4123', 'BELO HORIZONTE', 'MG', '30'),
]

NATUREZAS = [
    ('2062', 'Sociedade Empresária Limitada'),
    ('2054', 'Sociedade Anônima Fechada'),
    ('2135', 'Empresário (Individual)'),
    ('1244', 'Município'),
]

QUALIFICACOES = [
    ('00', 'Não informada'), ('05', 'Administrador'), ('10', 'Diretor'),
    ('16', 'Presidente'), ('17', 'Procurador'), ('22', 'Sócio'),
    ('37', 'Sócio Pessoa Jurídica Domiciliado no Exterior'),
    ('49', 'Sócio-Administrador'), ('50', 'Empresário'),
    ('65', 'Titular Pessoa Física Residente ou Domiciliado no Brasil'),
]

PAISES = [('105', 'BRASIL'), ('249', 'ESTADOS UNIDOS'), ('607', 'PORTUGAL')]

MOTIVOS = [('00', 'SEM MOTIVO'), ('01', 'EXTINCAO POR ENCERRAMENTO LIQUIDACAO VOLUNTARIA'),
           ('63', 'OMISSAO DE DECLARACOES')]

# ---------------------------------------------------------------------------
# Nomes ficticios
# ---------------------------------------------------------------------------
PRENOMES = ['ANA', 'BRUNO', 'CARLA', 'DANIEL', 'ELISA', 'FABIO', 'GABRIELA', 'HUGO',
            'IRENE', 'JOAO', 'KARINA', 'LUCAS', 'MARIA', 'NELSON', 'OLGA', 'PEDRO',
            'RAQUEL', 'SERGIO', 'TATIANA', 'VITOR']
SOBRENOMES = ['ALMEIDA', 'BARBOSA', 'CARDOSO', 'DIAS', 'ESTEVES', 'FARIAS', 'GOMES',
              'HENRIQUES', 'IGLESIAS', 'JARDIM', 'LACERDA', 'MOREIRA', 'NOGUEIRA',
              'OLIVEIRA', 'PEIXOTO', 'QUEIROZ', 'RIBEIRO', 'SALGADO', 'TEIXEIRA', "D'AVILA"]
PALAVRAS = ['AURORA', 'BOREAL', 'CASCATA', 'DUNA', 'ESTRELA', 'FAROL', 'GIRASSOL',
            'HORIZONTE', 'IPE', 'JASMIM', 'LUAR', 'MARE', 'NASCENTE', 'ORVALHO',
            'PRIMAVERA', 'QUARTZO', 'RECANTO', 'SERRA', 'TROPICO', 'VENTURA']
RAMOS = {
    '6204000': 'TECNOLOGIA', '6311900': 'DADOS', '4711302': 'SUPERMERCADOS',
    '4712100': 'MERCEARIA', '4120400': 'CONSTRUTORA', '5611201': 'RESTAURANTE',
    '4930202': 'TRANSPORTES', '6920601': 'CONTABILIDADE', '4781400': 'MODAS',
    '9602501': 'SALAO DE BELEZA',
}


def dv_cnpj(base12):
    '''Digitos verificadores do CNPJ (base12 = basico + ordem).'''
    def digito(numeros, pesos):
        resto = sum(int(n) * p for n, p in zip(numeros, pesos)) % 11
        return '0' if resto < 2 else str(11 - resto)
    d1 = digito(base12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = digito(base12 + d1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return d1 + d2


def cnpj_completo(basico, ordem='0001'):
    return basico + ordem + dv_cnpj(basico + ordem)


class Gerador:
    def __init__(self, semente=SEMENTE):
        self.rnd = random.Random(semente)
        self.empresas = []
        self.estabelecimentos = []
        self.socios = []
        self.simples = []
        self.cpfs_usados = set()
        self.pessoas = [self.nova_pessoa() for _ in range(90)]

    # -- auxiliares ---------------------------------------------------------
    def data(self, ano_ini=1995, ano_fim=2024):
        return '{:04d}{:02d}{:02d}'.format(self.rnd.randint(ano_ini, ano_fim),
                                           self.rnd.randint(1, 12), self.rnd.randint(1, 28))

    def nova_pessoa(self):
        while True:
            cpf = '***{:06d}**'.format(self.rnd.randint(0, 999999))
            if cpf not in self.cpfs_usados:
                self.cpfs_usados.add(cpf)
                break
        nome = '{} {} {}'.format(self.rnd.choice(PRENOMES), self.rnd.choice(SOBRENOMES),
                                 self.rnd.choice(SOBRENOMES))
        return (nome, cpf, self.rnd.randint(2, 8))  # faixa etaria

    def pessoa_popular(self):
        # Pessoas das empresas avulsas: cada uma aparece em algumas empresas e
        # forma ligacoes. As pessoas 0 a 29 ficam reservadas para os grupos,
        # para os grafos dos exemplos ficarem legiveis.
        return self.rnd.choice(self.pessoas[PESSOAS_GRUPOS:])

    # -- registros ----------------------------------------------------------
    def empresa(self, basico, razao, natureza='2062', capital='10000,00', porte='01',
                cnae=None, filiais=0, situacao='02', municipio=None, fantasia='',
                ente='', simples=None, secundarias=''):
        cnae = cnae or self.rnd.choice(CNAES_COMUNS)
        municipio = municipio or self.rnd.choice(MUNICIPIOS)
        qualif_resp = '50' if natureza == '2135' else '49'
        self.empresas.append([basico, razao, natureza, qualif_resp, capital, porte, ente])
        for i in range(filiais + 1):
            ordem = '{:04d}'.format(i + 1)
            mun = municipio if i == 0 else self.rnd.choice(MUNICIPIOS)
            self.estabelecimentos.append(self.estabelecimento(
                basico, ordem, '1' if i == 0 else '2',
                fantasia if i == 0 else '{} {}'.format(fantasia or 'FILIAL', mun[1]),
                situacao if i == 0 else '02', mun, cnae, secundarias if i == 0 else ''))
        if simples is None:
            simples = self.rnd.random() < 0.4 and natureza == '2062'
        if simples:
            self.simples.append([basico, 'S', self.data(2007, 2023), '00000000',
                                 'S' if natureza == '2135' else 'N',
                                 self.data(2009, 2023) if natureza == '2135' else '00000000',
                                 '00000000'])
        return cnpj_completo(basico)

    def estabelecimento(self, basico, ordem, matriz_filial, fantasia, situacao, municipio, cnae, secundarias):
        codigo, _, uf, cep = municipio
        motivo = '00' if situacao == '02' else ('01' if situacao == '08' else '63')
        return [basico, ordem, dv_cnpj(basico + ordem), matriz_filial, fantasia, situacao,
                self.data(2015, 2024), motivo, '', '', self.data(1990, 2022), cnae, secundarias,
                'RUA', '{} {}'.format(self.rnd.choice(PALAVRAS), self.rnd.choice(PALAVRAS)),
                str(self.rnd.randint(1, 3000)), '', 'CENTRO',
                '{}{:06d}'.format(cep, self.rnd.randint(0, 999999)), uf, codigo,
                '61', '3{:07d}'.format(self.rnd.randint(0, 9999999)), '', '', '', '',
                'contato@exemplo.com.br', '', '']

    def socio_pf(self, basico, pessoa, qualificacao='49'):
        nome, cpf, faixa = pessoa
        self.socios.append([basico, '2', nome, cpf, qualificacao, self.data(1995, 2024), '',
                            '***000000**', '', '00', str(faixa)])

    def socio_pj(self, basico, cnpj_socio, razao, qualificacao='22'):
        self.socios.append([basico, '1', razao, cnpj_socio, qualificacao, self.data(2000, 2024), '',
                            '***000000**', '', '00', '0'])

    def socio_estrangeiro(self, basico, nome, pais, representante):
        self.socios.append([basico, '3', nome, '', '37', self.data(2005, 2020), pais,
                            representante[1], representante[0], '17', '0'])

    # -- cenarios -----------------------------------------------------------
    def grupo_alfa(self):
        '''Holding com controladas, controlada de controlada, filiais,
        socio estrangeiro e administradores em comum.'''
        presidente = self.pessoas[0]
        diretora = self.pessoas[1]
        holding = self.empresa('10000001', 'ALFA HOLDING PARTICIPACOES S.A.', '2054',
                               '25000000,00', '05', '6462000', filiais=0,
                               municipio=MUNICIPIOS[0], fantasia='GRUPO ALFA', simples=False)
        self.socio_pf('10000001', presidente, '16')
        self.socio_pf('10000001', diretora, '10')
        self.socio_estrangeiro('10000001', 'GLOBAL ALFA INVESTMENTS LLC', '249', self.pessoas[2])

        controladas = [
            ('10000002', 'ALFA SUPERMERCADOS LTDA', '4711302', 3),
            ('10000003', 'ALFA TECNOLOGIA LTDA', '6204000', 1),
            ('10000004', 'ALFA CONSTRUTORA LTDA', '4120400', 0),
            ('10000005', 'ALFA TRANSPORTES LTDA', '4930202', 2),
        ]
        for basico, razao, cnae, filiais in controladas:
            self.empresa(basico, razao, '2062', '1000000,00', '05', cnae, filiais=filiais,
                         simples=False, secundarias='6311900' if cnae == '6204000' else '')
            self.socio_pj(basico, holding, 'ALFA HOLDING PARTICIPACOES S.A.', '22')
            self.socio_pf(basico, diretora, '05')

        # Controlada de controlada (nivel 2 a partir da holding)
        tec = cnpj_completo('10000003')
        self.empresa('10000006', 'ALFA DADOS E NUVEM LTDA', '2062', '300000,00', '03', '6311900', simples=False)
        self.socio_pj('10000006', tec, 'ALFA TECNOLOGIA LTDA', '22')
        self.socio_pf('10000006', self.pessoas[3], '49')

        # Empresa baixada que pertencia ao grupo
        self.empresa('10000007', 'ALFA ATACADO LTDA', '2062', '50000,00', '01', '4711302',
                     situacao='08', simples=False)
        self.socio_pj('10000007', holding, 'ALFA HOLDING PARTICIPACOES S.A.', '22')

        # O presidente tambem tem negocios fora do grupo
        self.empresa('10000008', 'RESTAURANTE SABOR DO PRESIDENTE LTDA', '2062', '80000,00',
                     '01', '5611201', fantasia='SABOR')
        self.socio_pf('10000008', presidente, '49')
        self.socio_pf('10000008', self.pessoas[4], '22')

    def grupo_bravo(self):
        bravo = self.empresa('20000001', 'BRAVO SERVICOS INTEGRADOS LTDA', '2062', '500000,00',
                             '03', '6920601', filiais=1, municipio=MUNICIPIOS[1], fantasia='BRAVO')
        self.socio_pf('20000001', self.pessoas[5], '49')
        self.socio_pf('20000001', self.pessoas[6], '49')

        self.empresa('20000002', 'BRAVO MODAS LTDA', '2062', '120000,00', '01', '4781400')
        self.socio_pj('20000002', bravo, 'BRAVO SERVICOS INTEGRADOS LTDA', '22')
        self.socio_pf('20000002', self.pessoas[6], '05')

        modas = cnpj_completo('20000002')
        self.empresa('20000003', 'BRAVO MODAS ONLINE LTDA', '2062', '40000,00', '01', '4781400')
        self.socio_pj('20000003', modas, 'BRAVO MODAS LTDA', '22')
        self.socio_pf('20000003', self.pessoas[7], '49')

        # Socio PJ que nao existe na base (aparece no grafo so com o CNPJ)
        self.socio_pj('20000003', '98765432000198', 'EMPRESA FORA DA BASE S.A.', '22')

    def grupo_charlie(self):
        '''Cadeia de participacoes: holding > industria > distribuidora > logistica.
        A partir da holding, a logistica esta no nivel 3.'''
        holding = self.empresa('50000001', 'CHARLIE PARTICIPACOES S.A.', '2054', '8000000,00', '05',
                               '6462000', municipio=MUNICIPIOS[3], fantasia='GRUPO CHARLIE', simples=False)
        self.socio_pf('50000001', self.pessoas[10], '16')
        self.socio_pf('50000001', self.pessoas[11], '22')

        industria = self.empresa('50000002', 'CHARLIE INDUSTRIA DE ALIMENTOS LTDA', '2062', '3000000,00',
                                 '05', '4711302', filiais=2, municipio=MUNICIPIOS[3], simples=False)
        self.socio_pj('50000002', holding, 'CHARLIE PARTICIPACOES S.A.', '22')
        self.socio_pf('50000002', self.pessoas[12], '05')

        distribuidora = self.empresa('50000003', 'CHARLIE DISTRIBUIDORA LTDA', '2062', '900000,00',
                                     '05', '4712100', filiais=1, simples=False)
        self.socio_pj('50000003', industria, 'CHARLIE INDUSTRIA DE ALIMENTOS LTDA', '22')
        self.socio_pf('50000003', self.pessoas[13], '05')

        self.empresa('50000004', 'CHARLIE LOGISTICA LTDA', '2062', '400000,00', '03', '4930202', simples=False)
        self.socio_pj('50000004', distribuidora, 'CHARLIE DISTRIBUIDORA LTDA', '22')
        self.socio_pf('50000004', self.pessoas[13], '49')

        self.empresa('50000005', 'CHARLIE ATACADO LTDA', '2062', '250000,00', '03', '4711302', simples=False)
        self.socio_pj('50000005', industria, 'CHARLIE INDUSTRIA DE ALIMENTOS LTDA', '22')
        self.socio_pf('50000005', self.pessoas[12], '05')

    def grupo_delta(self):
        '''Empresas de uma familia, ligadas pelas pessoas (sem holding).
        Uma socia tambem e socia do restaurante do presidente do grupo ALFA.'''
        pai, mae, filho, filha = self.pessoas[14], self.pessoas[15], self.pessoas[16], self.pessoas[17]
        self.empresa('60000001', 'PADARIA DELTA LTDA', '2062', '60000,00', '01', '5611201',
                     filiais=1, municipio=MUNICIPIOS[0], fantasia='PADARIA DELTA', simples=True)
        self.socio_pf('60000001', pai, '49')
        self.socio_pf('60000001', mae, '49')
        self.socio_pf('60000001', self.pessoas[4], '22')   # socia tambem do restaurante do grupo ALFA

        self.empresa('60000002', 'DELTA RESTAURANTE E EVENTOS LTDA', '2062', '120000,00', '01',
                     '5611201', municipio=MUNICIPIOS[0], fantasia='DELTA EVENTOS', simples=True)
        self.socio_pf('60000002', mae, '49')
        self.socio_pf('60000002', filho, '22')

        self.empresa('60000003', 'DELTA CONSTRUCOES LTDA', '2062', '500000,00', '03', '4120400',
                     municipio=MUNICIPIOS[0], simples=False)
        self.socio_pf('60000003', filho, '49')
        self.socio_pf('60000003', filha, '22')

        self.empresa('60000004', '{} 0004'.format(filha[0]), '2135', '5000,00', '01', '9602501',
                     municipio=MUNICIPIOS[0], fantasia='STUDIO DELTA', simples=True)
        self.socio_pf('60000004', filha, '65')

        self.empresa('60000005', 'DELTA CONTABILIDADE LTDA', '2062', '30000,00', '01', '6920601',
                     municipio=MUNICIPIOS[0], situacao='08', simples=False)
        self.socio_pf('60000005', filha, '49')
        self.socio_pf('60000005', self.pessoas[18], '22')

    def prefeitura(self):
        self.empresa('30000001', 'MUNICIPIO DE EXEMPLO', '1244', '0,00', '05', '8411600',
                     municipio=MUNICIPIOS[2], fantasia='PREFEITURA', ente='EXEMPLO - RJ', simples=False)

    def empresas_avulsas(self, quantidade=180):
        for i in range(quantidade):
            basico = '{:08d}'.format(40000001 + i)
            cnae = self.rnd.choice(CNAES_COMUNS)
            if self.rnd.random() < 0.2:
                # Empresario individual / MEI
                titular = self.pessoa_popular()
                nome = '{} {}'.format(titular[0], basico[-4:])
                self.empresa(basico, nome, '2135', '5000,00', '01', cnae, simples=True)
                self.socio_pf(basico, titular, '65')
                continue

            palavra1, palavra2 = self.rnd.choice(PALAVRAS), self.rnd.choice(PALAVRAS)
            razao = '{} {} {} LTDA'.format(RAMOS[cnae], palavra1, palavra2)
            situacao = self.rnd.choices(['02', '04', '08'], [85, 5, 10])[0]
            self.empresa(basico, razao, '2062', '{},00'.format(self.rnd.choice([10000, 50000, 200000])),
                         self.rnd.choice(['01', '03', '05']), cnae,
                         filiais=self.rnd.choices([0, 1, 2], [80, 15, 5])[0],
                         situacao=situacao, fantasia=palavra1 if self.rnd.random() < 0.5 else '')
            usados = set()
            for _ in range(self.rnd.choice([1, 1, 2, 2, 3])):
                pessoa = self.pessoa_popular()
                if pessoa[1] in usados:
                    continue
                usados.add(pessoa[1])
                self.socio_pf(basico, pessoa, self.rnd.choice(['49', '49', '22', '05']))

    def gera(self):
        self.grupo_alfa()
        self.grupo_bravo()
        self.grupo_charlie()
        self.grupo_delta()
        self.prefeitura()
        self.empresas_avulsas()
        return self


def grava_zip(pasta, nome_zip, nome_csv, linhas):
    dados = ''.join(';'.join('"{}"'.format(v) for v in linha) + '\n' for linha in linhas)
    with zipfile.ZipFile(os.path.join(pasta, nome_zip), 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(nome_csv, dados.encode('latin-1'))


def gera_zips(pasta, semente=SEMENTE):
    '''Cria em <pasta> os ZIPs no formato da RF e retorna a lista de arquivos.'''
    os.makedirs(pasta, exist_ok=True)
    g = Gerador(semente).gera()
    d = DATA_RF
    grava_zip(pasta, 'Empresas0.zip', 'K3241.K03200Y0.{}.EMPRECSV'.format(d), g.empresas)
    grava_zip(pasta, 'Estabelecimentos0.zip', 'K3241.K03200Y0.{}.ESTABELE'.format(d), g.estabelecimentos)
    grava_zip(pasta, 'Socios0.zip', 'K3241.K03200Y0.{}.SOCIOCSV'.format(d), g.socios)
    grava_zip(pasta, 'Simples.zip', 'F.K03200$W.SIMPLES.CSV.{}'.format(d), g.simples)
    grava_zip(pasta, 'Cnaes.zip', 'F.K03200$Z.{}.CNAECSV'.format(d), CNAES)
    grava_zip(pasta, 'Motivos.zip', 'F.K03200$Z.{}.MOTICSV'.format(d), MOTIVOS)
    grava_zip(pasta, 'Municipios.zip', 'F.K03200$Z.{}.MUNICCSV'.format(d), [m[:2] for m in MUNICIPIOS])
    grava_zip(pasta, 'Naturezas.zip', 'F.K03200$Z.{}.NATJUCSV'.format(d), NATUREZAS)
    grava_zip(pasta, 'Paises.zip', 'F.K03200$Z.{}.PAISCSV'.format(d), PAISES)
    grava_zip(pasta, 'Qualificacoes.zip', 'F.K03200$Z.{}.QUALSCSV'.format(d), QUALIFICACOES)
    return sorted(os.path.join(pasta, f) for f in os.listdir(pasta) if f.endswith('.zip'))


def gera_banco(arquivo=ARQUIVO_PADRAO, pasta_zips=None):
    temporaria = tempfile.mkdtemp(prefix='cnpj_teste_')
    try:
        zips = gera_zips(pasta_zips or os.path.join(temporaria, 'zips'))
        saida = os.path.join(temporaria, 'saida')
        cnpj.cnpj_full(zips, 'sqlite', saida, cnpj.MODO_SEGURO)
        cnpj.cnpj_index(saida, cnpj.MODO_SEGURO)
        destino = os.path.abspath(arquivo)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        shutil.move(os.path.join(saida, cnpj.NOME_ARQUIVO_SQLITE), destino)
    finally:
        shutil.rmtree(temporaria, ignore_errors=True)
    print('\nBanco de teste gerado: {}'.format(destino))
    return destino


def main():
    args = sys.argv[1:]
    arquivo = ARQUIVO_PADRAO
    pasta_zips = None
    i = 0
    while i < len(args):
        if args[i] == '--saida' and i + 1 < len(args):
            arquivo = args[i + 1]
            i += 2
        elif args[i] == '--zips' and i + 1 < len(args):
            pasta_zips = args[i + 1]
            i += 2
        else:
            print(__doc__)
            sys.exit(-1)
    gera_banco(arquivo, pasta_zips)


if __name__ == '__main__':
    main()
