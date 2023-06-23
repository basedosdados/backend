# -*- coding: utf-8 -*-
import pytest
import uuid


from basedosdados_api.account.models import Account

# from django.core.exceptions import ValidationError

from basedosdados_api.api.v1.models import (
    AnalysisType,
    Table,
    Dataset,
    Organization,
    Area,
    License,
    Theme,
    Tag,
    Entity,
    Pipeline,
    ObservationLevel,
    Column,
    BigQueryType,
    RawDataSource,
    Availability,
    InformationRequest,
    Status,
    Coverage,
    EntityCategory,
    Analysis,
    Dictionary,
    Key,
    QualityCheck,
)


@pytest.fixture(name="area_br")
@pytest.mark.django_db
def fixture_area_br():
    """Fixture for Area."""
    area_br = Area(
        slug="sa_br",
    )
    area_br.save()
    return area_br


@pytest.fixture(name="organizacao_bd")
@pytest.mark.django_db
def fixture_organizacao_bd(area_br):
    """Fixture for Organization."""
    return Organization.objects.create(
        area=area_br,
        slug="basedosdados",
    )


@pytest.fixture(name="organizacao_parceira")
@pytest.mark.django_db
def fixture_organizacao_parceira(area_br):
    """Fixture for Organization."""
    return Organization.objects.create(
        area=area_br,
        slug="organizacao_parceira",
    )


@pytest.fixture(name="tema_educacao")
@pytest.mark.django_db
def fixture_tema_educacao():
    """Fixture for Theme Education."""
    return Theme.objects.create(
        id=uuid.uuid4(),
        slug="educacao",
        name="Educação",
    )


@pytest.fixture(name="tema_saude")
@pytest.mark.django_db
def fixture_tema_saude():
    """Fixture for Theme Health."""
    return Theme.objects.create(
        id=uuid.uuid4(),
        slug="saude",
        name="Saúde",
    )


@pytest.fixture(name="tag_aborto")
@pytest.mark.django_db
def fixture_tag_aborto():
    """Fixture for Tag."""
    return Tag.objects.create(
        id=uuid.uuid4(),
        slug="aborto",
        name="Aborto",
    )


@pytest.fixture(name="tag_covid")
@pytest.mark.django_db
def fixture_tag_covid():
    """Fixture for Tag."""
    return Tag.objects.create(
        id=uuid.uuid4(),
        slug="covid",
        name="Covid-19",
    )


@pytest.fixture(name="licenca_mit")
@pytest.mark.django_db
def fixture_licenca_mit():
    """Fixture for License."""
    return License.objects.create(
        slug="mit",
        name="MIT",
        url="https://mit.com/license",
    )


@pytest.fixture(name="entity_anual")
@pytest.mark.django_db
def fixture_entity_anual():
    """Fixture for Entity."""
    entity_time = EntityCategory.objects.create(
        slug="time",
        name="Time",
    )

    return Entity.objects.create(
        slug="anual",
        name="Anual",
        category=entity_time,
    )


@pytest.fixture(name="entity_escola")
@pytest.mark.django_db
def fixture_entity_escola():
    """Fixture for Entity."""
    entity_education = EntityCategory.objects.create(
        slug="education",
        name="Educação",
    )

    return Entity.objects.create(
        slug="escola",
        name="Escola",
        category=entity_education,
    )


@pytest.fixture(name="pipeline")
@pytest.mark.django_db
def fixture_pipeline():
    """Fixture for Pipeline."""
    return Pipeline.objects.create(
        github_url="https://github.com/basedosdados/pipeline_test",
    )


@pytest.fixture(name="observation_level_anual")
@pytest.mark.django_db
def fixture_observation_level_anual(
    entity_anual,
):
    """Fixture for ObservationLevel."""
    return ObservationLevel.objects.create(
        entity=entity_anual,
    )


@pytest.fixture(name="bigquery_type_string")
@pytest.mark.django_db
def fixture_bigquery_type_string():
    """Fixture for BigQueryType."""
    return BigQueryType.objects.create(name="STRING")


@pytest.fixture(name="bigquery_type_int64")
@pytest.mark.django_db
def fixture_bigquery_type_int64():
    """Fixture for BigQueryType."""
    return BigQueryType.objects.create(name="INT64")


@pytest.fixture(name="disponibilidade_online")
@pytest.mark.django_db
def fixture_disponibilidade_online():
    """Fixture for Availability."""
    return Availability.objects.create(
        name="Online",
        slug="online",
    )


@pytest.fixture(name="status_em_processamento")
@pytest.mark.django_db
def fixture_status_em_processamento():
    """Fixture for Status."""
    return Status.objects.create(
        name="Em processamento",
        slug="em_processamento",
    )


@pytest.fixture(name="coverage_tabela")
@pytest.mark.django_db
def fixture_coverage_tabela(tabela_bairros, area_br):
    """Fixture for Coverage."""
    return Coverage.objects.create(
        table=tabela_bairros,
        area=area_br,
    )


#############################################################################################
# Dataset fixtures
#############################################################################################


@pytest.fixture(name="dataset_dados_mestres")
@pytest.mark.django_db
def fixture_dataset_dados_mestres(
    organizacao_bd,
    tema_saude,
    tema_educacao,
    tag_aborto,
    tag_covid,
    status_em_processamento,
):
    """Test for Dataset."""
    return Dataset.objects.create(
        organization=organizacao_bd,
        slug="dados_mestres",
        name="Dados Mestres",
        description="Descrição dos dados mestres",
        status=status_em_processamento,
        version=1,
    )


#############################################################################################
# Table fixtures
#############################################################################################


@pytest.fixture(name="tabela_bairros")
@pytest.mark.django_db
def fixture_tabela_bairros(
    dataset_dados_mestres,
    licenca_mit,
    organizacao_parceira,
    pipeline,
):
    """Fixture for Table."""
    return Table.objects.create(
        dataset=dataset_dados_mestres,
        license=licenca_mit,
        partner_organization=organizacao_parceira,
        pipeline=pipeline,
        slug="bairros",
        name="Tabela de bairros do Rio de Janeiro",
        description="Descrição da tabela de bairros do Rio de Janeiro",
        is_directory=False,
        data_cleaning_description="Descrição da limpeza de dados",
        data_cleaning_code_url="http://cleaning.com/bairros",
        raw_data_url="http://raw.com/bairros",
        auxiliary_files_url="http://aux.com/bairros",
        architecture_url="http://arch.com/bairros",
        source_bucket_name="basedosdados-dev",
        uncompressed_file_size=1000,
        compressed_file_size=20,
        number_rows=100,
        number_columns=10,
        version=1,
        order=0,
    )


@pytest.fixture(name="tabela_diretorios_brasil_uf")
@pytest.mark.django_db
def fixture_tabela_diretorios_brasil_uf(
    dataset_dados_mestres,
    licenca_mit,
    organizacao_parceira,
    pipeline,
    observation_level_anual,
):
    """Fixture for Table."""
    return Table.objects.create(
        dataset=dataset_dados_mestres,
        license=licenca_mit,
        partner_organization=organizacao_parceira,
        pipeline=pipeline,
        slug="brasil_uf",
        name="Tabela de estados do Brasil",
        description="Descrição da tabela de estados do Brasil",
        is_directory=True,
        data_cleaning_description="Descrição da limpeza de dados",
        data_cleaning_code_url="http://cleaning.com/brasil_uf",
        raw_data_url="http://raw.com/brasil_uf",
        auxiliary_files_url="http://aux.com/brasil_uf",
        architecture_url="http://arch.com/brasil_uf",
        source_bucket_name="basedosdados-dev",
        uncompressed_file_size=1000,
        compressed_file_size=20,
        number_rows=100,
        number_columns=10,
    )


#############################################################################################
# Column fixtures
#############################################################################################


@pytest.fixture(name="coluna_state_id_diretorio")
@pytest.mark.django_db
def fixture_coluna_state_id_diretorio(
    tabela_diretorios_brasil_uf,
    bigquery_type_string,
):
    """Fixture for state_id column in a directory table."""
    return Column.objects.create(
        table=tabela_diretorios_brasil_uf,
        name="ID do estado no diretório",
        description="Descrição da coluna state_id no diretório",
        bigquery_type=bigquery_type_string,
        is_in_staging=True,
        is_partition=False,
    )


@pytest.fixture(name="coluna_state_id_bairros")
@pytest.mark.django_db
def fixture_coluna_state_id_bairros(
    tabela_bairros, bigquery_type_string, coluna_state_id_diretorio
):
    """Fixture for state_id column. This is a directory."""
    return Column.objects.create(
        table=tabela_bairros,
        name="ID do estado",
        description="Descrição da coluna state_id",
        bigquery_type=bigquery_type_string,
        is_in_staging=True,
        is_partition=False,
        directory_primary_key=coluna_state_id_diretorio,
        order=1,
    )


@pytest.fixture(name="coluna_nome_bairros")
@pytest.mark.django_db
def fixture_coluna_nome_bairros(
    tabela_bairros, bigquery_type_string, status_em_processamento
):
    """Fixture for name column."""
    return Column.objects.create(
        table=tabela_bairros,
        name="Nome do bairro",
        name_staging="Nome do bairro",
        description="Descrição da coluna nome",
        bigquery_type=bigquery_type_string,
        is_in_staging=True,
        is_partition=False,
        status=status_em_processamento,
        is_primary_key=True,
        order=2,
    )


@pytest.fixture(name="coluna_populacao_bairros")
@pytest.mark.django_db
def fixture_coluna_populacao_bairros(
    tabela_bairros,
    bigquery_type_int64,
):
    """Fixture for population column."""
    return Column.objects.create(
        table=tabela_bairros,
        name="População",
        description="Descrição da coluna populacao",
        bigquery_type=bigquery_type_int64,
        is_in_staging=True,
        is_partition=False,
        version=1,
        is_primary_key=False,
        order=3,
    )


#############################################################################################
# RawData fixtures
#############################################################################################


@pytest.fixture(name="raw_data_source")
@pytest.mark.django_db
def fixture_raw_data_source(
    dataset_dados_mestres, disponibilidade_online, licenca_mit, status_em_processamento
):
    """Fixture for RawData."""
    return RawDataSource.objects.create(
        dataset=dataset_dados_mestres,
        availability=disponibilidade_online,
        license=licenca_mit,
        name="Fonte de dados",
        status=status_em_processamento,
        version=1,
        order=0,
    )


#############################################################################################
# Information Request fixtures
#############################################################################################


@pytest.fixture(name="usuario_inicio")
@pytest.mark.django_db
def fixture_usuario_inicio():
    """Fixture for User."""
    return Account.objects.create(
        username="usuario_inicio",
        email="usuario@usuario.com",
        first_name="Usuario",
        last_name="Inicio",
        profile=Account.STAFF,
    )


@pytest.fixture(name="pedido_informacao")
@pytest.mark.django_db
def fixture_pedido_informacao(
    dataset_dados_mestres,
    tabela_bairros,
    coluna_nome_bairros,
    coluna_populacao_bairros,
    status_em_processamento,
    usuario_inicio,
):
    """Fixture for InformationRequest."""
    return InformationRequest.objects.create(
        dataset=dataset_dados_mestres,
        status=status_em_processamento,
        started_by=usuario_inicio,
        version=1,
        order=0,
    )


#############################################################################################
# Analysis fixtures
#############################################################################################


@pytest.fixture(name="analise_tipo1")
@pytest.mark.django_db
def fixture_analise_tipo1():
    return AnalysisType.objects.create(
        name="Análise tipo 1",
        slug="analise-tipo-1",
    )


@pytest.fixture(name="analise_bairros")
@pytest.mark.django_db
def fixture_analise_bairros(
    analise_tipo1,
    dataset_dados_mestres,
    tema_saude,
    tema_educacao,
    tag_aborto,
    tag_covid,
):
    """Fixture for Analysis."""
    analysis = Analysis.objects.create(
        name="Análise de bairros",
        description="Descrição da análise de bairros",
        analysis_type=analise_tipo1,
        url="https://analise.com/bairros",
    )
    return analysis


@pytest.fixture(name="dicionario_1")
@pytest.mark.django_db
def test_dictionary(
    coluna_nome_bairros,
):
    """Fixture for Dictionary."""
    return Dictionary.objects.create(
        column=coluna_nome_bairros,
    )


@pytest.fixture(name="chave_1")
@pytest.mark.django_db
def fixture_chave_1(dicionario_1):
    chave = Key.objects.create(dictionary=dicionario_1, name="Chave 1", value="Valor 1")

    return chave


@pytest.fixture(name="teste_qualidade")
@pytest.mark.django_db
def fixture_teste_qualidade(
    pipeline,
    analise_bairros,
    dataset_dados_mestres,
    tabela_bairros,
    coluna_nome_bairros,
    chave_1,
    raw_data_source,
    pedido_informacao,
):
    teste_qualidade = QualityCheck.objects.create(
        name="Teste de qualidade",
        description="Descrição do teste de qualidade",
        passed=True,
        pipeline=pipeline,
        analysis=analise_bairros,
        dataset=dataset_dados_mestres,
        table=tabela_bairros,
        column=coluna_nome_bairros,
        key=chave_1,
        raw_data_source=raw_data_source,
        information_request=pedido_informacao,
    )
    return teste_qualidade
