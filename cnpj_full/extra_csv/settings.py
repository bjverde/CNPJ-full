# settings.py
# Carrega o .env da raiz do projeto (ou o indicado em CNPJ_ENV) e define a
# pasta do estabelecimento.csv (FILES_LOCATION, relativa a raiz do projeto).
import os
from dotenv import load_dotenv

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.getenv('CNPJ_ENV') or os.path.join(RAIZ, '.env'))

# os.path.join(..., '') garante a barra no final, com ou sem ela no .env
LOCATION = os.path.join(RAIZ, os.path.expanduser(os.getenv('FILES_LOCATION') or 'saida'), '')
