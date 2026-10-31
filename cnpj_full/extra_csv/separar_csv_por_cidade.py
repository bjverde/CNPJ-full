import settings
import csv, codecs, os
from header_dict import get_header_index

location = os.getenv('FILES_LOCATION')

file = 'estabelecimento.csv'

with codecs.open(location + file,'r+','utf-8') as empresas:

    empresas = csv.reader(cleaned.replace('\0', '') for cleaned in empresas)

    next(empresas,None)

    count_sucesso = 0
    count_erro = 0

    if not os.path.exists(location + 'UFs/'):
        os.makedirs(location + 'UFs/')

    for empresa in empresas:

        uf = empresa[get_header_index('uf')]
        municipio = empresa[get_header_index('municipio')]

        if not os.path.exists(location + 'UFs/' + uf):
            os.makedirs(location + 'UFs/' + uf)

        try:
            uf_file = open(location + 'UFs/' + uf + "/" + municipio + ".csv", "a+")
        except:
            uf_file = open(location + 'UFs/' + uf + "/" + municipio + ".csv", "w+")

        try:
            uf_file.writelines('"' + '","'.join(empresa) + '"\n')
            count_sucesso += 1
        except:
            count_erro += 1
            print('Erros de processamento: {}'.format(count_erro),end='\r')

        print('Empresas processadas: {}'.format(count_sucesso),end='\r')
