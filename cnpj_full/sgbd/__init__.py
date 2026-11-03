# -*- encoding: utf-8 -*-
'''
Destinos de carga em SGBDs (alem do SQLite, que fica em carga.py).

Cada SGBD tem um modulo com uma classe Destino<SGBD> com a mesma interface:

    destino = Destino(config)            # conecta (config: dict, ver configuracao())
    destino.cria_tabelas(tabelas)        # recria as tabelas e a controle_carga
    destino.prepara_continuacao(tabelas) # -> (concluidos, totais), para --continuar
    destino.grava_arquivo(tabela, caminho, membro, totais)
    destino.verificacao()                # -> linhas da controle_carga (dicts)
    destino.cria_indices()
    destino.fecha()

Para incluir um novo SGBD (MySQL, SQL Server, Oracle...), crie um modulo
seguindo o postgres.py e registre-o em DESTINOS.
'''
import os

DESTINOS = {
    'postgres': 'cnpj_full.sgbd.postgres',
}

SINONIMOS = {
    'postgresql': 'postgres',
    'pgsql': 'postgres',
    'pg': 'postgres',
}


def nome_destino(tipo):
    tipo = (tipo or '').lower()
    return SINONIMOS.get(tipo, tipo)


def configuracao():
    '''Le a conexao das variaveis de ambiente / .env (veja .env.example).'''
    return {
        'host': os.getenv('CNPJ_DB_HOST') or 'localhost',
        'porta': os.getenv('CNPJ_DB_PORTA') or '',
        'nome': os.getenv('CNPJ_DB_NOME') or 'dados_rfb',
        'usuario': os.getenv('CNPJ_DB_USUARIO') or '',
        'senha': os.getenv('CNPJ_DB_SENHA') or '',
        'schema': os.getenv('CNPJ_DB_SCHEMA') or '',
    }


def abre_destino(tipo, config=None):
    import importlib
    tipo = nome_destino(tipo)
    if tipo not in DESTINOS:
        raise ValueError('SGBD nao suportado: {}'.format(tipo))
    modulo = importlib.import_module(DESTINOS[tipo])
    return modulo.Destino(config or configuracao())
