import os
import sys
import json
import hashlib
import subprocess

import pandas as pd
import sqlite3
import networkx as nx

# Funciona tanto como script (python3 cnpj_full/consulta.py) quanto como
# modulo do pacote (python3 -m cnpj_full.consulta ou import nos testes)
if __package__:
    from . import config
    from .rede_cnpj import RedeCNPJ
else:
    import config
    from rede_cnpj import RedeCNPJ

PATH_VIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'viz')
PATH_TEMPLATE = os.path.join(PATH_VIZ, 'template.html')
# d3.js embutido no grafo.html para a visualizacao funcionar sem internet
PATH_D3 = os.path.join(PATH_VIZ, 'd3.v7.min.js')


def gera_html_grafo(grafo_json):
    """Monta o grafo.html autocontido: template + d3.js + dados do grafo."""
    with open(PATH_TEMPLATE, 'r', encoding='utf-8') as template:
        str_html = template.read()
    with open(PATH_D3, 'r', encoding='utf-8') as d3:
        str_d3 = d3.read()

    # "</" dentro do JSON fecharia a tag <script> antes da hora (ex: nome com "</script>")
    str_grafo = json.dumps(grafo_json).replace('</', '<\\/')

    # split/join em vez de replace encadeado: o conteudo inserido nunca e reprocessado
    antes_d3, depois_d3 = str_html.split('<!--D3-->', 1)
    antes_grafo, depois_grafo = depois_d3.split('<!--GRAFO-->', 1)
    return antes_d3 + str_d3 + antes_grafo + str_grafo + depois_grafo

# Arquivo gravado na pasta de saida com a chave da consulta que gerou os arquivos
ARQUIVO_CACHE = 'cache.json'
VERSAO_CACHE = 1


def _hash_arquivo(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b''):
            h.update(bloco)
    return h.hexdigest()


def versao_base(conBD, path_BD):
    """Identifica a carga da base. Muda quando a base e recarregada.

    Usa o fim da ultima carga registrada na controle_carga (gravada pelo carga.py).
    Se a tabela nao existir, usa data de modificacao e tamanho do arquivo.
    """
    try:
        pendentes, arquivos, ultima = conBD.execute(
            'SELECT SUM(fim IS NULL), COUNT(*), MAX(fim) FROM controle_carga').fetchone()
        if arquivos and not pendentes:
            return 'carga:{}:{}'.format(arquivos, ultima)
    except sqlite3.Error:
        pass
    info = os.stat(path_BD)
    return 'arquivo:{}:{}'.format(int(info.st_mtime), info.st_size)


def _normaliza_objeto(tipo_consulta, objeto_consulta):
    if tipo_consulta == 'cnpj':
        return objeto_consulta.replace('.', '').replace('/', '').replace('-', '').strip().zfill(14)
    if tipo_consulta == 'nome_socio':
        return objeto_consulta.strip().upper()
    # CPF sempre mascarado na chave: o cache.json nunca guarda o CPF completo
    # e "12345678901" e "***456789**" contam como a mesma consulta
    if tipo_consulta == 'cpf':
        return mascara_cpf(objeto_consulta.strip().replace('.', '').replace('-', ''))
    if tipo_consulta == 'cpf_nome':
        objeto_consulta = objeto_consulta.strip()
        return mascara_cpf(objeto_consulta[:11]) + objeto_consulta[11:].strip().upper()
    if tipo_consulta == 'file':
        # o conteudo do arquivo e que define a consulta, nao o nome
        return 'sha256:' + _hash_arquivo(objeto_consulta)
    return objeto_consulta.strip()


def chave_cache(tipo_consulta, objeto_consulta, qualificacoes, nivel_max, versao,
                csv, colunas_csv, csv_sep, graphml, gexf, viz, path_conexoes):
    """Tudo o que muda o resultado: criterio de pesquisa, nivel, qualificacoes,
    carga da base e saidas pedidas."""
    if isinstance(qualificacoes, dict):
        qualificacoes = sorted(qualificacoes)
    return {
        'versao_cache': VERSAO_CACHE,
        'tipo_consulta': tipo_consulta,
        'objeto_consulta': _normaliza_objeto(tipo_consulta, objeto_consulta),
        'nivel': int(nivel_max),
        'qualificacoes': qualificacoes,
        'base': versao,
        'saidas': {
            'csv': bool(csv), 'colunas_csv': list(colunas_csv) if (csv and colunas_csv) else None,
            'csv_sep': csv_sep if csv else None,
            'graphml': bool(graphml), 'gexf': bool(gexf), 'viz': bool(viz),
            'conexoes': _hash_arquivo(path_conexoes) if path_conexoes else None,
        },
    }


def le_cache(path_output):
    try:
        with open(os.path.join(path_output, ARQUIVO_CACHE), 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def cache_valido(path_output, chave):
    """True quando a pasta ja tem o resultado desta mesma consulta, com todos os arquivos."""
    gravado = le_cache(path_output)
    if not gravado or gravado.get('chave') != chave:
        return False
    return all(os.path.exists(os.path.join(path_output, nome)) for nome in gravado.get('arquivos', []))


def _limpa_cache(path_output):
    """Apaga o cache.json e os arquivos que ele lista, para nao misturar resultados."""
    gravado = le_cache(path_output)
    if gravado:
        for nome in gravado.get('arquivos', []):
            caminho = os.path.join(path_output, os.path.basename(nome))
            if os.path.isfile(caminho):
                os.remove(caminho)
    caminho_cache = os.path.join(path_output, ARQUIVO_CACHE)
    if os.path.exists(caminho_cache):
        os.remove(caminho_cache)


def _grava_cache(path_output, chave):
    arquivos = [nome for nome in ['pessoas.csv', 'vinculos.csv', 'rede.graphml', 'rede.gexf',
                                  'grafo.html', 'conexoes.csv']
                if os.path.exists(os.path.join(path_output, nome))]
    with open(os.path.join(path_output, ARQUIVO_CACHE), 'w', encoding='utf-8') as f:
        json.dump({'chave': chave, 'arquivos': arquivos}, f, ensure_ascii=False, indent=2)


def _abre_navegador(path_output):
    if config.PATH_NAVEGADOR:
        subprocess.Popen([config.PATH_NAVEGADOR, os.path.abspath(os.path.join(path_output, 'grafo.html'))])


def consulta(tipo_consulta, objeto_consulta, qualificacoes, path_BD, nivel_max, path_output, 
             csv=False, colunas_csv=None, csv_sep=',', graphml=False, gexf=False, viz=False, 
             path_conexoes=None, cache=False):
    """Executa a consulta e grava as saidas em path_output.

    Com cache=True, se path_output ja tiver o resultado da mesma consulta (mesmo
    criterio, nivel, qualificacoes, saidas e carga da base), os arquivos sao
    reaproveitados sem consultar o banco de novo. Retorna True nesse caso.
    """

    if not os.path.isfile(path_BD):
        # sqlite3.connect criaria um banco vazio no lugar
        print('Nao foi possivel encontrar ou conectar ao BD {}'.format(path_BD))
        return False

    try:
        conBD = sqlite3.connect(path_BD)

        try:
            chave = None
            if cache:
                chave = chave_cache(tipo_consulta, objeto_consulta, qualificacoes, nivel_max,
                                    versao_base(conBD, path_BD), csv, colunas_csv, csv_sep,
                                    graphml, gexf, viz, path_conexoes)
                if cache_valido(path_output, chave):
                    print('Resultado reaproveitado do cache na pasta "{}".'.format(path_output))
                    if viz:
                        _abre_navegador(path_output)
                    return True

            if os.path.isdir(path_output):
                # resultado antigo sai antes de gerar o novo; se a consulta falhar no meio,
                # nao fica um cache.json valido apontando para arquivos incompletos
                _limpa_cache(path_output)

            rede = RedeCNPJ(conBD, nivel_max=nivel_max, qualificacoes=qualificacoes)

            if tipo_consulta == 'file':
                df_file = pd.read_csv(objeto_consulta, sep=csv_sep, header=None, dtype=str)

                qtd_colunas = len(df_file.columns)

                for _, linha in df_file.iterrows():
                    if qtd_colunas >= 2:
                        try:
                            consulta_item(rede, linha[0].strip(), linha[1].strip())
                        except KeyError as e:
                            print('Item nao encontrado ({}): {}'.format(linha[0].strip(),
                                                                        linha[1].strip()))
                    else:
                        try:
                            consulta_item(rede, 'cnpj', linha[0].strip())
                        except KeyError as e:
                            print('CNPJ nao encontrado: {}'.format(linha[0].strip()))
            else:
                consulta_item(rede, tipo_consulta, objeto_consulta)

            if not os.path.exists(path_output):
                os.makedirs(path_output)

            if csv:
                # Garante todas as colunas configuradas, mesmo que ausentes nos nodes
                df_nodes = rede.dataframe_pessoas().reindex(columns=colunas_csv)

                # Verifica se teve ao menos um registro encontrado
                if len(df_nodes) > 0:
                    df_nodes.to_csv(os.path.join(path_output, 'pessoas.csv'), index_label='id', sep=csv_sep)

                    df_edges = rede.dataframe_vinculos()
                    if len(df_edges) > 0:
                        df_edges.to_csv(os.path.join(path_output, 'vinculos.csv'), sep=csv_sep)
                else:
                    print('Nenhum registro foi localizado. Arquivos de output nao foram gerados.')

            if graphml:
                rede.gera_graphml(os.path.join(path_output, 'rede.graphml'))

            if gexf:
                rede.gera_gexf(os.path.join(path_output, 'rede.gexf'))

            if viz:
                try:
                    str_html = gera_html_grafo(rede.json())

                    path_html = os.path.join(path_output, 'grafo.html')
                    with open(path_html, 'w', encoding='utf-8') as html:
                        html.write(str_html)

                    _abre_navegador(path_output)

                except Exception as e:
                    print('Não foi possível gerar a visualização. [{}]'.format(e))

            if path_conexoes:
                df_conexoes = pd.read_csv(path_conexoes, sep=csv_sep, header=None, dtype=str)

                qtd_colunas = len(df_conexoes.columns)

                if qtd_colunas >= 2:
                    G_undirected = rede.G.to_undirected()
                    lista_conexoes = []

                    for _, linha in df_conexoes.iterrows():
                        pessoa_A = linha[0].strip()
                        pessoa_B = linha[1].strip()

                        conexao = ''
                        try:
                            lst_pessoas_conexao = nx.shortest_path(G_undirected, pessoa_A, pessoa_B)
                            conexao = ' | '.join(lst_pessoas_conexao)
                        except:
                            conexao = 'SEM CONEXAO'

                        lista_conexoes.append((pessoa_A, pessoa_B, conexao))

                    pd.DataFrame(lista_conexoes).to_csv(os.path.join(path_output, 'conexoes.csv'),
                                                        sep=csv_sep,
                                                        header=None,
                                                        index=None)

                else:
                    print('''
Arquivo de vinculos precisa ter pelo menos duas colunas, contendo a identificacao das pessoas (CNPJ ou cpf+nome).
No caso de pessoa fisica, informar cpf seguido imediatamente do nome (ex: "***123456**NOME COMPLETO DA PESSOA").
                    ''')

            if cache:
                _grava_cache(path_output, chave)

            print('Consulta finalizada. Verifique o(s) arquivo(s) de saida na pasta "{}".'.format(path_output))

        except Exception as e:
            print('Um erro ocorreu:\n{}'.format(e))
        finally:
            conBD.close()

        return False

    except:
        print('Nao foi possivel encontrar ou conectar ao BD {}'.format(path_BD))

def consulta_item(rede, tipo_item, item):
    if tipo_item == 'cnpj':
        #print('Consultando CNPJ: {}'.format(item))
        rede.insere_pessoa(1, item.replace('.','').replace('/','').replace('-','').zfill(14))

    elif tipo_item == 'nome_socio':
        #print('Consultando socios com nome: {}'.format(item))
        rede.insere_com_cpf_ou_nome(nome=item.upper())

    elif tipo_item == 'cpf':
        cpf = mascara_cpf(item.replace('.','').replace('-',''))
        #print('Consultando socios com cpf (mascarado): {}.'.format(cpf))
        rede.insere_com_cpf_ou_nome(cpf=cpf)

    elif tipo_item == 'cpf_nome':
        cpf = mascara_cpf(item[:11])
        # nomes na base da RF sao em maiusculas
        nome = item[11:].strip().upper()

        #print('Consultando socio com cpf (mascarado) {} e nome {}'.format(cpf,nome))
        rede.insere_pessoa(2,(cpf,nome))

        # Se nao tem vinculo, nao existe socio com esse par cpf e nome
        if len(rede.dataframe_vinculos()) == 0:
            print('Nenhum socio encontrado com cpf "{}" e nome "{}"'.format(cpf, nome))
            rede.G.remove_node(cpf+nome)
    else:
        print('Tipo de consulta invalido: {}.\nTipos possiveis: cnpj, nome_socio, cpf, cpf_nome'.format(tipo_item))

def mascara_cpf(cpf_original):
    cpf = cpf_original.zfill(11)
    if cpf[0:3] != '***':
        cpf = '***' + cpf[3:9] + '**'

    return cpf

def help():
    print('''
consulta.py - Consulta empresas e socios e gera a rede de relacionamentos

Busca no banco SQLite gerado pelo carga.py (ou no banco de teste) uma empresa,
socio ou lista de itens, e gera a rede de relacionamentos ate o nivel pedido
em CSV, GraphML, GEXF ou grafo interativo (grafo.html).

Uso: python consulta.py <tipo consulta> <item|arquivo input> <caminho output> 
     [--base <arquivo sqlite>] [--nivel <int>] 
     [--csv] [--graphml] [--gexf] [--viz] [--cache]

Argumentos obrigatorios:
  <tipo consulta>: Especifica o tipo de item a ser procurado.
    Opcoes:
    - cnpj: Busca empresa pelo numero do CNPJ
    - nome_socio: Busca socios pelo nome completo
    - cpf: Busca socios pelo numero do CPF 
      Pode trazer varios socios, ja que apenas seis digitos sao armazenados.
    - cpf_nome: Busca socios pelo numero do CPF seguido (sem espaco) do nome
    - file: Arquivo que contem mais de um item a ser buscado.
        Caso o arquivo tenha apenas um dado por linha, dado lido como CNPJ.
        Caso o arquivo tenha mais de um dado separado por ";", o primeiro
        indica um dos tipos acima, e o segundo o item a ser buscado.
        (outro separador pode ser definido em SEP_CSV no config.py) 

  <item|arquivo input>: Item a ser procurado, de acordo com <tipo consulta>. 
  <caminho output>: Pasta onde serao salvos os arquivos gerados.

Argumentos opcionais:
  --base: Especifica o arquivo do banco de dados de CNPJ em formato sqlite.
           Caso nao seja especificado, usa CNPJ_DB_ARQUIVO (variavel de
           ambiente ou arquivo .env na raiz do projeto) e, sem ela, o banco
           de teste dados/teste/cnpj_teste.db.

  --nivel: Especifica a profundidade da consulta em número de pulos.
            Ex: Caso seja especificado --nivel 1, busca o item e as
            as empresas ou pessoas diretamente relacionadas.
            Csaso nao seja especificado, usa o NIVEL_MAX_DEFAULT no config.py

  --csv: Para gerar o resultado em arquivos csv.
          Sao gerados dois arquivos, pessoas.csv e vinculos.csv.

  --graphml: Para gerar o resultado em grafo no formato GRAPHML.

  --gexf: Para gerar o resultado em grafo no formato GEXF. 
           Pode ser aberto com o software gephi (https://gephi.org/)

  --viz: Para gerar um HTML interativo com o resultado em grafo.
          Para abrir automaticamente o navegador, informar o PATH_NAVEGADOR 
          no config.py. Do contrario, basta abrir o arquivo grafo.html gerado 
          em <caminho output>.

  --conexoes: Especifica arquivo com pares de id de pessoas (cnpj ou cpf+nome),
              um par por linha, para busca de conexoes (diretas ou indiretas) 
              entre cada par. Gera arquivo conexoes.csv, com tres colunas. 
              As duas primeiras com o par de pessoas e a terceira coluna
              com a conexao entre elas, ou a string "SEM CONEXAO".

  --cache: Reaproveita o resultado ja gravado em <caminho output> quando a
           consulta e a mesma: tipo e item pesquisado, nivel, qualificacoes,
           saidas pedidas e carga da base (controle_carga). Se a base for
           recarregada ou algo mudar, a consulta e refeita e o cache atualizado.
           Os dados da consulta ficam em <caminho output>/cache.json.

Exemplos: 
  python consulta.py cnpj 10000001000190 resultado --viz   (banco de teste, sem --base)
  python consulta.py cnpj 00000000000191 folder --nivel 1 --viz
  python consulta.py file data/input.csv pasta --csv --gexf
  python consulta.py nome_socio "FULANO SICRANO" output --graphml --viz
  python consulta.py cnpj 00000000000191 graficos/00000000000191_n3 --nivel 3 --viz --cache
    ''')

def main():
    NUM_ARGS_OBRIGATORIOS = 4

    # Defaults
    csv = False
    graphml = False
    gexf = False
    viz = False
    nivel = config.NIVEL_MAX_DEFAULT
    path_bd = config.PATH_BD
    path_conexoes = None
    cache = False

    # python consulta.py <tipo consulta> <item|arquivo input> <caminho output> 
    # [--base <arquivo sqlite>] [--nivel <int>] [--csv] [--graphml] [--gexf] [--viz]
    num_argv = len(sys.argv)
    if num_argv < NUM_ARGS_OBRIGATORIOS:
        help()
        sys.exit(-1)
    else:
        tipo_consulta = sys.argv[1]
        objeto_consulta = sys.argv[2]
        output_path = sys.argv[3]

        if num_argv > NUM_ARGS_OBRIGATORIOS:
            i_argv = NUM_ARGS_OBRIGATORIOS
            while i_argv < num_argv:
                opcional = sys.argv[i_argv]

                if opcional == '--base':
                    path_bd = sys.argv[i_argv+1]
                    i_argv += 2
                elif opcional == '--nivel':
                    nivel = int(sys.argv[i_argv+1])
                    i_argv += 2
                elif opcional == '--csv':
                    csv = True
                    i_argv += 1
                elif opcional == '--graphml':
                    graphml = True
                    i_argv += 1
                elif opcional == '--gexf':
                    gexf = True
                    i_argv += 1
                elif opcional == '--viz':
                    viz = True
                    i_argv += 1
                elif opcional == '--cache':
                    cache = True
                    i_argv += 1
                elif opcional == '--conexoes':
                    path_conexoes = sys.argv[i_argv+1]
                    i_argv += 2
                else:
                    print('Parametro opcional invalido: {}'.format(opcional))
                    i_argv += 1

        if not os.path.isfile(path_bd):
            print('ERRO: banco SQLite nao encontrado: {}'.format(os.path.abspath(path_bd)))
            print('Informe o arquivo com --base <arquivo> ou defina CNPJ_DB_ARQUIVO no .env '
                  '({}). Veja docs/ambientes.md.'.format(config.ARQUIVO_ENV))
            sys.exit(-1)
        print('Banco: {}'.format(os.path.abspath(path_bd)))

        # Caso nenhum tipo de saida tenha sido selecionado, gera csv como default
        if not (csv+graphml+gexf+viz):
            csv = True

        consulta(tipo_consulta, objeto_consulta, 
                 config.QUALIFICACOES, 
                 path_bd, 
                 nivel, 
                 output_path, 
                 csv=csv, colunas_csv=config.COLUNAS_CSV, csv_sep=config.SEP_CSV,
                 graphml=graphml,
                 gexf=gexf,
                 viz=viz,
                 path_conexoes=path_conexoes,
                 cache=cache)

if __name__ == '__main__':
    main()
