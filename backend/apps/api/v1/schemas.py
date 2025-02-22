# -*- coding: utf-8 -*-
from typing import Dict, List, Optional

from pydantic import BaseModel


class Organization(BaseModel):
    id: str
    slug: str
    name_pt: str
    name_en: str
    name_es: str
    picture: Optional[str]


class Theme(BaseModel):
    slug: str
    name_pt: str
    name_en: str
    name_es: str


class Tag(BaseModel):
    slug: str
    name_pt: str
    name_en: str
    name_es: str


class Entity(BaseModel):
    keyword: str
    slug: str
    name_pt: str
    name_en: str
    name_es: str


class MeasurementUnit(BaseModel):
    slug: str
    name_pt: str
    name_en: str
    name_es: str


class RawDataSource(BaseModel):
    id: str


class SpatialCoverage(BaseModel):
    slug: str
    name_pt: str
    name_en: str
    name_es: str


class TemporalCoverage(BaseModel):
    start_date: str
    end_date: str


class Dataset(BaseModel):
    id: str
    name: str
    slug: str
    #
    updated_at: str
    #
    n_tables: int
    first_table_id: str
    first_open_table_id: Optional[str]
    first_closed_table_id: Optional[str]
    #
    n_raw_data_sources: int
    first_raw_data_source_id: str
    #
    n_information_requests: int
    first_information_request_id: str
    #
    is_closed: bool
    contains_tables: bool
    contains_open_data: bool
    contains_closed_data: bool
    #
    contains_data_api_endpoint_tables: bool
    #
    themes: List[Theme]
    organization: List[Organization]
    temporal_coverage: List[str]
    spatial_coverage: List[SpatialCoverage]
    tags: List[Tag]
    entities: List[Entity]


class Facet(BaseModel):
    key: str
    name: str
    count: int


class Response(BaseModel):
    count: int
    results: List[Dataset] = []
    aggregations: Dict[str, list[Facet]] = {}
