# -*- encoding: utf-8 -*-
'''
Download dos dados abertos do CNPJ publicados pela Receita Federal.

A RF publica os arquivos em um compartilhamento publico do Nextcloud
(padrao: https://arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9),
com uma pasta por competencia (ex: 2026-10/). O script:

1. lista as pastas do compartilhamento (via WebDAV publico do Nextcloud);
2. entra na pasta da competencia mais recente (ano mais recente e ultimo mes),
   ou na competencia pedida com --competencia AAAA-MM;
3. baixa todos os arquivos dessa pasta para <destino>/<competencia>/.

Tambem funciona com uma listagem de diretorio comum (Apache/nginx), como a
antiga https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/.

Arquivos ja baixados com o mesmo tamanho sao pulados, e um download
interrompido continua de onde parou (arquivo .part), entao basta rodar de novo.

Usa apenas a biblioteca padrao do Python.
'''
import os
import re
import sys
import time
import base64
import zipfile
import argparse
import datetime
import posixpath
import http.client
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit, quote, unquote, parse_qs, urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cnpj_full import ambiente  # noqa: E402

URL_PADRAO = 'https://arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9'
PASTA_PADRAO = 'dados'

USER_AGENT = 'cnpj-full (https://github.com/bjverde/CNPJ-full)'
TIMEOUT = 60
TENTATIVAS = 5
TAMANHO_BLOCO = 1024 * 1024

MESES = ['janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho', 'julho',
         'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

PROPFIND_BODY = b'''<?xml version="1.0"?>
<d:propfind xmlns:d="DAV:">
  <d:prop><d:resourcetype/><d:getcontentlength/><d:getlastmodified/></d:prop>
</d:propfind>'''


class Item(object):
    '''Um arquivo ou pasta do servidor.'''
    def __init__(self, nome, pasta, url, tamanho=None):
        self.nome = nome
        self.pasta = pasta
        self.url = url
        self.tamanho = tamanho

    def __repr__(self):
        return 'Item({!r}, pasta={}, tamanho={})'.format(self.nome, self.pasta, self.tamanho)


# ---------------------------------------------------------------------------
# Acesso ao servidor
# ---------------------------------------------------------------------------

class Servidor(object):
    '''Base: lista uma pasta (caminho relativo, ex: "2026-10") e abre arquivos.'''
    headers = {}

    def lista(self, caminho):
        raise NotImplementedError

    def abre(self, url, inicio=0):
        headers = dict(self.headers)
        headers['User-Agent'] = USER_AGENT
        if inicio:
            headers['Range'] = 'bytes={}-'.format(inicio)
        return urlopen(Request(url, headers=headers), timeout=TIMEOUT)


class NextcloudPublico(Servidor):
    '''Compartilhamento publico do Nextcloud, lido pelo WebDAV publico
    (public.php/webdav, usuario = token do compartilhamento, sem senha).'''

    def __init__(self, base, token, caminho_inicial=''):
        self.base = base.rstrip('/')
        self.token = token
        self.caminho_inicial = caminho_inicial.strip('/')
        credencial = base64.b64encode('{}:'.format(token).encode()).decode()
        self.headers = {'Authorization': 'Basic ' + credencial}
        self.raiz_dav = self.base + '/public.php/webdav'

    def url_de(self, caminho):
        caminho = posixpath.join(self.caminho_inicial, caminho.strip('/')).strip('/')
        return self.raiz_dav + '/' + quote(caminho) + ('/' if caminho else '')

    def lista(self, caminho):
        url = self.url_de(caminho)
        headers = dict(self.headers)
        headers.update({'User-Agent': USER_AGENT, 'Depth': '1',
                        'Content-Type': 'application/xml'})
        req = Request(url, data=PROPFIND_BODY, headers=headers, method='PROPFIND')
        with abre_com_tentativas(lambda: urlopen(req, timeout=TIMEOUT)) as resp:
            xml = resp.read()
        return interpreta_propfind(xml, urlsplit(url).path, self.base)


def interpreta_propfind(xml, caminho_pedido, base):
    '''Converte a resposta multistatus do PROPFIND em lista de Item,
    sem a propria pasta listada.'''
    ns = {'d': 'DAV:'}
    raiz = ET.fromstring(xml)
    pedido = unquote(caminho_pedido).rstrip('/')
    itens = []
    for resp in raiz.findall('d:response', ns):
        href = resp.findtext('d:href', default='', namespaces=ns)
        caminho = unquote(urlsplit(href).path).rstrip('/')
        if caminho == pedido:
            continue
        prop = None
        for propstat in resp.findall('d:propstat', ns):
            if ' 200 ' in (propstat.findtext('d:status', default='', namespaces=ns) + ' '):
                prop = propstat.find('d:prop', ns)
                break
        if prop is None:
            continue
        pasta = prop.find('d:resourcetype/d:collection', ns) is not None
        tamanho = prop.findtext('d:getcontentlength', default='', namespaces=ns)
        itens.append(Item(posixpath.basename(caminho), pasta, urljoin(base + '/', href),
                          int(tamanho) if tamanho.isdigit() else None))
    return itens


class ListagemHTML(Servidor):
    '''Listagem de diretorio comum (Apache/nginx): links para subpastas
    terminam com "/".'''

    def __init__(self, url):
        self.url = url if url.endswith('/') else url + '/'

    def lista(self, caminho):
        url = urljoin(self.url, quote(caminho.strip('/')) + '/') if caminho else self.url
        req = Request(url, headers={'User-Agent': USER_AGENT})
        with abre_com_tentativas(lambda: urlopen(req, timeout=TIMEOUT)) as resp:
            html = resp.read().decode('utf-8', 'replace')
        return interpreta_listagem_html(html, url)


class _Links(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href')
            if href:
                self.links.append(href)


def interpreta_listagem_html(html, url):
    parser = _Links()
    parser.feed(html)
    base = urlsplit(url)
    itens = {}
    for href in parser.links:
        absoluto = urljoin(url, href)
        partes = urlsplit(absoluto)
        # So links para dentro da pasta listada (ignora "pasta pai", ordenacao etc.)
        if partes.netloc != base.netloc or partes.query or not partes.path.startswith(base.path):
            continue
        resto = partes.path[len(base.path):]
        if not resto or '/' in resto.rstrip('/'):
            continue
        pasta = resto.endswith('/')
        nome = unquote(resto.rstrip('/'))
        itens[nome] = Item(nome, pasta, urlunsplit((partes.scheme, partes.netloc, partes.path, '', '')))
    return list(itens.values())


def servidor_para(url):
    '''Escolhe o tipo de servidor pela URL.
    Nextcloud: https://host/index.php/s/<token>[?dir=/pasta] ou https://host/s/<token>'''
    partes = urlsplit(url)
    achou = re.search(r'^(.*?)/(?:index\.php/)?s/([A-Za-z0-9]+)/?$', partes.path)
    if achou:
        base = urlunsplit((partes.scheme, partes.netloc, achou.group(1), '', ''))
        query = parse_qs(partes.query)
        inicial = (query.get('dir') or query.get('path') or [''])[0]
        return NextcloudPublico(base, achou.group(2), inicial)
    return ListagemHTML(url)


def abre_com_tentativas(funcao, tentativas=TENTATIVAS):
    for tentativa in range(1, tentativas + 1):
        try:
            return funcao()
        except HTTPError as e:
            # Erros do cliente (404, 401...) nao adianta repetir
            if 400 <= e.code < 500 and e.code not in (408, 429):
                raise
            erro = e
        except (URLError, OSError, http.client.HTTPException) as e:
            erro = e
        if tentativa < tentativas:
            espera = 2 ** tentativa
            print('  Falha ({}). Nova tentativa em {}s...'.format(erro, espera), file=sys.stderr)
            time.sleep(espera)
    raise erro


# ---------------------------------------------------------------------------
# Escolha da competencia
# ---------------------------------------------------------------------------

def _sem_acento(texto):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFKD', texto)
                   if not unicodedata.combining(c)).lower()


def chave_data(nome):
    '''Interpreta o nome de uma pasta como data. Retorna:
    ('am', ano, mes) para "2026-10", "2026_10", "202610" ...
    ('a', ano) para "2026"
    ('m', mes) para "10", "10-outubro", "Outubro"
    None se o nome nao parece data.'''
    texto = _sem_acento(nome.strip())
    achou = re.search(r'(?<!\d)((?:19|20)\d{2})[-_. ]?(0[1-9]|1[0-2])(?!\d)', texto)
    if achou:
        return ('am', int(achou.group(1)), int(achou.group(2)))
    achou = re.fullmatch(r'((?:19|20)\d{2})', texto)
    if achou:
        return ('a', int(achou.group(1)))
    achou = re.match(r'(0?[1-9]|1[0-2])(?!\d)', texto)
    if achou:
        return ('m', int(achou.group(1)))
    for i, mes in enumerate(MESES):
        if mes in texto:
            return ('m', i + 1)
    return None


def compativel(chave, alvo):
    '''A pasta de chave "chave" leva a competencia alvo (ano, mes)?'''
    if alvo is None:
        return True
    if chave[0] == 'am':
        return (chave[1], chave[2]) == alvo
    if chave[0] == 'a':
        return chave[1] == alvo[0]
    return chave[1] == alvo[1]


def escolhe_pasta(pastas, alvo=None):
    '''Entre as pastas com nome de data, escolhe a mais recente (ou a do alvo).
    Da preferencia as pastas "ano-mes" sobre as so de ano ou de mes.'''
    candidatas = []
    for item in pastas:
        chave = chave_data(item.nome)
        if chave and compativel(chave, alvo):
            candidatas.append((chave, item))
    if not candidatas:
        return None
    for tipo in ('am', 'a', 'm'):
        do_tipo = [c for c in candidatas if c[0][0] == tipo]
        if do_tipo:
            return max(do_tipo, key=lambda c: c[0][1:])[1]


def localiza_competencia(servidor, alvo=None, max_niveis=4):
    '''Desce pelas pastas de data ate a pasta com os arquivos.
    Retorna (caminho, competencia "AAAA-MM" ou None, lista de arquivos).'''
    caminho = ''
    ano = mes = None
    for _ in range(max_niveis + 1):
        itens = servidor.lista(caminho)
        pastas = [i for i in itens if i.pasta]
        escolhida = escolhe_pasta(pastas, alvo)
        if escolhida is None:
            arquivos = [i for i in itens if not i.pasta]
            if not arquivos:
                break
            competencia = '{:04d}-{:02d}'.format(ano, mes) if ano and mes else None
            return caminho, competencia, sorted(arquivos, key=lambda i: i.nome)
        chave = chave_data(escolhida.nome)
        if chave[0] == 'am':
            ano, mes = chave[1], chave[2]
        elif chave[0] == 'a':
            ano = chave[1]
        else:
            mes = chave[1]
        caminho = posixpath.join(caminho, escolhida.nome)
        print('Entrando na pasta: {}'.format(caminho))

    if alvo:
        raise SystemExit(u'ERRO: competencia {:04d}-{:02d} nao encontrada no servidor.'.format(*alvo))
    raise SystemExit(u'ERRO: nenhuma pasta com arquivos encontrada no servidor.')


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def tamanho_legivel(n):
    if n is None:
        return '?'
    for unidade in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unidade == 'GB':
            return '{:.1f} {}'.format(n, unidade) if unidade != 'B' else '{} B'.format(n)
        n /= 1024.0


def zip_valido(caminho):
    '''Confere rapidamente se o ZIP esta inteiro (le o diretorio central).'''
    try:
        with zipfile.ZipFile(caminho) as zf:
            return bool(zf.namelist())
    except (zipfile.BadZipFile, OSError):
        return False


def baixa_arquivo(servidor, item, destino):
    '''Baixa um arquivo. Retorna "baixado" ou "existente".'''
    final = os.path.join(destino, item.nome)
    parcial = final + '.part'

    if os.path.exists(final):
        tamanho = os.path.getsize(final)
        if item.tamanho is None or tamanho == item.tamanho:
            if not item.nome.lower().endswith('.zip') or zip_valido(final):
                return 'existente'
        print('  Arquivo local diferente do servidor, baixando de novo.')
        os.remove(final)

    for tentativa in range(1, TENTATIVAS + 1):
        inicio = os.path.getsize(parcial) if os.path.exists(parcial) else 0
        if item.tamanho is not None and inicio > item.tamanho:
            os.remove(parcial)
            inicio = 0
        try:
            if item.tamanho is not None and inicio == item.tamanho:
                break
            resp = servidor.abre(item.url, inicio)
            with resp:
                # Servidor ignorou o Range: comeca do zero
                if inicio and getattr(resp, 'status', 200) != 206:
                    inicio = 0
                modo = 'ab' if inicio else 'wb'
                total = item.tamanho
                if total is None and resp.headers.get('Content-Length'):
                    total = inicio + int(resp.headers['Content-Length'])
                baixados = inicio
                ultimo = 0
                with open(parcial, modo) as saida:
                    while True:
                        bloco = resp.read(TAMANHO_BLOCO)
                        if not bloco:
                            break
                        saida.write(bloco)
                        baixados += len(bloco)
                        agora = time.time()
                        if agora - ultimo > 1:
                            ultimo = agora
                            pct = ' ({:.0f}%)'.format(100.0 * baixados / total) if total else ''
                            print('  {} de {}{}   '.format(tamanho_legivel(baixados),
                                                          tamanho_legivel(total), pct), end='\r')
            if total is not None and baixados < total:
                raise IOError('download incompleto ({} de {} bytes)'.format(baixados, total))
            break
        except HTTPError as e:
            if e.code == 416:  # Range invalido: arquivo .part ja completo ou maior
                os.remove(parcial)
                continue
            if 400 <= e.code < 500 and e.code not in (408, 429):
                raise
            erro = e
        except (URLError, OSError, http.client.HTTPException) as e:
            erro = e
        else:
            break
        if tentativa == TENTATIVAS:
            raise erro
        espera = 2 ** tentativa
        print('\n  Falha ({}). Continuando em {}s...'.format(erro, espera), file=sys.stderr)
        time.sleep(espera)

    if item.nome.lower().endswith('.zip') and not zip_valido(parcial):
        os.remove(parcial)
        raise IOError(u'{} baixado, mas o ZIP esta corrompido. Rode de novo.'.format(item.nome))

    os.replace(parcial, final)
    print()
    return 'baixado'


def baixa(url=URL_PADRAO, destino=PASTA_PADRAO, competencia=None, somente_listar=False,
          filtro=None):
    '''Baixa todos os arquivos da competencia mais recente (ou da informada).
    Retorna a pasta local com os arquivos.'''
    alvo = None
    if competencia:
        achou = re.fullmatch(r'(\d{4})-(\d{2})', competencia)
        if not achou:
            raise SystemExit(u'ERRO: competencia deve estar no formato AAAA-MM (ex: 2026-10).')
        alvo = (int(achou.group(1)), int(achou.group(2)))

    print('Servidor: {}'.format(url))
    servidor = servidor_para(url)
    caminho, comp, arquivos = localiza_competencia(servidor, alvo)
    if filtro:
        arquivos = [a for a in arquivos if re.search(filtro, a.nome, re.IGNORECASE)]

    nome_pasta = comp or posixpath.basename(caminho) or 'download'
    pasta_local = os.path.join(destino, nome_pasta)
    total = sum(a.tamanho or 0 for a in arquivos)
    print(u'Competencia: {}  ({} arquivos, {})'.format(
        comp or '(nao identificada)', len(arquivos), tamanho_legivel(total)))

    if somente_listar:
        for a in arquivos:
            print('  {:<30} {:>10}'.format(a.nome, tamanho_legivel(a.tamanho)))
        return pasta_local

    os.makedirs(pasta_local, exist_ok=True)
    print('Destino: {}'.format(os.path.abspath(pasta_local)))
    resumo = {'baixado': 0, 'existente': 0}
    for n, item in enumerate(arquivos, 1):
        print('[{}/{}] {} ({})'.format(n, len(arquivos), item.nome, tamanho_legivel(item.tamanho)))
        situacao = baixa_arquivo(servidor, item, pasta_local)
        if situacao == 'existente':
            print('  Ja baixado, pulando.')
        resumo[situacao] += 1

    print(u'\nDownload concluido: {} baixado(s), {} ja existente(s).'.format(
        resumo['baixado'], resumo['existente']))
    print(u'Para carregar: python cnpj_full/cnpj.py "{}" sqlite saida --dir'.format(pasta_local))
    return pasta_local


def main(argv=None):
    ambiente.carrega()
    parser = argparse.ArgumentParser(
        description='Baixa os dados abertos do CNPJ da Receita Federal '
                    '(competencia mais recente, ou a informada).')
    parser.add_argument('url', nargs='?', default=os.getenv('CNPJ_RF_URL') or URL_PADRAO,
                        help='URL do compartilhamento da RF (padrao: CNPJ_RF_URL do .env, '
                             'ou {})'.format(URL_PADRAO))
    parser.add_argument('--destino', default=os.getenv('CNPJ_PASTA_DOWNLOAD') or PASTA_PADRAO,
                        help='Pasta onde salvar; os arquivos vao para <destino>/<AAAA-MM>/ '
                             '(padrao: CNPJ_PASTA_DOWNLOAD do .env, ou "dados")')
    parser.add_argument('--competencia', metavar='AAAA-MM',
                        help='Baixa essa competencia em vez da mais recente')
    parser.add_argument('--listar', action='store_true',
                        help='So mostra a competencia e os arquivos, sem baixar')
    parser.add_argument('--filtro', metavar='REGEX',
                        help='Baixa so os arquivos cujo nome casa com a expressao (ex: "Cnaes|Paises")')
    args = parser.parse_args(argv)

    print('Inicio: {}'.format(datetime.datetime.now()))
    try:
        baixa(args.url, args.destino, args.competencia, args.listar, args.filtro)
    except HTTPError as e:
        raise SystemExit(u'ERRO HTTP {} em {}'.format(e.code, e.url))
    except URLError as e:
        raise SystemExit(u'ERRO de conexao: {}'.format(e.reason))
    print('Fim: {}'.format(datetime.datetime.now()))


if __name__ == '__main__':
    main()
