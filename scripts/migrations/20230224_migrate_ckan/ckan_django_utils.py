# -*- coding: utf-8 -*-
# TODO fazer coverage para os trez tipos de recurso utilizando parse_temporal_coverage
# TODO filtrar pelo id do modelo pai
# TODO usar dataframe para controle dos packages, coluna migrate 'e alterada para 1 quando o package 'e migrado


import itertools
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm
from unidecode import unidecode


def get_token(url, username, password):
    r = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json={
            "query": """
                mutation tokenAuth($username: String!, $password: String!) {
                    tokenAuth(
                        username: $username,
                        password: $password,
                    ) {
                        payload,
                        refreshExpiresIn,
                        token
                    }
                }
            """,
            "variables": {"username": username, "password": password},
        },
    )
    r.raise_for_status()
    return r.json()["data"]["tokenAuth"]["token"]


def request_bd_package(file_path):
    url = "https://basedosdados.org"
    api_url = f"{url}/api/3/action/package_search?q=&rows=2000"
    packages = requests.get(api_url, verify=False).json()["result"]["results"]
    df = pd.DataFrame(data={"packages": packages})
    df["package_id"] = df["packages"].apply(lambda x: x["id"])
    df.to_json(file_path)
    return df


def get_bd_packages():
    path = Path("./utils/migration/data")
    path.mkdir(parents=True, exist_ok=True)
    file_path = path / "packages.json"
    file_path_migrated = path / "packages_migrated.csv"

    if not file_path.exists():
        return request_bd_package(file_path)
    df = pd.read_json(file_path)

    if file_path_migrated.exists():
        df_migrated = pd.read_csv(file_path_migrated)
        return df[~df["package_id"].isin(df_migrated["package_id"].tolist())]
    else:
        return df


def build_areas_from_json():

    with open("./basedosdados_api/schemas/repository/bd_spatial_coverage_tree.json") as f:
        area = json.load(f)

    return area.get("result")


def get_package_model(name_or_id):
    url = f"https://basedosdados.org/api/3/action/package_show?name_or_id={name_or_id}"
    packages = requests.get(url, verify=False).json()["result"]

    df = pd.DataFrame(data={"packages": [packages]})

    df["package_id"] = df["packages"].apply(lambda x: x["id"])

    return df


def pprint(msg):
    print(">>>>> ", msg)


def parse_temporal_coverage(temporal_coverage):
    # Extrai as informações de data e intervalo da string
    if "(" in temporal_coverage:
        start_str, interval_str, end_str = re.split(r"[(|)]", temporal_coverage)
        if start_str == "" and end_str != "":
            start_str = end_str
        elif end_str == "" and start_str != "":
            end_str = start_str
    elif len(temporal_coverage) == 4:
        start_str, interval_str, end_str = temporal_coverage, 1, temporal_coverage
    start_len = 0 if start_str == "" else len(start_str.split("-"))
    end_len = 0 if end_str == "" else len(end_str.split("-"))

    def parse_date(position, date_str, date_len):
        result = {}
        if date_len == 3:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            result[f"{position}Year"] = date.year
            result[f"{position}Month"] = date.month
            result[f"{position}Day"] = date.month
        elif date_len == 2:
            date = datetime.strptime(date_str, "%Y-%m")
            result[f"{position}Year"] = date.year
            result[f"{position}Month"] = date.month
        elif date_len == 1:
            date = datetime.strptime(date_str, "%Y")
            result[f"{position}Year"] = date.year
        return result

    start_result = parse_date(position="start", date_str=start_str, date_len=start_len)
    end_result = parse_date(position="end", date_str=end_str, date_len=end_len)
    start_result.update(end_result)

    if interval_str != 0:
        start_result["interval"] = int(interval_str)

    return start_result


class Migration:
    def __init__(self, url, token):
        self.base_url = url
        self.header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        self.area_dict = build_areas_from_json()

    def get_id(self, query_class, query_parameters):  # sourcery skip: avoid-builtin-shadow
        _filter = ", ".join(list(query_parameters.keys()))
        keys = [
            parameter.replace("$", "").split(":")[0] for parameter in list(query_parameters.keys())
        ]
        values = list(query_parameters.values())
        _input = ", ".join([f"{key}:${key}" for key in keys])

        query = f"""query({_filter}) {{
                        {query_class}({_input}){{
                        edges{{
                            node{{
                            id,
                            }}
                        }}
                        }}
                    }}"""
        r = requests.post(
            url=self.base_url,
            json={"query": query, "variables": dict(zip(keys, values))},
            headers=self.header,
        ).json()

        if "data" in r and r is not None:
            if r.get("data", {}).get(query_class, {}).get("edges") == []:
                id = None
                # print(f"get: not found {query_class}", dict(zip(keys, values)))
            else:
                id = r["data"][query_class]["edges"][0]["node"]["id"]
                # print(f"get: found {id}")
                id = id.split(":")[1]
            return r, id
        else:
            print("get:  Error:", json.dumps(r, indent=4, ensure_ascii=False))
            raise Exception("get: Error")

    def create_update(
        self,
        mutation_class,
        mutation_parameters,
        query_class,
        query_parameters,
        update=False,
    ):
        r, id = self.get_id(query_class=query_class, query_parameters=query_parameters)
        if id is not None:
            r["r"] = "query"
            if update is False:
                return r, id

        _classe = mutation_class.replace("CreateUpdate", "").lower()
        query = f"""
                mutation($input:{mutation_class}Input!){{
                    {mutation_class}(input: $input){{
                    errors {{
                        field,
                        messages
                    }},
                    clientMutationId,
                    {_classe} {{
                        id,
                    }}
                }}
                }}
            """

        if update is True and id is not None:
            mutation_parameters["id"] = id
        r = requests.post(
            self.base_url,
            json={"query": query, "variables": {"input": mutation_parameters}},
            headers=self.header,
        ).json()

        r["r"] = "mutation"
        if "data" in r and r is not None:
            if r.get("data", {}).get(mutation_class, {}).get("errors", []) != []:
                print(f"create: not found {mutation_class}", mutation_parameters)
                print("create: error\n", json.dumps(r, indent=4, ensure_ascii=False), "\n")
                id = None
                raise Exception("create: Error")
            else:
                id = r["data"][mutation_class][_classe]["id"]
                # print(f"create: created {id}")
                id = id.split(":")[1]

                return r, id
        else:
            print("\n", "create: query\n", query, "\n")
            print(
                "create: input\n",
                json.dumps(mutation_parameters, indent=4, ensure_ascii=False),
                "\n",
            )
            print("create: error\n", json.dumps(r, indent=4, ensure_ascii=False), "\n")
            raise Exception("create: Error")

    def delete(self, classe, id):
        query = f"""
            mutation{{
                Delete{classe}(id: "{id}") {{
                    ok,
                    errors
                }}
            }}
        """

        r = requests.post(
            self.base_url,
            json={"query": query},
            headers=self.header,
        ).json()

        if r["data"][f"Delete{classe}"]["ok"] is True:
            print(f"deleted dataset {id} ")
        else:
            print("delete errors", r["data"][f"Delete{classe}"]["errors"])

        return r

    def create_themes(self, objs):
        ids = []
        for obj in objs:
            r, id = self.create_update(
                mutation_class="CreateUpdateTheme",
                mutation_parameters={
                    "slug": obj.get("name"),
                    "name": obj.get("title"),
                    "logoUrl": obj.get("image_display_url"),
                },
                query_class="allTheme",
                query_parameters={"$slug: String": obj.get("name")},
            )
            ids.append(id)

        return ids

    def create_tags(self, objs):
        ids = []
        for obj in objs:
            tag_slug = obj.get("name").replace("+", "").lower().replace(" ", "_")
            tag_name = obj.get("display_name")
            r, id = self.create_update(
                mutation_class="CreateUpdateTag",
                mutation_parameters={
                    "slug": "desconhecida" if tag_slug is None else unidecode(tag_slug),
                    "name": "desconhecida" if tag_name is None else tag_name.replace(" ", "_"),
                },
                query_class="allTag",
                query_parameters={"$slug: String": unidecode(tag_slug)},
            )
            ids.append(id)

        return ids

    def create_availability(self, obj):
        availability = (
            "desconhecida" if obj.get("availability") is None else obj.get("availability")
        )
        r, id = self.create_update(
            mutation_class="CreateUpdateAvailability",
            mutation_parameters={
                "slug": availability,
                "name": availability,
            },
            query_class="allAvailability",
            query_parameters={"$slug: String": availability},
        )

        return id

    def create_entity(self, obj=None):
        if (obj is None) or (obj.get("entity") is None):
            r, id = self.create_update(
                mutation_class="CreateUpdateEntity",
                mutation_parameters={
                    "slug": "desconhecida",
                    "name": "desconhecida",
                },
                query_class="allEntity",
                query_parameters={"$slug: String": "desconhecida"},
            )
        else:
            r, id = self.create_update(
                mutation_class="CreateUpdateEntity",
                mutation_parameters={
                    "slug": obj["entity"],
                    "name": obj["entity"],
                },
                query_class="allEntity",
                query_parameters={"$slug: String": obj["entity"]},
            )

        return id

    def create_update_frequency(self, update_frequency=None, observation_levels=None):
        update_frequency_dict = {
            "second": 1,
            "minute": 1,
            "hour": 1,
            "day": 1,
            "week": 1,
            "month": 1,
            "quarter": 1,
            "semester": 1,
            "one_year": 1,
            "two_years": 2,
            "three_years": 3,
            "four_years": 4,
            "five_years": 5,
            "ten_years": 10,
            "unique": 0,
            "recurring": 0,
            "uncertain": 0,
            "other": 0,
            None: 0,
        }

        update_frequency_entity_dict = {
            "year": "",
            "semester": "",
            "quarter": "",
            "bimester": "",
            "month": "",
            "week": "",
            "day": "",
            "hour": "",
            "minute": "",
            "second": "",
            "date": "",
            "time": "",
        }

        if observation_levels is None:
            entity_id = self.create_entity(obj=None)

            r, id = self.create_update(
                mutation_class="CreateUpdateUpdateFrequency",
                mutation_parameters={
                    "entity": entity_id,
                    "number": update_frequency_dict[update_frequency],
                },
                query_class="allUpdatefrequency",
                query_parameters={
                    "$number: Int": update_frequency_dict[update_frequency],
                    "$entity_Id: ID": entity_id,
                },
            )
        else:
            for ob in observation_levels:
                if (
                    ob.get("entity") in update_frequency_entity_dict
                    and ob.get("entity") is not None
                ):
                    entity_id = self.create_entity(obj=ob)
                    r, id = self.create_update(
                        mutation_class="CreateUpdateUpdateFrequency",
                        mutation_parameters={
                            "entity": entity_id,
                            "number": update_frequency_dict[update_frequency],
                        },
                        query_class="allUpdatefrequency",
                        query_parameters={
                            "$number: Int": update_frequency_dict[update_frequency],
                            "$entity_Id: ID": entity_id,
                        },
                    )
                elif ob.get("entity") is None:

                    entity_id = self.create_entity(obj=None)

                    r, id = self.create_update(
                        mutation_class="CreateUpdateUpdateFrequency",
                        mutation_parameters={
                            "entity": entity_id,
                            "number": update_frequency_dict[update_frequency],
                        },
                        query_class="allUpdatefrequency",
                        query_parameters={
                            "$number: Int": update_frequency_dict[update_frequency],
                            "$entity_Id: ID": entity_id,
                        },
                    )
                else:
                    entity_id = self.create_entity(obj=None)
                    r, id = self.create_update(
                        mutation_class="CreateUpdateUpdateFrequency",
                        mutation_parameters={
                            "entity": entity_id,
                            "number": 0,
                        },
                        query_class="allUpdatefrequency",
                        query_parameters={
                            "$number: Int": 0,
                            "$entity_Id: ID": entity_id,
                        },
                    )

        return id

    def create_observation_level(self, observation_levels=None):

        if observation_levels is None:
            entity_id = self.create_entity(obj=None)
            r, id = self.create_update(
                mutation_class="CreateUpdateObservationLevel",
                mutation_parameters={
                    "entity": entity_id,
                },
                query_class="allObservationlevel",
                query_parameters={
                    "$entity_Id: ID": entity_id,
                },
            )
        else:
            for ob in observation_levels:
                entity_id = self.create_entity(obj=ob)
                r, id = self.create_update(
                    mutation_class="CreateUpdateObservationLevel",
                    mutation_parameters={
                        "entity": entity_id,
                    },
                    query_class="allObservationlevel",
                    query_parameters={
                        "$entity_Id: ID": entity_id,
                    },
                )
        return id

    def create_license(self):
        r, id = self.create_update(
            mutation_class="CreateUpdateLicense",
            mutation_parameters={
                "slug": "desconhecida",
                "name": "desconhecida",
                "url": "desconhecida.com",
            },
            query_class="allLicense",
            query_parameters={"$slug: String": "desconhecida"},
        )

        return id

    def create_bq_type(self, obj):
        r, id = self.create_update(
            mutation_class="CreateUpdateBigQueryTypes",
            mutation_parameters={
                "name": obj,
            },
            query_class="allBigquerytypes",
            query_parameters={"$name: String": obj},
        )

        return id

    def create_directory_columns(self, column, table_id):
        if column.get("covered_by_dictionary") == "yes":
            r, id = self.get_id(
                query_class="allColumn",
                query_parameters={
                    "$name: String": column.get("directory_column").get("column_name"),
                    "$table_Id: ID": table_id,
                },
            )
            return id
        else:
            return None

    def create_temporal_coverage(self, resource, coverage_id):
        temporal_temporal_coverages = (
            [None]
            if resource.get("temporal_coverage") == [] or resource.get("temporal_coverage") is None
            else resource.get("temporal_coverage")
        )

        if temporal_temporal_coverages != [None]:
            temporal_temporal_coverages_chain = [
                s.split(",") if "," in s else [s] for s in temporal_temporal_coverages
            ]
            temporal_temporal_coverages = list(itertools.chain(*temporal_temporal_coverages_chain))

        for temporal_coverage in temporal_temporal_coverages:
            if temporal_coverage is not None:
                resource_to_temporal_coverage = parse_temporal_coverage(temporal_coverage)
                resource_to_temporal_coverage["coverage"] = coverage_id

                r, id = self.create_update(
                    query_class="allDatetimerange",
                    query_parameters={"$coverage_Id: ID": coverage_id},
                    mutation_class="CreateUpdateDateTimeRange",
                    mutation_parameters=resource_to_temporal_coverage,
                )

    def create_coverage(self, resource, coverage):
        coverage_type = list(coverage.keys())[0]
        coverage_value = list(coverage.values())[0]
        area_slugs = (
            ["desconhecida"]
            if resource.get("spatial_coverage") == [] or resource.get("spatial_coverage") is None
            else resource.get("spatial_coverage")
        )

        if coverage_type == "table":
            coverage_filter = "table_Id"
        elif coverage_type == "column":
            coverage_filter = "column_Id"
        elif coverage_type == "rawDataSource":
            coverage_filter = "rawDataSource_Id"
        elif coverage_type == "informationRequest":
            coverage_filter = "informationRequest_Id"

        for area in area_slugs:
            package_to_coverage = {coverage_type: coverage_value}
            package_to_coverage["area"] = self.create_area(area=area)
            r, id = self.create_update(
                query_class="allCoverage",
                query_parameters={f"${coverage_filter}: ID": coverage_value},
                mutation_class="CreateUpdateCoverage",
                mutation_parameters=package_to_coverage,
            )

            self.create_temporal_coverage(resource=resource, coverage_id=id)

        return id

    def create_columns(self, resource, table_id):
        objs = resource.get("columns")
        if objs is None:
            r, id = self.create_update(
                mutation_class="CreateUpdateColumn",
                mutation_parameters={
                    "table": table_id,
                    "bigqueryType": self.create_bq_type("desconhecida"),
                    "name": "desconhecida",
                    "isInStaging": "desconhecida",
                    "isPartition": "desconhecida",
                    "description": "desconhecida",
                    "coveredByDictionary": False,
                    "measurementUnit": "desconhecida",
                    "containsSensitiveData": False,
                    "observations": "desconhecida",
                },
                query_class="allColumn",
                query_parameters={
                    "$name: String": "desconhecida",
                    "$table_Id: ID": table_id,
                },
            )
            if r.get("r") == "mutation":
                coverage_id = self.create_coverage(
                    resource=resource,
                    coverage={"column": id},
                )
            ids = [id]
        else:
            ids = []
            for column in tqdm(objs):
                r, id = self.create_update(
                    mutation_class="CreateUpdateColumn",
                    mutation_parameters={
                        "table": table_id,
                        "bigqueryType": self.create_bq_type(column.get("bigquery_type")),
                        "directoryPrimaryKey": self.create_directory_columns(column, table_id),
                        "name": column.get("name"),
                        "isInStaging": column.get("is_in_staging"),
                        "isPartition": column.get("is_partition"),
                        "description": column.get("description"),
                        "coveredByDictionary": True
                        if column.get("covered_by_dictionary") == "yes"
                        else False,
                        "measurementUnit": column.get("measurement_unit"),
                        "containsSensitiveData": column.get("contains_sensitive_data"),
                        "observations": column.get("observations"),
                    },
                    query_class="allColumn",
                    query_parameters={
                        "$name: String": column.get("name"),
                        "$table_Id: ID": table_id,
                    },
                )
                if r.get("r") == "mutation":
                    coverage_id = self.create_coverage(  # noqa
                        resource=resource,
                        coverage={"column": id},
                    )

                ids.append(id)

        return ids

    def create_org(self, org_dict):

        if org_dict is None:
            r, graphql_org_id = self.create_update(
                query_class="allOrganization",
                query_parameters={"$slug: String": "desconhecida"},
                mutation_class="CreateUpdateOrganization",
                mutation_parameters={
                    "area": self.create_area(area="desconhecida"),
                    "slug": "desconhecida",
                    "name": "desconhecida",
                    "description": "desconhecida",
                },
            )
        else:
            org_name = (
                org_dict.get("title", "desconhecida")
                if "title" in org_dict
                else org_dict.get("name", "desconhecida")
            )
            org_description = org_dict.get("description", "desconhecida")

            org_id = (
                org_dict.get("name") if "title" in org_dict else org_dict.get("organization_id")
            )
            org_slug = "desconhecida" if org_id is None else org_id.replace("-", "_")

            org_name = org_slug if org_name is None else org_name
            package_to_part_org = {
                "area": self.create_area("desconhecida"),
                "slug": org_slug,
                "name": org_name,
                "description": org_description,
            }
            r, graphql_org_id = self.create_update(
                query_class="allOrganization",
                query_parameters={"$slug: String": org_slug},
                mutation_class="CreateUpdateOrganization",
                mutation_parameters=package_to_part_org,
            )
        return graphql_org_id

    def create_area(self, area):

        area = area.replace("-", ".").replace(" ", ".")
        r, id = self.create_update(
            query_class="allArea",
            query_parameters={"$slug: String": area.replace(".", "_")},
            mutation_class="CreateUpdateArea",
            mutation_parameters={
                "slug": area.replace(".", "_"),
                "name": self.area_dict.get(area, {}).get("label", {}).get("pt", "Desconhecida"),
                "key": "unknown" if area == "desconhecida" else area,
            },
        )
        return id

    def test(self):
        query = """
            query($slug: String) {
                    allTag(slug:$slug){
                        edges{
                        node{
                            id,
                            slug,
                        }
                        }
                    }
                    }
        """
        r = requests.get(
            url=self.base_url,
            json={"query": query, "variables": {"slug": "corrupcao"}},
            # headers=self.header,
        )
        print(r)
