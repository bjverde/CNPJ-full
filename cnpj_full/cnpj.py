# -*- encoding: utf-8 -*-
'''
Nome antigo do script de carga. Foi renomeado para carga.py.
Este arquivo so repassa os argumentos, para nao quebrar comandos antigos.
'''
import os
import sys

if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cnpj_full.carga import *  # noqa: E402,F401,F403
from cnpj_full import carga as _carga  # noqa: E402

if __name__ == '__main__':
    print(u'AVISO: cnpj.py foi renomeado para carga.py. Use: python cnpj_full/carga.py ...\n',
          file=sys.stderr)
    _carga.main()
