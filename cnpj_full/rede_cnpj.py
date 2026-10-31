import pandas as pd

import networkx as nx
from networkx.readwrite import json_graph

# Tipos de pessoa (mesmos codigos do identificador_socio da RF)
PJ = 1
PF = 2
ESTRANGEIRO = 3

MATRIZ = 1
FILIAL = 2
SITUACAO_ATIVA = 2

# Consulta base dos dados de uma PJ (estabelecimento + empresa + simples
# + descricoes das tabelas de dominio). O id do node da PJ e o CNPJ
# completo (14 digitos) do estabelecimento.
SQL_PJ = '''
    SELECT
        est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv AS cnpj,
        est.cnpj_basico,
        est.identificador_matriz_filial,
        emp.razao_social,
        est.nome_fantasia,
        est.situacao_cadastral,
        est.data_situacao_cadastral,
        est.motivo_situacao_cadastral,
        moti.descricao AS motivo_situacao_cadastral_descricao,
        est.nome_cidade_exterior,
        est.pais,
        pais.descricao AS pais_descricao,
        emp.natureza_juridica,
        natju.descricao AS natureza_juridica_descricao,
        est.data_inicio_atividade,
        est.cnae_fiscal_principal,
        cnae.descricao AS cnae_fiscal_principal_descricao,
        est.cnae_fiscal_secundaria,
        est.tipo_logradouro,
        est.logradouro,
        est.numero,
        est.complemento,
        est.bairro,
        est.cep,
        est.uf,
        est.municipio,
        munic.descricao AS municipio_descricao,
        est.ddd_1,
        est.telefone_1,
        est.ddd_2,
        est.telefone_2,
        est.ddd_fax,
        est.fax,
        est.correio_eletronico,
        emp.qualificacao_responsavel,
        emp.capital_social,
        emp.porte_empresa,
        emp.ente_federativo_responsavel,
        est.situacao_especial,
        est.data_situacao_especial,
        simples.opcao_pelo_simples,
        simples.data_opcao_simples,
        simples.data_exclusao_simples,
        simples.opcao_mei,
        simples.data_opcao_mei,
        simples.data_exclusao_mei
    FROM
        estabelecimento est
            LEFT JOIN empresa emp ON emp.cnpj_basico = est.cnpj_basico
            LEFT JOIN simples ON simples.cnpj_basico = est.cnpj_basico
            LEFT JOIN moti ON moti.codigo = est.motivo_situacao_cadastral
            LEFT JOIN pais ON pais.codigo = est.pais
            LEFT JOIN natju ON natju.codigo = emp.natureza_juridica
            LEFT JOIN cnae ON cnae.codigo = est.cnae_fiscal_principal
            LEFT JOIN munic ON munic.codigo = est.municipio
'''


def _int(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


class RedeCNPJ:
    __conBD = None
    __nivel_max = 1
    __qualificacoes = 'TODAS'

    G = None

    def __init__(self, conBD, nivel_max=1, qualificacoes='TODAS'):
        self.__conBD = conBD
        self.__nivel_max = nivel_max

        # Normaliza as chaves das qualificacoes para int, ja que no BD o
        # codigo da qualificacao e armazenado como inteiro ('05' -> 5)
        if qualificacoes == 'TODAS':
            self.__qualificacoes = qualificacoes
        else:
            self.__qualificacoes = {int(k): v for k, v in qualificacoes.items()}

        self.G = nx.DiGraph()

    def _consulta(self, sql, params=()):
        # Retorna lista de dicts. Valores nulos viram '' para manter
        # compatibilidade com os formatos de exportacao (graphml/gexf).
        cursor = self.__conBD.execute(sql, params)
        colunas = [c[0] for c in cursor.description]
        return [{k: ('' if v is None else v) for k, v in zip(colunas, linha)}
                for linha in cursor.fetchall()]

    def _qualificacao(self, cod_qualificacao):
        # Retorna a descricao da qualificacao, ou None se nao for de interesse
        if self.__qualificacoes == 'TODAS':
            return cod_qualificacao
        return self.__qualificacoes.get(_int(cod_qualificacao))

    def insere_pessoa(self, tipo_pessoa, id_pessoa):
        self._vinculos(tipo_pessoa=tipo_pessoa, id_pessoa=id_pessoa)

    def dataframe_pessoas_G(self, G):
        nodes = list(G.nodes(data=True))
        return pd.DataFrame([i[1] for i in nodes], index=[i[0] for i in nodes], dtype=object)

    def dataframe_pessoas(self, nivel_max=None):
        if nivel_max is None:
            nivel_max = self.__nivel_max

        df = self.dataframe_pessoas_G(self.G)
        if len(df) == 0:
            return df
        return df[df['nivel'] <= nivel_max]

    def dataframe_vinculos_G(self, G):
        edge_data = G.edges(data=True)
        return pd.DataFrame([i[2] for i in edge_data], dtype=object,
                            index=pd.MultiIndex.from_tuples([(i[0], i[1]) for i in edge_data],
                            names=['source','target']))

    def dataframe_vinculos(self):
        return self.dataframe_vinculos_G(self.G)

    def json_G(self, G):
        # O template de visualizacao espera a chave "links". Versoes recentes
        # do networkx usam "edges" por padrao.
        try:
            return json_graph.node_link_data(G, edges='links')
        except TypeError:
            return json_graph.node_link_data(G)

    def json(self):
        return self.json_G(self.G)

    def gera_json(self, path):
        import json

        with open(path, "w") as f:
            f.write(json.dumps(self.json()))

    def gera_graphml_G(self, G, path):
        nx.write_graphml(G, path)

    def gera_graphml(self, path):
        self.gera_graphml_G(self.G, path)

    def gera_gexf_G(self, G, path):
        # Antes de gerar esse formato, necessario adaptar alguns atributos do grafo
        G_adapt = G.copy()

        pos = nx.spring_layout(G_adapt, dim=4, scale=1000)

        for node in G_adapt.nodes:
            tipo_pessoa = G_adapt.nodes[node]['tipo_pessoa']

            G_adapt.nodes[node]['label'] = G_adapt.nodes[node]['nome']

            # Configura atributos de visualizacao necessarios para alguns leitores
            G_adapt.nodes[node]['viz'] = {'size':10}

            if tipo_pessoa == PJ:
                if _int(G_adapt.nodes[node]['situacao_cadastral']) == SITUACAO_ATIVA:
                    G_adapt.nodes[node]['viz']['color'] = {'a':1,'r':1,'g':57,'b':155}
                else:
                    G_adapt.nodes[node]['viz']['color'] = {'a':1,'r':255,'g':0,'b':0}
            else:
                G_adapt.nodes[node]['viz']['color'] = {'a':1,'r':46,'g':125,'b':32}

            G_adapt.nodes[node]['viz']['position'] = {'x':float(pos[node][0]),
                                                      'y':float(pos[node][1]),
                                                      'z':5}

        nx.write_gexf(G_adapt, path)

    def gera_gexf(self, path):
        self.gera_gexf_G(self.G, path)

    def insere_com_cpf_ou_nome(self, cpf='', nome=''):
        # A partir de um nome ou um cpf, busca socios com esses dados e inclui na rede
        sql = '''
            SELECT distinct
                identificador_socio,
                cpf_cnpj_socio,
                nome_socio_razao_social
            FROM
                socios
        '''
        if cpf != '':
            sql += 'WHERE cpf_cnpj_socio = ?'
            params = (cpf,)
        else:
            sql += 'WHERE nome_socio_razao_social = ?'
            params = (nome,)

        empresas_socios = self._consulta(sql, params)
        if len(empresas_socios) > 0:
            for emp_socio in empresas_socios:
                cnpj_cpf_socio = emp_socio['cpf_cnpj_socio']
                nome_socio = emp_socio['nome_socio_razao_social']
                tipo_socio = _int(emp_socio['identificador_socio'])

                if tipo_socio == PJ:
                    self._vinculos(tipo_pessoa=tipo_socio, id_pessoa=cnpj_cpf_socio)
                else:
                    self._vinculos(tipo_pessoa=tipo_socio, id_pessoa=(cnpj_cpf_socio,nome_socio))
        else:
            print('Nenhum socio encontrado com o cpf ou nome informado: cpf:{} / nome:{}'.format(cpf, nome))

    def _busca_pj(self, cnpj):
        sql = SQL_PJ + '''
            WHERE est.cnpj_basico = ? AND est.cnpj_ordem = ? AND est.cnpj_dv = ?
        '''
        return self._consulta(sql, (cnpj[:8], cnpj[8:12], cnpj[12:14]))

    def _vinculos(self, tipo_pessoa, id_pessoa, atributos=None, nivel=0, origem=None):
        nome = None

        # Monta o id do node de acordo com o tipo de pessoa
        if tipo_pessoa == PJ:
            id_pessoa_str = id_pessoa
        else:
            nome = id_pessoa[1]
            id_pessoa_str = id_pessoa[0] + nome

        # Nova pessoa
        if id_pessoa_str not in self.G:
            nova_pessoa = True

            if atributos:
                self.G.add_node(id_pessoa_str, nome=nome, tipo_pessoa=tipo_pessoa, nivel=nivel, **atributos)
            else:
                self.G.add_node(id_pessoa_str, nome=nome, tipo_pessoa=tipo_pessoa, nivel=nivel)

            # Se for PJ, pega dados da empresa nas tabelas de estabelecimento/empresa
            if (tipo_pessoa == PJ):
                # Pega do banco apenas se dados nao vieram como parametro
                if not atributos:
                    empresa = self._busca_pj(id_pessoa)

                    if not empresa:
                        print('Empresa nao encontrada: {}'.format(id_pessoa_str))
                        self.G.remove_node(id_pessoa_str)
                        raise KeyError(id_pessoa_str)

                    for k, v in empresa[0].items():
                        self.G.nodes[id_pessoa_str][k] = v

                node = self.G.nodes[id_pessoa_str]
                nome_fantasia = str(node.get('nome_fantasia', '')).strip()
                if nome_fantasia in ('', 'NAO POSSUI'):
                    node['nome'] = node.get('razao_social', '')
                else:
                    node['nome'] = nome_fantasia

            else:
                # Se no for pessoa fisica (ou estrangeiro)
                self.G.nodes[id_pessoa_str]['cpf'] = id_pessoa[0]
        else:
            nova_pessoa = False
            nivel_anterior = self.G.nodes[id_pessoa_str]['nivel']

            if nivel < nivel_anterior:
                self.G.nodes[id_pessoa_str]['nivel'] = nivel

        # Condicoes para explorar "relacionados":
        # 1) Nivel atual ser menor do que configuracao max_nivel; e
        # 2) Relacionamentos não terem sido totalmente explorados antes, por
        #       a) ser uma pessoa nova OU
        #       b) nao é uma pessoa nova, mas o nivel atual é menor do que o nivel anterior dessa pessoa
        if (nivel < self.__nivel_max) and (nova_pessoa or nivel < nivel_anterior):
            # obtem todas as relacoes de sociedades que envolvam esse PJ ou PF

            # Verifica se relacionados ja estao no grafo ou se precisa buscar no BD
            if (not nova_pessoa) and (nivel_anterior < self.__nivel_max):
                # Relacionados ja estao no grafo, nao precisa buscar no BD

                # navega para os socios
                for id_socio_str in list(self.G.predecessors(id_pessoa_str)):
                    node_socio = self.G.nodes[id_socio_str]
                    tipo_socio = node_socio['tipo_pessoa']

                    if tipo_socio == PJ:
                        # socio eh PJ
                        socio = id_socio_str
                    else:
                        # socio eh PF
                        socio = (node_socio['cpf'],node_socio['nome'])

                    self._vinculos(tipo_pessoa=tipo_socio, id_pessoa=socio, nivel=nivel+1, origem=id_pessoa)

                # navega para empresas das quais e socio
                for empresa in list(self.G.successors(id_pessoa_str)):
                    self._vinculos(tipo_pessoa=PJ, id_pessoa=empresa, nivel=nivel+1, origem=id_pessoa)

            else:
                # Relacionados ainda nao estao no grafo; buscar no BD.
                # (A) busca EMPRESAS das quais esta PJ/PF eh socia.
                # No novo layout o socio e vinculado ao CNPJ basico, entao a
                # empresa e representada pelo estabelecimento matriz.
                sql = '''
                    SELECT
                        s.qualificacao_socio AS s_qualificacao_socio,
                        s.data_entrada_sociedade AS s_data_entrada_sociedade,
                        pj.*
                    FROM
                        socios s
                            INNER JOIN ({}) pj
                                ON pj.cnpj_basico = s.cnpj_basico
                                AND pj.identificador_matriz_filial = {}
                    '''.format(SQL_PJ, MATRIZ)

                if tipo_pessoa == PJ:
                    sql += 'WHERE s.cpf_cnpj_socio = ?'
                    params = (id_pessoa,)
                else:
                    sql += 'WHERE s.cpf_cnpj_socio = ? AND s.nome_socio_razao_social = ?'
                    params = (id_pessoa[0], id_pessoa[1])

                empresas = self._consulta(sql, params)

                for empresa in empresas:
                    cod_qualificacao = empresa.pop('s_qualificacao_socio')
                    data_entrada = empresa.pop('s_data_entrada_sociedade')
                    qualificacao = self._qualificacao(cod_qualificacao)

                    # Apenas adiciona relacionamento se for qualificacao de interesse
                    if qualificacao is not None:
                        cnpj = empresa['cnpj']

                        # se a empresa nao for a origem desse pulo
                        if cnpj != origem:
                            # chama recursivamente para tratar a PJ
                            self._vinculos(tipo_pessoa=PJ, id_pessoa=cnpj, nivel=nivel+1, origem=id_pessoa, atributos=empresa)

                            # adiciona aresta de socio para empresa em questao
                            self.G.add_edge(id_pessoa_str,
                                            cnpj,
                                            tipo='socio',
                                            cod_qualificacao=cod_qualificacao,
                                            qualificacao=qualificacao,
                                            data_entrada=data_entrada)


                # (B) SOCIOS desta PJ (apenas se matriz)
                if tipo_pessoa == PJ and (_int(self.G.nodes[id_pessoa_str]['identificador_matriz_filial']) == MATRIZ):
                    sql = '''
                    SELECT
                        identificador_socio,
                        cpf_cnpj_socio,
                        nome_socio_razao_social,
                        qualificacao_socio,
                        data_entrada_sociedade
                    FROM
                        socios
                    WHERE
                        cnpj_basico = ?
                    '''

                    socios = self._consulta(sql, (id_pessoa[:8],))

                    for socio in socios:
                        cod_qualificacao = socio['qualificacao_socio']
                        qualificacao = self._qualificacao(cod_qualificacao)

                        # Apenas adiciona relacionamento se for qualificacao de interesse
                        if qualificacao is not None:
                            cnpj_cpf_socio = socio['cpf_cnpj_socio']
                            nome_socio = socio['nome_socio_razao_social']
                            tipo_socio = _int(socio['identificador_socio'])
                            data_entrada = socio['data_entrada_sociedade']

                            if tipo_socio == PJ:
                                # socio eh PJ. Sem o CNPJ nao e possivel montar o node.
                                if cnpj_cpf_socio == '':
                                    continue
                                id_socio = cnpj_cpf_socio
                                socio_str = id_socio
                            else:
                                # socio eh PF (ou estrangeiro)
                                id_socio = (cnpj_cpf_socio,nome_socio)
                                socio_str = cnpj_cpf_socio + nome_socio

                            # se o socio nao for a origem desse pulo
                            if id_socio != origem:
                                # chama recursivamente para tratar a nova PJ/PF
                                try:
                                    self._vinculos(tipo_pessoa=tipo_socio, id_pessoa=id_socio, nivel=nivel+1, origem=id_pessoa)
                                except KeyError:
                                    # socio PJ sem cadastro na base (ex: base parcial)
                                    continue

                                # adiciona aresta de socio para empresa em questao
                                self.G.add_edge(socio_str,
                                                id_pessoa_str,
                                                tipo='socio',
                                                cod_qualificacao=cod_qualificacao,
                                                qualificacao=qualificacao,
                                                data_entrada=data_entrada)


                # Se for filial, busca matriz
                if (tipo_pessoa == PJ) and (_int(self.G.nodes[id_pessoa_str]['identificador_matriz_filial']) == FILIAL):
                    sql = SQL_PJ + '''
                        WHERE est.cnpj_basico = ? AND est.identificador_matriz_filial = {}
                    '''.format(MATRIZ)

                    matriz = self._consulta(sql, (id_pessoa[:8],))
                    if matriz:
                        cnpj_matriz = matriz[0]['cnpj']

                        self._vinculos(tipo_pessoa=PJ, id_pessoa=cnpj_matriz, nivel=nivel+1, origem=id_pessoa, atributos=matriz[0])

                        self.G.add_edge(id_pessoa_str, cnpj_matriz, tipo='filial')
                    else:
                        print('Matriz nao encontrada associada a filial: {}'.format(id_pessoa_str))
