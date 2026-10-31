def get_header_index(column):
    # Colunas do arquivo estabelecimento.csv gerado pelo cnpj.py
    header = {
        'cnpj_basico': 0,
        'cnpj_ordem': 1,
        'cnpj_dv': 2,
        'identificador_matriz_filial': 3,
        'nome_fantasia': 4,
        'situacao_cadastral': 5,
        'data_situacao_cadastral': 6,
        'motivo_situacao_cadastral': 7,
        'nome_cidade_exterior': 8,
        'pais': 9,
        'data_inicio_atividade': 10,
        'cnae_fiscal_principal': 11,
        'cnae_fiscal_secundaria': 12,
        'tipo_logradouro': 13,
        'logradouro': 14,
        'numero': 15,
        'complemento': 16,
        'bairro': 17,
        'cep': 18,
        'uf': 19,
        'municipio': 20,
        'ddd_1': 21,
        'telefone_1': 22,
        'ddd_2': 23,
        'telefone_2': 24,
        'ddd_fax': 25,
        'fax': 26,
        'correio_eletronico': 27,
        'situacao_especial': 28,
        'data_situacao_especial': 29
    }

    return header[column]