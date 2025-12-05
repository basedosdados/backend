# -*- coding: utf-8 -*-
RAIS_DATASET_SEARCH = {
    "status": "success",
    "results": [
        {
            "id": "3e7c4d58-96ba-448e-b053-d385a829ef00",
            "name": "Relação Anual de Informações Sociais (RAIS)",
            "slug": "rais",
            "description": "A Relação Anual de Informações Sociais (RAIS) é um relatório de informações socioeconômicas solicitado pela Secretaria de Trabalho do Ministério da Economia brasileiro às pessoas jurídicas e outros empregadores anualmente. Foi instituída pelo Decreto nº 76.900, de 23 de dezembro de 1975.",  # noqa: E501
            "tags": ["emprego", "trabalho"],
            "themes": ["Economia"],
            "organizations": ["Ministério da Economia (ME)"],
        },
        {
            "id": "562b56a3-0b01-4735-a049-eeac5681f056",
            "name": "Cadastro Geral de Empregados e Desempregados (CAGED)",
            "slug": "caged",
            "description": "O Cadastro Geral de Empregados e Desempregados – CAGED, instituído pela Lei nº 4.923, em 23 de dezembro de 1965, constitui fonte de informação de âmbito nacional e de periodicidade mensal. Foi criado como instrumento de acompanhamento e de fiscalização do processo de admissão e de dispensa de trabalhadores regidos pela CLT, com o objetivo de assistir os desempregados e de apoiar medidas contra o desemprego.\r\n\r\nO CAGED é um Registro Administrativo, e, inicialmente, objetivou gerir e controlar a concessão do auxílio-desemprego. A partir de 1986, passou a ser utilizado como suporte ao pagamento do seguro desemprego e, mais recentemente, tornou-se, também, um relevante instrumento à reciclagem profissional e à recolocação do trabalhador no mercado de trabalho e, ainda, um importante subsídio para a fiscalização.\r\n\r\nDevido à crescente demanda por dados conjunturais do mercado de trabalho e à necessidade deste Ministério em contar com estatísticas mais completas, mais consistentes e mais ágeis, foram implementadas expressivas alterações ao sistema – Lei nº 4.923/65. Como decorrência dos substanciais avanços, pôde-se construir, a partir de 1983, o índice mensal de emprego, a taxa de rotatividade e a flutuação da mão-de-obra (admitidos / desligados).\r\n\r\nOs aperfeiçoamentos ocorridos no sistema CAGED e também na metodologia de tratamento dos dados tornaram esse registro administrativo uma das principais fontes de informações estatísticas sobre o mercado de trabalho conjuntural. O CAGED apresenta desagregações idênticas às da RAIS, em termos geográficos, setoriais e ocupacionais, possibilitando a realização de estudos que indicam as tendências mais atuais. No espectro conjuntural, é a única fonte de informação com tal nível de desagregação, sendo, portanto, imprescindível para o balizamento das intervenções dos formuladores de políticas na esfera do mercado de trabalho, aumentando a eficácia e eficiência das políticas de emprego que possibilitam o aumento do número e da qualidade de postos de trabalho e, por conseguinte, a redução da desigualdade social.\r\n\r\nA qualidade das informações do CAGED vem apresentando significativa melhora. Concorreu para esse fato a implantação da Portaria nº 561/2001 que determinou a extinção da declaração do CAGED em formulário padrão a partir da competência de novembro de 2001. Esta medida teve um impacto positivo na qualidade, uma vez que as informações declaradas, em meios eletrônicos, passam por um processo de críticas. Ademais, a implantação da recepção do CAGED, via Internet, possibilitou, também, um ganho na tempestividade.",  # noqa: E501
            "tags": ["emprego", "empresa", "firma", "trabalho"],
            "themes": ["Economia"],
            "organizations": ["Ministério da Economia (ME)"],
        },
    ],
}

RAIS_DATASET_DETAILS = {
    "status": "success",
    "results": {
        "id": "DatasetNode:3e7c4d58-96ba-448e-b053-d385a829ef00",
        "name": "Relação Anual de Informações Sociais (RAIS)",
        "slug": "rais",
        "description": "A Relação Anual de Informações Sociais (RAIS) é um relatório de informações socioeconômicas solicitado pela Secretaria de Trabalho do Ministério da Economia brasileiro às pessoas jurídicas e outros empregadores anualmente. Foi instituída pelo Decreto nº 76.900, de 23 de dezembro de 1975.",  # noqa: E501
        "tags": ["emprego", "trabalho"],
        "themes": ["Economia"],
        "organizations": ["Ministério da Economia (ME)"],
        "tables": [
            {
                "id": "TableNode:c3a5121e-f00d-41ff-b46f-bd26be8d4af3",
                "gcp_id": "basedosdados.br_me_rais.dicionario",
                "name": "Dicionário",
                "slug": "dicionario",
                "description": "Dicionário para tradução dos códigos das tabelas do do conjunto Relação Anual de Informações Sociais (RAIS). Para códigos definidos por outras instituições, como id_municipio ou cnaes, buscar por diretórios",  # noqa: E501
                "temporal_coverage": {"start": None, "end": None},
                "columns": [
                    {"name": "chave", "type": "STRING", "description": "Chave"},
                    {
                        "name": "cobertura_temporal",
                        "type": "STRING",
                        "description": "Cobertura Temporal",
                    },
                    {"name": "id_tabela", "type": "STRING", "description": "ID Tabela"},
                    {"name": "nome_coluna", "type": "STRING", "description": "Nome da coluna"},
                    {"name": "valor", "type": "STRING", "description": "Valor"},
                ],
            },
            {
                "id": "TableNode:86b69f96-0bfe-45da-833b-6edc9a0af213",
                "gcp_id": "basedosdados.br_me_rais.microdados_estabelecimentos",
                "name": "Microdados Estabelecimentos",
                "slug": "microdados_estabelecimentos",
                "description": "Microdados de estabelecimentos da RAIS.",
                "temporal_coverage": {"start": "1985", "end": "2024"},
                "columns": [
                    {"name": "ano", "type": "INT64", "description": "Ano"},
                    {
                        "name": "bairros_fortaleza",
                        "type": "STRING",
                        "description": "Bairros do município de Fortaleza",
                    },
                    {
                        "name": "bairros_rj",
                        "type": "STRING",
                        "description": "Bairros do município do Rio de Janeiro",
                    },
                    {
                        "name": "bairros_sp",
                        "type": "STRING",
                        "description": "Bairros do Municipio de São Paulo",
                    },
                    {
                        "name": "cep",
                        "type": "STRING",
                        "description": "Código de Endereçamento Postal",
                    },
                    {
                        "name": "cnae_1",
                        "type": "STRING",
                        "description": "Código Nacional de Atividades Econômicas 1.0",
                    },
                    {
                        "name": "cnae_2",
                        "type": "STRING",
                        "description": "Código Nacional de Atividades Econômicas 2.0",
                    },
                    {
                        "name": "cnae_2_subclasse",
                        "type": "STRING",
                        "description": "Subclasse do Código Nacional de Atividades Econômicas 2.0",
                    },
                    {
                        "name": "distritos_sp",
                        "type": "STRING",
                        "description": "Distritos do município de São Paulo",
                    },
                    {
                        "name": "id_municipio",
                        "type": "STRING",
                        "description": "ID Município - IBGE 7 Dígitos",
                    },
                    {
                        "name": "indicador_atividade_ano",
                        "type": "INT64",
                        "description": "Indicador de estabelecimento/entidade que exerceu atividade durante o ano de referência.",  # noqa: E501
                    },
                    {
                        "name": "indicador_cei_vinculado",
                        "type": "INT64",
                        "description": "Indicador de CEI vinculado.",
                    },
                    {
                        "name": "indicador_pat",
                        "type": "INT64",
                        "description": "Indicador de estabelecimento pertencente ao PAT.",
                    },
                    {
                        "name": "indicador_rais_negativa",
                        "type": "INT64",
                        "description": "Indicador de Rais Negativa.",
                    },
                    {
                        "name": "indicador_simples",
                        "type": "INT64",
                        "description": "Indicador de optante pelo SIMPLES.",
                    },
                    {
                        "name": "natureza_estabelecimento",
                        "type": "STRING",
                        "description": "Natureza do Estabelecimento",
                    },
                    {
                        "name": "natureza_juridica",
                        "type": "STRING",
                        "description": "Natureza jurídica (CONCLA/2002)",
                    },
                    {
                        "name": "quantidade_vinculos_ativos",
                        "type": "INT64",
                        "description": "Estoque de vínculos ativos em 31/12.",
                    },
                    {
                        "name": "quantidade_vinculos_clt",
                        "type": "INT64",
                        "description": "Estoque de vínculos, sob o regime CLT e Outros, ativos em 31/12",  # noqa: E501
                    },
                    {
                        "name": "quantidade_vinculos_estatutarios",
                        "type": "INT64",
                        "description": "Estoque de vínculos, sob o regime estatutário, ativos em 31/12",  # noqa: E501
                    },
                    {
                        "name": "regioes_administrativas_df",
                        "type": "STRING",
                        "description": "Regiões Administrativas do Distrito Federal",
                    },
                    {
                        "name": "sigla_uf",
                        "type": "STRING",
                        "description": "Sigla da Unidade da Federação",
                    },
                    {
                        "name": "subatividade_ibge",
                        "type": "STRING",
                        "description": "Subatividade IBGE",
                    },
                    {"name": "subsetor_ibge", "type": "STRING", "description": "Subsetor IBGE"},
                    {
                        "name": "tamanho_estabelecimento",
                        "type": "STRING",
                        "description": "Tamanho - empregados ativos em 31/12.",
                    },
                    {
                        "name": "tipo_estabelecimento",
                        "type": "STRING",
                        "description": "Tipo do Estabelecimento",
                    },
                ],
            },
            {
                "id": "TableNode:dabe5ea8-3bb5-4a3e-9d5a-3c7003cd4a60",
                "gcp_id": "basedosdados.br_me_rais.microdados_vinculos",
                "name": "Microdados Vínculos",
                "slug": "microdados_vinculos",
                "description": "Microdados públicos dos vínculos de emprego na RAIS. Base desidentificada, isto é, que não inclui identificadores únicos de linha. Cada linha representa um vínculo - por isso indicamos este como nível de observação mesmo que não conste como coluna.",  # noqa: E501
                "temporal_coverage": {"start": "1985", "end": "2024"},
                "columns": [
                    {"name": "ano", "type": "INT64", "description": "Ano"},
                    {
                        "name": "ano_chegada_brasil",
                        "type": "INT64",
                        "description": "Ano de Chegada no Brasil",
                    },
                    {
                        "name": "bairros_fortaleza",
                        "type": "STRING",
                        "description": "Bairros em Fortaleza",
                    },
                    {
                        "name": "bairros_rj",
                        "type": "STRING",
                        "description": "Bairros no Rio de Janeiro",
                    },
                    {"name": "bairros_sp", "type": "STRING", "description": "Bairros em São Paulo"},
                    {
                        "name": "causa_desligamento_1",
                        "type": "STRING",
                        "description": "Causa 1 do Desligamento",
                    },
                    {
                        "name": "causa_desligamento_2",
                        "type": "STRING",
                        "description": "Causa 2 do Desligamento",
                    },
                    {
                        "name": "causa_desligamento_3",
                        "type": "STRING",
                        "description": "Causa 3 do Desligamento",
                    },
                    {
                        "name": "cbo_1994",
                        "type": "STRING",
                        "description": "Classificação Brasileira de Ocupações (CBO) 1994",
                    },
                    {
                        "name": "cbo_2002",
                        "type": "STRING",
                        "description": "Classificação Brasileira de Ocupações (CBO) 2002",
                    },
                    {
                        "name": "cnae_1",
                        "type": "STRING",
                        "description": "Classificação Nacional de Atividades Econômicas (CNAE) 1.0",
                    },
                    {
                        "name": "cnae_2",
                        "type": "STRING",
                        "description": "Classificação Nacional de Atividades Econômicas (CNAE) 2.0",
                    },
                    {
                        "name": "cnae_2_subclasse",
                        "type": "STRING",
                        "description": "Classificação Nacional de Atividades Econômicas (CNAE) 2.0 Subclasse",  # noqa: E501
                    },
                    {
                        "name": "distritos_sp",
                        "type": "STRING",
                        "description": "Distritos em São Paulo",
                    },
                    {"name": "faixa_etaria", "type": "STRING", "description": "Faixa Etária"},
                    {
                        "name": "faixa_horas_contratadas",
                        "type": "STRING",
                        "description": "Faixa Horas Contratadas",
                    },
                    {
                        "name": "faixa_remuneracao_dezembro_sm",
                        "type": "STRING",
                        "description": "Faixa Remuneração em Dezembro (Salários Mínimos)",
                    },
                    {
                        "name": "faixa_remuneracao_media_sm",
                        "type": "STRING",
                        "description": "Faixa Remuneração Média (Salários Mínimos)",
                    },
                    {
                        "name": "faixa_tempo_emprego",
                        "type": "STRING",
                        "description": "Faixa Tempo Emprego",
                    },
                    {
                        "name": "grau_instrucao_1985_2005",
                        "type": "STRING",
                        "description": "Grau de Instrução 1985-2005",
                    },
                    {
                        "name": "grau_instrucao_apos_2005",
                        "type": "STRING",
                        "description": "Grau de Instrução Após 2005",
                    },
                    {"name": "idade", "type": "INT64", "description": "Idade"},
                    {
                        "name": "id_municipio",
                        "type": "STRING",
                        "description": "ID Município - IBGE 7 Dígitos",
                    },
                    {
                        "name": "id_municipio_trabalho",
                        "type": "STRING",
                        "description": "ID Município de Trabalho - IBGE 7 Dígitos",
                    },
                    {
                        "name": "indicador_cei_vinculado",
                        "type": "STRING",
                        "description": "Indicador CEI Vinculado",
                    },
                    {
                        "name": "indicador_portador_deficiencia",
                        "type": "STRING",
                        "description": "Indicador de Portador de Deficiência",
                    },
                    {
                        "name": "indicador_simples",
                        "type": "STRING",
                        "description": "Indicador do Simples",
                    },
                    {
                        "name": "indicador_trabalho_intermitente",
                        "type": "STRING",
                        "description": "Indicador Trabalho Intermitente",
                    },
                    {
                        "name": "indicador_trabalho_parcial",
                        "type": "STRING",
                        "description": "Indicador Trabalho Parcial",
                    },
                    {"name": "mes_admissao", "type": "INT64", "description": "Mês de Admissão"},
                    {
                        "name": "mes_desligamento",
                        "type": "INT64",
                        "description": "Mês de Desligamento",
                    },
                    {
                        "name": "motivo_desligamento",
                        "type": "STRING",
                        "description": "Motivo do Desligamento",
                    },
                    {"name": "nacionalidade", "type": "STRING", "description": "Nacionalidade"},
                    {
                        "name": "natureza_juridica",
                        "type": "STRING",
                        "description": "Natureza Jurídica do Estabelecimento",
                    },
                    {
                        "name": "quantidade_dias_afastamento",
                        "type": "INT64",
                        "description": "Quantidade de Dias sob Afastamento",
                    },
                    {
                        "name": "quantidade_horas_contratadas",
                        "type": "INT64",
                        "description": "Quantidade de Horas Contratadas",
                    },
                    {"name": "raca_cor", "type": "STRING", "description": "Raça ou Cor"},
                    {
                        "name": "regioes_administrativas_df",
                        "type": "STRING",
                        "description": "Regiões Administrativas no Distrito Federal",
                    },
                    {"name": "sexo", "type": "STRING", "description": "Sexo"},
                    {
                        "name": "sigla_uf",
                        "type": "STRING",
                        "description": "Sigla da Unidade da Federação",
                    },
                    {
                        "name": "subatividade_ibge",
                        "type": "STRING",
                        "description": "Subatividade - IBGE",
                    },
                    {"name": "subsetor_ibge", "type": "STRING", "description": "Subsetor - IBGE"},
                    {
                        "name": "tamanho_estabelecimento",
                        "type": "STRING",
                        "description": "Tamanho do Estabelecimento",
                    },
                    {"name": "tempo_emprego", "type": "FLOAT64", "description": "Tempo Emprego"},
                    {"name": "tipo_admissao", "type": "STRING", "description": "Tipo da Admissão"},
                    {
                        "name": "tipo_deficiencia",
                        "type": "STRING",
                        "description": "Tipo da Deficiência",
                    },
                    {
                        "name": "tipo_estabelecimento",
                        "type": "STRING",
                        "description": "Tipo do Estabelecimento",
                    },
                    {"name": "tipo_salario", "type": "STRING", "description": "Tipo do Salário"},
                    {"name": "tipo_vinculo", "type": "STRING", "description": "Tipo do Vínculo"},
                    {
                        "name": "valor_remuneracao_abril",
                        "type": "FLOAT64",
                        "description": "Valor da Remuneração em Abril",
                    },
                    {
                        "name": "valor_remuneracao_agosto",
                        "type": "FLOAT64",
                        "description": "Valor da Remuneração em Agosto",
                    },
                    {
                        "name": "valor_remuneracao_dezembro",
                        "type": "FLOAT64",
                        "description": "Valor da Remuneração em Dezembro",
                    },
                    {
                        "name": "valor_remuneracao_dezembro_sm",
                        "type": "FLOAT64",
                        "description": "Valor da Remuneração em Dezembro (Salários Mínimos)",
                    },
                    {
                        "name": "valor_remuneracao_fevereiro",
                        "type": "FLOAT64",
                        "description": "Valor da Remuneração em Fevereiro",
                    },
                    {
                        "name": "valor_remuneracao_janeiro",
                        "type": "FLOAT64",
                        "description": "Valor da Remuneração em Janeiro",
                    },
                    {
                        "name": "valor_remuneracao_julho",
                        "type": "FLOAT64",
                        "description": "Valor da Remuneração em Julho",
                    },
                    {
                        "name": "valor_remuneracao_junho",
                        "type": "FLOAT64",
                        "description": "Valor da Remuneração em Junho",
                    },
                    {
                        "name": "valor_remuneracao_maio",
                        "type": "FLOAT64",
                        "description": "Valor da Remuneração em Maio",
                    },
                    {
                        "name": "valor_remuneracao_marco",
                        "type": "FLOAT64",
                        "description": "Valor da Remuneração em Março",
                    },
                    {
                        "name": "valor_remuneracao_media",
                        "type": "FLOAT64",
                        "description": "Valor da Remuneração Média",
                    },
                    {
                        "name": "valor_remuneracao_media_sm",
                        "type": "FLOAT64",
                        "description": "Valor da Remuneração Média (Salários Mínimos)",
                    },
                    {
                        "name": "valor_remuneracao_novembro",
                        "type": "FLOAT64",
                        "description": "Valor da Remuneração em Novembro",
                    },
                    {
                        "name": "valor_remuneracao_outubro",
                        "type": "FLOAT64",
                        "description": "Valor da Remuneração em Outubro",
                    },
                    {
                        "name": "valor_remuneracao_setembro",
                        "type": "FLOAT64",
                        "description": "Valor da Remuneração em Setembro",
                    },
                    {
                        "name": "valor_salario_contratual",
                        "type": "FLOAT64",
                        "description": "Valor Contratual do Salário",
                    },
                    {
                        "name": "vinculo_ativo_3112",
                        "type": "STRING",
                        "description": "Vínculo Ativo no dia 31/12",
                    },
                ],
            },
        ],
        "usage_guide": '---\ntitle: Guia de uso da RAIS\ndescription: >-\n  Guia de uso da Relação Anual de Informações Sociais (RAIS). Este material contém informações sobre as variáveis mais importantes, perguntas frequentes e exemplos de uso do conjunto da RAIS \ndate:\n  created: "2024-11-28T18:18:06.419Z"\nthumbnail: \ncategories: [guia-de-uso]\nauthors:\n  - name: Laura Amaral\n    role: Texto\n---\n\n# Introdução\n\n> O guia contém informações detalhadas sobre os dados. Para dúvidas sobre acesso ou uso da plataforma, consulte nossa [página de Perguntas Frequentes](/faq).\n\nEste conjunto de dados possui duas tabelas de microdados: \n- **Microdados Estabelecimentos:** Cada linha representa um estabelecimento em um ano específico. As colunas mostram detalhes sobre a empresa e seus empregados.\n- **Microdados Vínculos:** Cada linha representa um vínculo de trabalho em um ano específico. As colunas mostram informações sobre o vínculo, o empregado e a empresa contratante.\n\n# Considerações para análises\n## Vínculos e filtragem de dados\nA tabela de vínculos mostra todos os vínculos registrados por uma empresa durante o ano. Se um empregado for demitido e outro contratado no mesmo ano, ambos terão uma registro de vínculo para a mesma posição. Para contar os empregados ativos em um setor ou região, use a coluna `vinculo_ativo_3112`.\n\n## Informações de endereço\nA RAIS não possui informações sobre o endereço dos empregados. A coluna `id_municipio` se refere ao município da empresa, e a coluna `id_municipio_trabalho` se refere ao município onde o trabalhador presta serviços, caso seja diferente.\n\n## Dados parciais e dados completos\nA RAIS é divulgada duas vezes ao ano. Entre a divulgação parcial (setembro) e a completa (início do ano seguinte), o último ano da série sempre aparece com menos registros. Por exemplo, em novembro de 2025, o ano de 2024 mostra cerca de 46 milhões de vínculos, enquanto 2022 e 2023 têm mais de 50 milhões. Isso não significa que o número de vínculos caiu — só quer dizer que os dados de 2024 ainda não foram totalmente liberados.\n\n# Limitações\nOs dados são limitados a trabalhadores com vínculo formal e não incluem trabalhadores informais ou autônomos. Os dados públicos são anonimizados.\n\n# Inconsistências\n## Colunas `quantidade_vinculos_ativos` e `tamanho_estabelecimento`\nHá discrepâncias entre as colunas `quantidade_vinculos_ativos` e `tamanho_estabelecimento`. A primeira mostra o total de vínculos, enquanto a segunda classifica o estabelecimento por número de vínculos. Em alguns casos, a quantidade de vínculos não corresponde à categoria do tamanho do estabelecimento.\n\n## Vínculos de trabalho na RAIS e no CAGED\nA RAIS registra vínculos de trabalho anualmente e o CAGED registra movimentações durante o ano. Teoricamente, somando ou subtraindo as movimentações do CAGED ao total de vínculos da RAIS, seria possível calcular o total do ano seguinte, mas isso não acontece. Como os sistemas operam de forma independente, as divergências podem ser causadas por erros acumulados em cada um. \n\n## Coluna id_municipio_trabalho\nA coluna `id_municipio_trabalho` está preenchida apenas entre 2005-2011 e 2017-2021. Não se sabe o motivo.  \n\n## Dados desatualizados\nÀs vezes, os dados da RAIS são atualizados fora do calendário esperado e nossa equipe nem sempre fica sabendo. Se você está confiante de que está fazendo as queries corretas, entre em contato conosco enviando a query e a diferença com o site oficial, para que possamos avaliar a situação e, se necessário, corrigir.  \n\n# Observações ao longo tempo\nA cada ano, o conjunto de dados é atualizado, fazendo com que um estabelecimento ou vínculo apareça em todos os anos em que esteve ativo. Como os dados são anonimizados, não é possível acompanhar a evolução de vínculos ou empresas ao longo do tempo, mas é possível analisar o número de empregados com carteira de trabalho em diferentes setores ou locais.\n\n# Linhas duplicadas\nNão foram encontradas linhas duplicadas neste conjunto de dados. No entanto, a tabela Microdados Vínculos inclui todos os vínculos de uma empresa, então, se um empregado foi demitido e outro contratado no mesmo ano, terão duas linhas para a mesma posição.\n\n# Cruzamentos\nOs dados são anonimizadas, não contendo CNPJs nem CPFs. Isso limita os cruzamentos com outros conjuntos, mas é possível usar colunas como `cnae` e `cep` para tal.\n\n# Download dos dados\nOs microdados somam mais de 350 GB. Para evitar sobrecarregar seu computador, recomendamos usar queries no BigQuery para processar os dados em nuvem antes de baixá-los. Filtre pelas colunas de partição (como `ano` e `sigla_uf`) e selecione apenas as colunas relevantes.\n\n# Instrumento de coleta\nO instrumento de coleta atual é um formulário que deve ser preenchido pelos empregadores sobre seus empregados.\n\n# Mudanças na coleta\nAlgumas colunas foram adicionadas ou retiradas ao longo do tempo. A partir do ano de 2022 as empresas do grupo 3 do eSocial ficaram desobrigadas a declarar a RAIS pelo seu programa usual. Assim não é recomendável a comparação dos resultados desse ano com os resultados do anos anteriores.\n\n# Atualizações\nOs dados têm atualização parcial e completa. A atualização parcial ocorre em setembro do ano de coleta e a completa ocorre até o início do ano seguinte ao ano de coleta. Isso significa que os dados referentes a 2023, que foram coletados em 2024, ficaram parcialmente disponíveis em setembro de 2024 e a versão completa foi disponibilizada até o início de 2025. Às vezes, a atualização pode ocorrer fora do calendário previsto. Se perceber que os dados estão desatualizados, entre em contato com nossa equipe.\n\n# Dados identificados\nOs dados são anonimizados, não contendo CNPJs nem CPFs. Para obter dados identificados da RAIS, é necessário solicitar ao MTE. O processo pode ser demorado e não há garantia de aprovação.\n\n# Tratamentos feitos pela BD\nNeste guia, os tratamentos são descritos em uma linguagem mais acessível. De maneira complementar, os [códigos de tratamento](https://github.com/basedosdados/queries-basedosdados/tree/main/models/br_me_rais/code) e as [modificações feitas no BigQuery](https://github.com/basedosdados/queries-basedosdados/tree/main/models/br_me_rais) estão disponíveis no repositório do GitHub para consulta. \nOs tratamentos realizados foram: \n* Adequação das colunas que identificam municípios ao formato ID Município IBGE (7 dígitos);\n* Adequação das colunas que identificam Unidades Federativas ao padrão de sigla UF;\n* Substituição de códigos inválidos (como “9999” ou “000”) por valores nulos nas colunas de `bairros`, `cbo`, `cnae` e `ano`;\n* Padronização dos códigos na coluna `tipo_estabelecimento` para garantir consistência entre diferentes anos.\n\n# Materiais de apoio\n* [Manual de orientação para os empregadores sobre como preencher os campos do formulário](http://www.rais.gov.br/sitio/rais_ftp/ManualRAIS2023.pdf)\n* [Informações detalhadas sobre a RAIS no site do MTE](http://www.rais.gov.br/sitio/sobre.jsf)\n* [Dashboard do MTE com números consolidados da RAIS completa](https://app.powerbi.com/view?r=eyJrIjoiZmJmMDVhODctMTEwOS00YTVhLWJhNzItOWE3NmVlMWEwMTUxIiwidCI6IjNlYzkyOTY5LTVhNTEtNGYxOC04YWM5LWVmOThmYmFmYTk3OCJ9)\n* [Dashboard do MTE com números consolidados da RAIS parcial](https://app.powerbi.com/view?r=eyJrIjoiNjk3M2IwZDYtOGQzMS00YmE1LWE3M2MtZWRjODA4NTk3YTQ2IiwidCI6IjNlYzkyOTY5LTVhNTEtNGYxOC04YWM5LWVmOThmYmFmYTk3OCJ9)',  # noqa: E501
    },
}

RAIS_DECODE_SEXO = {
    "status": "success",
    "results": [
        {"nome_coluna": "sexo", "chave": "-1", "valor": "Ignorado"},
        {"nome_coluna": "sexo", "chave": "1", "valor": "Masculino"},
        {"nome_coluna": "sexo", "chave": "2", "valor": "Feminino"},
        {
            "nome_coluna": "sexo",
            "chave": "9",
            "valor": "Código não encontrado nos dicionários oficiais.",
        },
    ],
}

RAIS_DECODE_VINCULO_ATIVO = {
    "status": "success",
    "results": [
        {"nome_coluna": "vinculo_ativo_3112", "chave": "0", "valor": "Não"},
        {"nome_coluna": "vinculo_ativo_3112", "chave": "1", "valor": "Sim"},
    ],
}

RAIS_FINAL_RESPONSE = """Esta consulta SQL calcula a proporção de mulheres no mercado de trabalho formal brasileiro para o ano mais recente disponível, 2024, utilizando os dados da Relação Anual de Informações Sociais (RAIS). Ela considera apenas os vínculos de trabalho ativos em 31 de dezembro de 2024.

```sql
SELECT
    ano,
    COUNTIF(sexo = '2') AS total_mulheres_formal, -- Conta o número de mulheres no mercado formal
    COUNT(*) AS total_vinculos_formal, -- Conta o número total de vínculos formais
    SAFE_DIVIDE(COUNTIF(sexo = '2'), COUNT(*)) AS proporcao_mulheres_formal -- Calcula a proporção de mulheres
FROM
    basedosdados.br_me_rais.microdados_vinculos AS t
WHERE
    ano = 2024 -- Filtra para o ano mais recente disponível
    AND vinculo_ativo_3112 = '1' -- Considera apenas vínculos ativos em 31/12
GROUP BY
    ano
ORDER BY
    ano DESC
```

A consulta seleciona o ano, conta o total de vínculos formais ativos, o total de vínculos formais ativos de mulheres e, em seguida, calcula a proporção de mulheres no mercado de trabalho formal. Os dados são filtrados para o ano de 2024 e incluem apenas os vínculos que estavam ativos em 31 de dezembro daquele ano, garantindo uma representação precisa do mercado de trabalho formal.

Você pode adaptar esta consulta para:
*   Analisar outros anos, alterando o valor no filtro `WHERE ano = 2024`.
*   Incluir outras dimensões, como `sigla_uf` ou `id_municipio`, adicionando-as ao `SELECT` e ao `GROUP BY` para obter a proporção por estado ou município.
*   Explorar a proporção de mulheres em setores específicos, adicionando filtros ou agrupamentos por colunas como `cnae_2_subclasse`.
"""  # noqa: E501
