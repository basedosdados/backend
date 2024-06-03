# -*- coding: utf-8 -*-

from enum import Enum


class WorkArea(str, Enum):
    TECNOLOGIA = "Tecnologia"
    SAUDE = "Saúde"
    FINANCEIRO = "Financeiro"
    EDUCACAO = "Educação"
    VAREJO = "Varejo"
    ENERGIA = "Energia"
    JORNALISMO = "Jornalismo"
    OUTRA = "Outra"

    @classmethod
    def as_choices(cls):
        return [(i.name, i.value) for i in cls]


class WorkRole(str, Enum):
    CEO_DIRETOR = "CEO/Diretor(a)"
    GERENTE = "Gerente"
    COORDENADOR = "Coordenador(a)"
    ANALISTA = "Analista"
    CONSULTOR = "Consultor(a)"
    ESPECIALISTA = "Especialista"
    ASSISTENTE = "Assistente"
    ESTAGIARIO = "Estagiário(a)"
    ESTUDANTE = "Estudante"
    PROFESSOR_PESQUISADOR = "Professor(a)/Pesquisador(a)"
    FREELANCER = "Freelancer"
    EMPREENDEDOR = "Empreendedor(a)"
    OUTRO = "Outro"

    @classmethod
    def as_choices(cls):
        return [(i.name, i.value) for i in cls]


class WorkSize(str, Enum):
    PEQUENA_1_10 = "1-10 funcionários"
    PEQUENA_11_50 = "11-50 funcionários"
    MEDIA_51_200 = "51-200 funcionários"
    MEDIA_201_500 = "201-500 funcionários"
    GRANDE_MAIS_500 = "Mais de 500 funcionários"

    @classmethod
    def as_choices(cls):
        return [(i.name, i.value) for i in cls]


class WorkDataTool(str, Enum):
    SQL = "SQL"
    PYTHON = "Python"
    R = "R"
    STATA = "Stata"
    EXCEL = "Excel"
    NONE = "Nenhuma"
    OTHER = "Outra"

    @classmethod
    def as_choices(cls):
        return [(i.name, i.value) for i in cls]


class WorkGoal(str, Enum):
    MARKET_ANALYSIS = "Análise de mercado"
    COMPETITOR_MONITORING = "Monitoramento de concorrência"
    ACADEMIC_RESEARCH = "Pesquisa acadêmica"
    RISK_MANAGEMENT = "Gestão de riscos"
    PRODUCT_DEVELOPMENT = "Desenvolvimento de produto"
    COMPLIANCE_REGULATORY = "Compliance e regulatório"
    PUBLIC_POLICY_ANALYSIS = "Análise de políticas públicas"
    OTHER = "Outro"

    @classmethod
    def as_choices(cls):
        return [(i.name, i.value) for i in cls]


class DiscoveryMethod(str, Enum):
    SOCIAL_MEDIA = "Redes sociais"
    REFERRAL = "Indicação"
    ONLINE_SEARCH = "Pesquisa online"
    EVENTS = "Eventos"
    ADVERTISING = "Publicidade"
    OTHER = "Outros"

    @classmethod
    def as_choices(cls):
        return [(i.name, i.value) for i in cls]


class AvailableForResearch(str, Enum):
    YES = "Sim"
    NO = "Não"

    @classmethod
    def as_choices(cls):
        return [(i.name, i.value) for i in cls]
