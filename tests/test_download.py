# -*- encoding: utf-8 -*-
'''Testes do download, com um servidor local que imita o compartilhamento
publico do Nextcloud da RF (WebDAV) e uma listagem de diretorio comum.'''
import os
import io
import base64
import zipfile
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote, quote

import pytest

from cnpj_full import download

TOKEN = 'YggdBLfdninEJX9'


def _zip_bytes(nome):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zf:
        zf.writestr(nome + '.CSV', ('"1";"conteudo de ' + nome + '"\n') * 500)
    return buffer.getvalue()


# Estrutura do servidor: pastas (dict) e arquivos (bytes)
ARVORE = {
    '2026-09': {'Cnaes.zip': _zip_bytes('CNAE09'), 'Empresas0.zip': _zip_bytes('EMPRE09')},
    '2026-10': {'Cnaes.zip': _zip_bytes('CNAE10'), 'Empresas0.zip': _zip_bytes('EMPRE10'),
                'LEIA-ME.txt': b'texto'},
    '2025-12': {'Cnaes.zip': _zip_bytes('CNAE12')},
    'temp': {},
    'regime_tributario': {'x.zip': _zip_bytes('X')},
}

# Mesma ideia, com pasta por ano e subpasta por mes
ARVORE_ANO_MES = {
    '2025': {'12': {'Cnaes.zip': _zip_bytes('A2025')}},
    '2026': {'09': {'Cnaes.zip': _zip_bytes('A0926')},
             '10': {'Cnaes.zip': _zip_bytes('A1026'), 'Paises.zip': _zip_bytes('P1026')}},
}


def _no(arvore, caminho):
    no = arvore
    for parte in [p for p in caminho.split('/') if p]:
        no = no[parte]
    return no


class Handler(BaseHTTPRequestHandler):
    arvore = ARVORE
    sem_range = False
    corta_em = None  # corta a resposta do 1o GET nesse byte (simula queda)
    gets = []

    def log_message(self, *args):
        pass

    def _caminho_dav(self):
        prefixo = '/public.php/webdav'
        if not self.path.startswith(prefixo):
            return None
        return unquote(self.path[len(prefixo):])

    def _autorizado(self):
        esperado = 'Basic ' + base64.b64encode((TOKEN + ':').encode()).decode()
        return self.headers.get('Authorization') == esperado

    def do_PROPFIND(self):
        self.rfile.read(int(self.headers.get('Content-Length') or 0))
        caminho = self._caminho_dav()
        if caminho is None or not self._autorizado():
            return self.send_error(401)
        try:
            no = _no(self.arvore, caminho)
        except KeyError:
            return self.send_error(404)
        base = '/public.php/webdav/' + '/'.join(quote(p) for p in caminho.split('/') if p)
        base = base.rstrip('/') + '/'
        respostas = ['<d:response><d:href>{}</d:href><d:propstat><d:prop><d:resourcetype><d:collection/>'
                     '</d:resourcetype></d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
                     '</d:response>'.format(base)]
        for nome, filho in no.items():
            if isinstance(filho, dict):
                respostas.append('<d:response><d:href>{}{}/</d:href><d:propstat><d:prop><d:resourcetype>'
                                 '<d:collection/></d:resourcetype></d:prop><d:status>HTTP/1.1 200 OK'
                                 '</d:status></d:propstat></d:response>'.format(base, quote(nome)))
            else:
                respostas.append('<d:response><d:href>{}{}</d:href><d:propstat><d:prop><d:resourcetype/>'
                                 '<d:getcontentlength>{}</d:getcontentlength></d:prop><d:status>HTTP/1.1 '
                                 '200 OK</d:status></d:propstat></d:response>'.format(base, quote(nome), len(filho)))
        corpo = ('<?xml version="1.0"?><d:multistatus xmlns:d="DAV:">' + ''.join(respostas)
                 + '</d:multistatus>').encode()
        self.send_response(207)
        self.send_header('Content-Type', 'application/xml')
        self.send_header('Content-Length', str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        caminho = self._caminho_dav()
        if caminho is not None:
            if not self._autorizado():
                return self.send_error(401)
        else:
            # Listagem de diretorio comum em /dados/
            if not self.path.startswith('/dados/'):
                return self.send_error(404)
            caminho = unquote(self.path[len('/dados/'):])
        try:
            no = _no(self.arvore, caminho)
        except KeyError:
            return self.send_error(404)

        if isinstance(no, dict):
            links = ['<a href="../">Parent Directory</a>', '<a href="?C=N;O=D">Name</a>']
            links += ['<a href="{}{}">{}</a>'.format(quote(n), '/' if isinstance(f, dict) else '', n)
                      for n, f in no.items()]
            corpo = ('<html><body>' + '\n'.join(links) + '</body></html>').encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(corpo)))
            self.end_headers()
            return self.wfile.write(corpo)

        type(self).gets.append((caminho, self.headers.get('Range')))
        inicio = 0
        intervalo = self.headers.get('Range')
        if intervalo and not self.sem_range:
            inicio = int(intervalo.split('=')[1].rstrip('-'))
            self.send_response(206)
        else:
            self.send_response(200)
        dados = no[inicio:]
        self.send_header('Content-Length', str(len(dados)))
        self.end_headers()
        if type(self).corta_em is not None:
            corte, type(self).corta_em = type(self).corta_em, None
            self.wfile.write(dados[:corte])
            self.wfile.flush()
            self.close_connection = True
            return
        self.wfile.write(dados)


@pytest.fixture
def servidor(monkeypatch):
    monkeypatch.setattr(download.time, 'sleep', lambda s: None)
    Handler.arvore = ARVORE
    Handler.sem_range = False
    Handler.corta_em = None
    Handler.gets = []
    httpd = HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    # O servidor local nao deve passar pelo proxy do ambiente
    monkeypatch.setenv('NO_PROXY', '127.0.0.1')
    monkeypatch.setenv('no_proxy', '127.0.0.1')
    yield 'http://127.0.0.1:{}'.format(httpd.server_port)
    httpd.shutdown()


def test_chave_data():
    assert download.chave_data('2026-10') == ('am', 2026, 10)
    assert download.chave_data('2026_03') == ('am', 2026, 3)
    assert download.chave_data('202603') == ('am', 2026, 3)
    assert download.chave_data('Dados 2026-10') == ('am', 2026, 10)
    assert download.chave_data('2026') == ('a', 2026)
    assert download.chave_data('10') == ('m', 10)
    assert download.chave_data('03 - Março') == ('m', 3)
    assert download.chave_data('Dezembro') == ('m', 12)
    assert download.chave_data('temp') is None
    assert download.chave_data('regime_tributario') is None
    assert download.chave_data('13') is None


def test_escolhe_pasta_mais_recente_e_competencia():
    pastas = [download.Item(n, True, n) for n in ['2025-12', '2026-09', '2026-10', 'temp']]
    assert download.escolhe_pasta(pastas).nome == '2026-10'
    assert download.escolhe_pasta(pastas, (2025, 12)).nome == '2025-12'
    assert download.escolhe_pasta(pastas, (2024, 1)) is None
    meses = [download.Item(n, True, n) for n in ['1', '2', '10', '9']]
    assert download.escolhe_pasta(meses).nome == '10'


def test_servidor_para_url():
    s = download.servidor_para(download.URL_PADRAO)
    assert isinstance(s, download.NextcloudPublico)
    assert s.token == TOKEN
    assert s.url_de('2026-10') == 'https://arquivos.receitafederal.gov.br/public.php/webdav/2026-10/'
    s = download.servidor_para('https://host/index.php/s/abc123?dir=/Dados/CNPJ')
    assert s.url_de('2026-10') == 'https://host/public.php/webdav/Dados/CNPJ/2026-10/'
    assert isinstance(download.servidor_para('https://host/dados/cnpj/'), download.ListagemHTML)


def test_baixa_competencia_mais_recente(servidor, tmp_path):
    pasta = download.baixa(servidor + '/index.php/s/' + TOKEN, str(tmp_path))
    assert pasta == os.path.join(str(tmp_path), '2026-10')
    assert sorted(os.listdir(pasta)) == ['Cnaes.zip', 'Empresas0.zip', 'LEIA-ME.txt']
    with open(os.path.join(pasta, 'Cnaes.zip'), 'rb') as f:
        assert f.read() == ARVORE['2026-10']['Cnaes.zip']

    # Rodando de novo, nada e baixado
    Handler.gets = []
    download.baixa(servidor + '/index.php/s/' + TOKEN, str(tmp_path))
    assert Handler.gets == []


def test_baixa_competencia_informada_e_filtro(servidor, tmp_path):
    pasta = download.baixa(servidor + '/index.php/s/' + TOKEN, str(tmp_path), '2026-09',
                           filtro='cnae')
    assert pasta.endswith('2026-09')
    assert os.listdir(pasta) == ['Cnaes.zip']


def test_competencia_inexistente(servidor, tmp_path):
    with pytest.raises(SystemExit):
        download.baixa(servidor + '/index.php/s/' + TOKEN, str(tmp_path), '2020-01')


def test_listar_nao_baixa(servidor, tmp_path):
    pasta = download.baixa(servidor + '/index.php/s/' + TOKEN, str(tmp_path), somente_listar=True)
    assert not os.path.exists(pasta)


def test_pasta_por_ano_e_mes(servidor, tmp_path):
    Handler.arvore = ARVORE_ANO_MES
    pasta = download.baixa(servidor + '/index.php/s/' + TOKEN, str(tmp_path))
    assert pasta == os.path.join(str(tmp_path), '2026-10')
    assert sorted(os.listdir(pasta)) == ['Cnaes.zip', 'Paises.zip']


def test_listagem_html(servidor, tmp_path):
    pasta = download.baixa(servidor + '/dados/', str(tmp_path))
    assert pasta == os.path.join(str(tmp_path), '2026-10')
    assert sorted(os.listdir(pasta)) == ['Cnaes.zip', 'Empresas0.zip', 'LEIA-ME.txt']


def test_download_interrompido_continua(servidor, tmp_path):
    Handler.corta_em = 100
    pasta = download.baixa(servidor + '/index.php/s/' + TOKEN, str(tmp_path), filtro='Empresas')
    with open(os.path.join(pasta, 'Empresas0.zip'), 'rb') as f:
        assert f.read() == ARVORE['2026-10']['Empresas0.zip']
    # A segunda requisicao pediu so o que faltava
    assert Handler.gets[-1][1] == 'bytes=100-'
    assert not os.path.exists(os.path.join(pasta, 'Empresas0.zip.part'))


def test_servidor_sem_range_recomeca(servidor, tmp_path):
    Handler.sem_range = True
    pasta = os.path.join(str(tmp_path), '2026-10')
    os.makedirs(pasta)
    with open(os.path.join(pasta, 'Cnaes.zip.part'), 'wb') as f:
        f.write(b'lixo')
    download.baixa(servidor + '/index.php/s/' + TOKEN, str(tmp_path), filtro='Cnaes')
    with open(os.path.join(pasta, 'Cnaes.zip'), 'rb') as f:
        assert f.read() == ARVORE['2026-10']['Cnaes.zip']


def test_arquivo_local_diferente_baixa_de_novo(servidor, tmp_path):
    pasta = os.path.join(str(tmp_path), '2026-10')
    os.makedirs(pasta)
    with open(os.path.join(pasta, 'Cnaes.zip'), 'wb') as f:
        f.write(b'incompleto')
    download.baixa(servidor + '/index.php/s/' + TOKEN, str(tmp_path), filtro='Cnaes')
    with open(os.path.join(pasta, 'Cnaes.zip'), 'rb') as f:
        assert f.read() == ARVORE['2026-10']['Cnaes.zip']
