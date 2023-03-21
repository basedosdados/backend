from enum import Enum
from typing import Union


class EntityDateTimeEnum:
    # fmt: off
    year       = { "category":"datetime", "label": "Ano"} #"One Year"}
    semester   = { "category":"datetime", "label": "Semestre"} #"Semester"}
    quarter    = { "category":"datetime", "label": "Trimestre"} #"Quarter"}
    bimester   = { "category":"datetime", "label": "Bimestre"} #"Bimester"}
    month      = { "category":"datetime", "label": "Mês"} #"Month"}
    week       = { "category":"datetime", "label": "Semana"} #"Week"}
    day        = { "category":"datetime", "label": "Dia"} #"Day"}
    hour       = { "category":"datetime", "label": "Hora"} #"Hour"}
    minute     = { "category":"datetime", "label": "Minuto"} #"Minute"}
    second     = { "category":"datetime", "label": "Segundo"} #"Second"}
    date       = { "category":"datetime", "label": "Data"} #"Date"}
    time       = { "category":"datetime", "label": "Horário"} #"Time"}
    # fmt: on


class EntitySpatialEnum:
    # fmt: off
    continent        = { "category":"spatial", 'label': "Continente"} #"Continent"}
    country          = { "category":"spatial", 'label': "País"} #"Country"}
    region           = { "category":"spatial", 'label': "Região"} #"Region"}
    state            = { "category":"spatial", 'label': "Estado/Unidade da Federação"} #"State"}
    district         = { "category":"spatial", 'label': "Distrito"} #"District"}
    county           = { "category":"spatial", 'label': "Condado"} #"County"}
    municipality     = { "category":"spatial", 'label': "Município"} #"Municipality"}
    city             = { "category":"spatial", 'label': "Cidade"} #"City"}
    village          = { "category":"spatial", 'label': "Vila/Aldeia"} #"Village"}
    neighborhood     = { "category":"spatial", 'label': "Bairro"} #"Neighborhood"}
    zip_code         = { "category":"spatial", 'label': "CEP"} #"Zip Code"}
    census_tract     = { "category":"spatial", 'label': "Setor censitário"} #"CensusTract"}
    # fmt: on


class EntityIndividualEnum:
    # fmt: off
    person           = { "category":"individual", 'label': "Pessoa"} #"Person"}
    household        = { "category":"individual", 'label': "Domicílio"} #"Household"}
    name             = { "category":"individual", 'label': "Nome"} #"Name"}
    animal           = { "category":"individual", 'label': "Animal (mamífero, micróbio, vírus, etc)"} #"Animal"}
    plant            = { "category":"individual", 'label': "Planta (árvore, espécie)"} #"Plant"}
    # fmt: on


class EntityEstablishmentEnum:
    # fmt: off
    agency           = { "category":"establishment", 'label': "Agência"} #"Agency"}
    protected_area   = { "category":"establishment", 'label': "Área protegida"} #"Protected Area"}
    band             = { "category":"establishment", 'label': "Banda"}
    library          = { "category":"establishment", 'label': "Biblioteca"} #"Library"}
    notary_office    = { "category":"establishment", 'label': "Cartório"} #"Notary's Office"}
    school           = { "category":"establishment", 'label': "Creche/Escola/Universidade"} #"School"}
    legislature      = { "category":"establishment", 'label': "Congresso/Assembleia Legislativa"}
    police_station   = { "category":"establishment", 'label': "Delegacia"} #"Property"}
    company          = { "category":"establishment", 'label': "Empresa/Companhia"} #"Company"}
    station          = { "category":"establishment", 'label': "Estação"} #"Station"}
    stadium          = { "category":"establishment", 'label': "Estádio"} #"Stadium"}
    terrorist_group  = { "category":"establishment", 'label': "Grupo terrorista"} #"Terrorist Group"}
    hospital         = { "category":"establishment", 'label': "Hospital"} #"Hospital"}
    church           = { "category":"establishment", 'label': "Igreja"}
    property         = { "category":"establishment", 'label': "Imóvel/Propriedade"} #"Property"}
    ministry         = { "category":"establishment", 'label': "Ministério/Departamento"} #"Ministry/Department"}
    museum           = { "category":"establishment", 'label': "Museu"} #"Museum"}
    construction     = { "category":"establishment", 'label': "Obra/Construção"} #"Nongovernmental Organization (NGO)"}
    ngo              = { "category":"establishment", 'label': "Organização Não-Governamental (ONG)"} #"Nongovernmental Organization (NGO)"}
    prison           = { "category":"establishment", 'label': "Presídio/Cadeia"} #"Prison"}
    team             = { "category":"establishment", 'label': "Time"} #"Team"}
    court            = { "category":"establishment", 'label': "Tribunal"} #"Company"}
    store            = { "category":"establishment", 'label': "Loja"} #"Store"}
    # fmt: on


class EntityPoliticsEnum:
    # fmt: off
    agreement        = { "category":"politics", 'label': "Acordo/Tratado"} #"Agreement/Treaty"}
    speech           = { "category":"politics", 'label': "Discurso/Fala"} #"Speech"}
    election         = { "category":"politics", 'label': "Eleição"} #"Election"}
    caucus           = { "category":"politics", 'label': "Frente Parlamentar/Caucus"}
    law              = { "category":"politics", 'label': "Lei/Proposição/Matéria"} #"Law/Proposition"}
    party            = { "category":"politics", 'label': "Partido"} #"Party"}
    poll             = { "category":"politics", 'label': "Pesquisa de Opinião"} #"Poll"}
    vote             = { "category":"politics", 'label': "Voto"}
    # fmt: on


class EntityScienceEnum:
    # fmt: off
    article          = { "category":"science", 'label': "Artigo/Publicação"} #"Article/Paper"}
    citation         = { "category":"science", 'label': "Citação"} #"Citation"}
    domain           = { "category":"science", 'label': "Domínio"} #"Domain"}
    document         = { "category":"science", 'label': "Documento"}
    iceberg          = { "category":"science", 'label': "Iceberg"}
    book             = { "category":"science", 'label': "Livro"} #"Book"}
    newspaper        = { "category":"science", 'label': "Jornal"} #"Newspaper"}
    drug             = { "category":"science", 'label': "Medicamento/Droga"}
    patent           = { "category":"science", 'label': "Patente"} #"Patent"}
    journal          = { "category":"science", 'label': "Periódico/Revista"} #"Journal/Magazine"}
    word             = { "category":"science", 'label': "Palavra"} #"Word"}
    post             = { "category":"science", 'label': "Post/Tweet"} #"Post/Tweet"}
    language         = { "category":"science", 'label': "Língua"} #"Language"}
    crs              = { "category":"science", 'label': "Creche"} #"Coordinate Reference System"}
    page             = { "category":"science", 'label': "Página"}
    protein          = { "category":"science", 'label': "Proteína"} #"Protein"}
    meteor           = { "category":"science", 'label': "Meteoro"} #"Meteor"}
    terrain          = { "category":"science", 'label': "Terreno"}
    typo             = { "category":"science", 'label': "Erro de digitação"}
    # fmt: on


class EntityEconomicsEnum:
    # fmt: off
    contract         = { "category":"economics", 'label': "Contrato"} #"Contract"}
    donation         = { "category":"economics", 'label': "Doação"} #"Contract"}
    amendment        = { "category":"economics", 'label': "Emenda Parlamentar"}
    expenditure      = { "category":"economics", 'label': "Gasto"}
    item             = { "category":"economics", 'label': "Item"}
    grant            = { "category":"economics", 'label': "Prêmio/Concessão/Convênio"} #"Grant"}
    procurement      = { "category":"economics", 'label': "Licitação"} #"Procurement"}
    product          = { "category":"economics", 'label': "Produto"} #"Product"}
    transaction      = { "category":"economics", 'label': "Transação"} #"Transaction"}
    transfer         = { "category":"economics", 'label': "Transferência"} #"Transfer"}
    bill             = { "category":"economics", 'label': "Nota de dinheiro"} #"Money Bill"}
    occupation       = { "category":"economics", 'label': "Ocupação"} #"Occupation"}
    sector           = { "category":"economics", 'label': "Setor"} #"Sector"}
    # fmt: on


class EntityEducationEnum:
    # fmt: off
    scholarship      = { "category":"education", 'label': "Bolsa"} #"Scholarship"}
    exam             = { "category":"education", 'label': "Prova/Exame"} #"Test/Exam"}
    # fmt: on


class EntityEventEnum:
    # fmt: off
    alert            = { "category":"event", 'label': "Alerta"} #"Alert"}
    attack           = { "category":"event", 'label': "Ataque/Atentado"} #"Attack"}
    audit            = { "category":"event", 'label': "Auditoria"}
    act              = { "category":"event", 'label': "Ato"} #"Act"}
    concert          = { "category":"event", 'label': "Concerto/Show"} #"Concert"}
    disinvitation    = { "category":"event", 'label': "Cancelamento de convite"} #"Disinvitation"}
    disaster         = { "category":"event", 'label': "Desastre Natural (terremoto, enchente/inundação, fogo, etc)"} #"Natural Disaster (earthquake, flood, fire, etc)"}
    war              = { "category":"event", 'label': "Guerra/Conflito"}
    territorial_change = { "category":"event", 'label': "Mudança Territorial"}
    birth            = { "category":"event", 'label': "Nascimento"} #"Birth"}
    death            = { "category":"event", 'label': "Morte/Óbito"} #"Death"}
    request          = { "category":"event", 'label': "Pedido/Solicitação/Reclamação"} #"Request/Complaint"}
    protest          = { "category":"event", 'label': "Protesto"} #"Protest"}
    match            = { "category":"event", 'label': "Partida"} #"Match"}
    sanction         = { "category":"event", 'label': "Sanção/Multa"} #"Match"}
    # fmt: on


class EntityArtEnum:
    # fmt: off
    album            = { "category":"art", 'label': "Álbum"} #"Album"}
    movie            = { "category":"art", 'label': "Filme/Série/Clipe"} #"Movie/Film/Clip/Show"}
    photo            = { "category":"art", 'label': "Foto"} #"Photo/Picture"}
    song             = { "category":"art", 'label': "Música"} #"Song"}
    statue           = { "category":"art", 'label': "Estátua"} #"Statue"}
    painting         = { "category":"art", 'label': "Pintura/Desenho/Ilustração"} #"Painting/Drawing/Illustration"}
    poem             = { "category":"art", 'label': "Poema"} #"Poem"}
    # fmt: on


class EntityInfrastructureEnum:
    # fmt: off
    dam              = { "category":"infra_structure", 'label': "Represa/Barragem"} #"Dam"}
    satellitte       = { "category":"infra_structure", 'label': "Satélite"} #"Satellite"}
    street_road      = { "category":"infra_structure", 'label': "Rua/Avenida/Estrada"} #"Street/Avenue/Road/Highway"}
    roller_coaster   = { "category":"infra_structure", 'label': "Montanha-Russa"} #"Roller Coaster"}
    # fmt: on


class EntityTransportationEnum:
    # fmt: off
    automobile       = { "category":"transportation", 'label': "Carro/Ônibus/Caminhão/Moto"} #"Car/Bus/Truck/Motorcycle"}
    train            = { "category":"transportation", 'label': "Trem"} #"Train"}
    aircraft         = { "category":"transportation", 'label': "Avião/Helicóptero"} #"Plane/Helicopter"}
    ship             = { "category":"transportation", 'label': "Embarcação/Navio"} #"Ship"}
    # fmt: on


class EntitySecurityEnum:
    # fmt: off
    gun              = { "category":"security", 'label': "Arma"} #"Gun"}
    # fmt: on


class EntityDemographicEnum:
    # fmt: off
    age              = { "category":"demographic", 'label': "Idade"} #"Age"}
    race             = { "category":"demographic", 'label': "Raça/Cor de pele"} #"Race/Skin color"}
    sex              = { "category":"demographic", 'label': "Sexo"} #"Sex"}
    # fmt: on


class EntityImageEnum:
    # fmt: off
    pixel            = { "category":"image", 'label': "Pixel/Grid"} #"Pixel/Grid"}
    polygon          = { "category":"image", 'label': "Polígono"} #"Polygon"}
    # fmt: on


class EntityHistoryEnum:
    # fmt: off
    empire           = { "category":"history", 'label': "Império"} #"Empire"}
    # fmt: on


class EntityOtherEnum:
    # fmt: off
    other            = { "category":"other", 'label': "Outro"} #"Other"}
    # fmt: on


class EntityUnknownEnum:
    # fmt: off
    unknown            = { "category":"unknown", 'label': "Desconhecida"} #"Other"}
    # fmt: on


EntityEnum = [
    EntityDateTimeEnum,
    EntitySpatialEnum,
    EntityIndividualEnum,
    EntityEstablishmentEnum,
    EntityPoliticsEnum,
    EntityScienceEnum,
    EntityEconomicsEnum,
    EntityEducationEnum,
    EntityEventEnum,
    EntityArtEnum,
    EntityInfrastructureEnum,
    EntityTransportationEnum,
    EntitySecurityEnum,
    EntityDemographicEnum,
    EntityHistoryEnum,
    EntityOtherEnum,
    EntityImageEnum,
    EntityUnknownEnum,
]
