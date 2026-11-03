# -*- encoding: utf-8 -*-
'''
Leitura do arquivo .env com as configuracoes (download e banco de dados).

O .env fica na raiz do projeto (ao lado do README.md). Variaveis ja
definidas no ambiente (ex: docker-compose, export no shell) tem prioridade
sobre o .env. Veja o .env.example.
'''
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQUIVO_ENV = os.path.join(RAIZ, '.env')


def carrega(arquivo=None):
    '''Carrega o .env (se existir e se o python-dotenv estiver instalado).'''
    arquivo = arquivo or os.getenv('CNPJ_ENV') or ARQUIVO_ENV
    if not os.path.isfile(arquivo):
        return False
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False
    return load_dotenv(arquivo, override=False)
