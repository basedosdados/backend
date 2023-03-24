from datetime import datetime
import json
import re
import requests
import time

from pathlib import Path
import pandas as pd
from tqdm import tqdm
import itertools

from data.enums.availability import AvailabilityEnum
from data.enums.bigquery_type import BigQueryTypeEnum
from data.enums.entity import EntityEnum, EntityDateTimeEnum
from data.enums.language import LanguageEnum
from data.enums.license import LicenseEnum
from data.enums.status import StatusEnum

import threading


from unidecode import unidecode


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

    with open(
        "./basedosdados_api/schemas/repository/bd_spatial_coverage_tree.json"
    ) as f:
        area = json.load(f)

    return area.get("result")


def class_to_dict(class_obj):
    return {
        name: getattr(class_obj, name)
        for name in dir(class_obj)
        if not name.startswith("__")
    }


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
        # if start_str == "" and end_str != "":
        #     start_str = end_str
        # elif end_str == "" and start_str != "":
        #     end_str = start_str
    elif len(temporal_coverage) in {4, 7, 9}:
        start_str, interval_str, end_str = temporal_coverage, None, temporal_coverage

    start_len = 0 if start_str == "" else len(start_str.split("-"))
    end_len = 0 if end_str == "" else len(end_str.split("-"))

    def parse_date(position, date_str, date_len):
        result = {}

        if date_str != "":
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

    if interval_str != 0 and interval_str is not None:
        start_result["interval"] = int(interval_str)
    # start_result["interval"] = interval_str

    return start_result


def get_credentials(mode):
    j = json.load(open("./credentials.json"))
    return j[mode]["username"], j[mode]["password"], j[mode]["url"]


class Migration:
    def __init__(self, mode):
        self.mode = mode
        self.username, self.password, self.base_url = get_credentials(mode)
        self.header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.get_token()}",
        }
        self.df_area = pd.read_csv(
            "./utils/migration/data/enums/spatial_coverage_tree.csv"
        )
        self.token_updater = threading.Thread(target=self.update_token_periodically)
        self.token_updater.setDaemon(True)
        self.token_updater.start()

    def update_token_periodically(self):
        while True:
            time.sleep(300)  # Sleep for 5 minutes (300 seconds)
            new_token = self.get_token()
            # Implement this method to obtain a new token
            self.header["Authorization"] = f"Bearer {new_token}"
            print("$$$$$$$$$$$$$$$$$$$$$ Token updated $$$$$$$$$$$$$$$$$$$$$")

    def get_token(self):
        r = requests.post(
            self.base_url,
            headers={"Content-Type": "application/json"},
            json={
                "query": """
                    mutation tokenAuth($username: String!, $password: String!) {
                        tokenAuth(
                            email: $username,
                            password: $password,
                        ) {
                            payload,
                            refreshExpiresIn,
                            token
                        }
                    }
                """,
                "variables": {"username": self.username, "password": self.password},
            },
        )
        r.raise_for_status()
        return r.json()["data"]["tokenAuth"]["token"]

    def get_id(self, query_class, query_parameters):
        _filter = ", ".join(list(query_parameters.keys()))
        keys = [
            parameter.replace("$", "").split(":")[0]
            for parameter in list(query_parameters.keys())
        ]
        values = list(query_parameters.values())
        _input = ", ".join([f"{key}:${key}" for key in keys])

        column_query = """
            columns {
                edges {
                    node {
                        id
                    }
                }
            }
        """

        columns = column_query if query_class == "allObservationlevel" else ""
        query = f"""
        query({_filter}) {{
            {query_class}({_input}) {{
                edges {{
                    node {{
                        id
                        {columns}
                    }}
                }}
            }}
        }}
        """

        response = requests.post(
            url=self.base_url,
            json={"query": query, "variables": dict(zip(keys, values))},
            headers=self.header,
        ).json()

        if "data" in response and response is not None:
            query_class_data = response.get("data", {}).get(query_class, {}) or {}
            edges = query_class_data.get("edges", [])

            if not edges:
                return response, None

            node = edges[0]["node"]

            if columns != "":
                columns = edges[0]["node"]["columns"]["edges"]
                cols_ids = [d.get("node").get("id").split(":")[-1] for d in columns]
                return cols_ids, node["id"].split(":")[1]
            else:
                return response, node["id"].split(":")[1]
        else:
            print("get: Error:", json.dumps(response, indent=4, ensure_ascii=False))
            raise Exception("get: Error")

    def create_update(
        self,
        mutation_class,
        mutation_parameters,
        query_class,
        query_parameters,
        update=False,
    ):

        response, node_id = self.get_id(
            query_class=query_class, query_parameters=query_parameters
        )
        time.sleep(0.1)

        if node_id is not None and not update:
            if mutation_class != "CreateUpdateObservationLevel":
                response["r"] = "query"
            return response, node_id

        _class = mutation_class.replace("CreateUpdate", "").lower()
        query = f"""
        mutation($input:{mutation_class}Input!) {{
            {mutation_class}(input: $input) {{
                errors {{
                    field,
                    messages
                }},
                clientMutationId,
                {_class} {{
                    id,
                }}
            }}
        }}
        """

        if update and node_id is not None:
            mutation_parameters["id"] = node_id

        for retry in range(5):
            try:
                response = requests.post(
                    self.base_url,
                    json={"query": query, "variables": {"input": mutation_parameters}},
                    headers=self.header,
                ).json()
                time.sleep(0.1)
                break
            except Exception as e:
                print(f"retrying...{retry}")
                print("create: Error:", e)

        response["r"] = "mutation"

        if "data" not in response or response is None:
            self.get_mutation_error(
                mutation_class, query, mutation_parameters, response
            )

        mutation_class_data = response.get("data", {}).get(mutation_class, {}) or {}

        if response.get("errors", []) or mutation_class_data.get("errors", []):
            self.get_mutation_error(
                mutation_class, query, mutation_parameters, response
            )

        _id = mutation_class_data[_class]["id"].split(":")[1]
        return response, _id

    def get_mutation_error(self, mutation_class, query, mutation_parameters, response):
        print(f"create: not found {mutation_class}", mutation_parameters)
        print(
            "create: error\n", json.dumps(response, indent=4, ensure_ascii=False), "\n"
        )
        raise Exception("create: Error")

    def delete(self, class_name, node_id):
        query = f"""
            mutation {{
                Delete{class_name}(id: "{node_id}") {{
                    ok,
                    errors
                }}
            }}
        """

        response = requests.post(
            self.base_url,
            json={"query": query},
            headers=self.header,
        ).json()

        if response["data"][f"Delete{class_name}"]["ok"]:
            print(f"Deleted {class_name.lower()} {node_id}")
        else:
            errors = response["data"][f"Delete{class_name}"]["errors"]
            print(f"Delete errors for {class_name.lower()} {node_id}:", errors)

        return response

    def create_themes(self, objs):
        theme_ids = []

        for obj in objs:
            theme_name = obj.get("name")
            response, theme_id = self.create_update(
                mutation_class="CreateUpdateTheme",
                mutation_parameters={
                    "slug": theme_name,
                    "name": obj.get("title"),
                },
                query_class="allTheme",
                query_parameters={"$slug: String": theme_name},
            )
            theme_ids.append(theme_id)

        return theme_ids

    def create_tags(self, objs):
        tag_ids = []

        for obj in objs:
            tag_slug = obj.get("name").replace("+", "").lower().replace(" ", "_")
            tag_name = obj.get("display_name")
            tag_slug = "desconhecida" if tag_slug is None else unidecode(tag_slug)
            tag_name = (
                "desconhecida" if tag_name is None else tag_name.replace(" ", "_")
            )

            response, tag_id = self.create_update(
                mutation_class="CreateUpdateTag",
                mutation_parameters={
                    "slug": tag_slug,
                    "name": tag_name,
                },
                query_class="allTag",
                query_parameters={"$slug: String": unidecode(tag_slug)},
            )
            tag_ids.append(tag_id)

        return tag_ids

    def create_availability(self, obj):
        slug = obj.get("availability", "unknown")
        slug = slug if slug is not None else "unknown"
        name = obj.get("name", None)
        nameEn = slug.replace("_", " ").title()

        r, id = self.create_update(
            mutation_class="CreateUpdateAvailability",
            mutation_parameters={
                "slug": slug,
                "name": name,
                "nameEn": nameEn,
            },
            query_class="allAvailability",
            query_parameters={"$slug: String": slug},
        )

        return id

    def _create_update_entity(self, slug, name, category):
        r, id = self.create_update(
            mutation_class="CreateUpdateEntity",
            mutation_parameters={
                "slug": slug,
                "name": name,
                "category": category,
            },
            query_class="allEntity",
            query_parameters={
                "$slug: String": slug,
            },
        )
        return id

    def create_entity(self, obj=None):
        if obj is None or obj.get("entity") is None:
            default_parameters = {
                "slug": "unknown",
                "name": "Desconhecida",
                "category": "unknown",
            }

            return self._create_update_entity(**default_parameters)
        else:

            entity_dict = {
                key: value
                for entity in EntityEnum
                for key, value in class_to_dict(entity).items()
            }
            slug = obj.get("entity", "unknown")
            if slug == "langugage":
                slug = "language"

            name = obj.get("label") or entity_dict[slug].get("label")
            category = obj.get("category") or entity_dict[slug].get("category")

            category_id = self.create_category(category)

            parameters = {
                "slug": slug,
                "name": name,
                "category": category_id,
            }

            # print(parameters)

            return self._create_update_entity(**parameters)

    def _create_update_frequency_for_entity(self, entity_id, update_frequency_number):
        r, id = self.create_update(
            mutation_class="CreateUpdateUpdate",
            mutation_parameters={
                "entity": entity_id,
                "number": update_frequency_number,
            },
            query_class="allUpdate",
            query_parameters={
                "$number: Int": update_frequency_number,
                "$entity_Id: ID": entity_id,
            },
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

        if observation_levels is None or len(observation_levels) == 0:
            observation_levels = [{"entity": "unknown"}]

        for ob in observation_levels:
            entity_key = ob.get("entity") if ob else None
            if (
                entity_key in list(class_to_dict(EntityDateTimeEnum).keys())
                and entity_key is not None
            ):
                entity_id = self.create_entity(obj=ob)
                update_frequency_number = update_frequency_dict[update_frequency]
            else:
                update_frequency_number = 0
                entity_id = self.create_entity(obj={"entity": "unknown"})
            id = self._create_update_frequency_for_entity(
                entity_id, update_frequency_number
            )

        return id

    def _create_observation_level_for_entity(self, entity_id, obs_resource):

        resource_type = list(obs_resource.keys())[0]
        resource_id = list(obs_resource.values())[0]
        resource_filter = f"{resource_type}_Id"

        mutation_parameters = {
            "entity": entity_id,
            resource_type: resource_id,
        }

        r, id = self.create_update(
            mutation_class="CreateUpdateObservationLevel",
            mutation_parameters=mutation_parameters,
            query_class="allObservationlevel",
            query_parameters={
                "$entity_Id: ID": entity_id,
                f"${resource_filter}: ID": resource_id,
            },
        )

        return id

    def create_observation_level(self, observation_levels=None, obs_resource=None):

        if observation_levels is None or len(observation_levels) == 0:
            observation_levels = [{"entity": "unknown"}]
        ids = []

        for ob in observation_levels:
            entity_id = self.create_entity(obj=ob)
            id = self._create_observation_level_for_entity(entity_id, obs_resource)
            ids.append(id)

        return ids

    def create_license(self, obj):
        slug = obj["slug"]
        name = obj["name"]

        slug = slug if slug is not None else "desconhecida"
        name = name if name is not None else "Desconhecida"
        r, id = self.create_update(
            mutation_class="CreateUpdateLicense",
            mutation_parameters={
                "slug": slug,
                "name": name,
                "url": "todo.com",
            },
            query_class="allLicense",
            query_parameters={"$slug: String": slug},
        )

        return id

    def create_bq_type(self, obj):
        r, id = self.create_update(
            mutation_class="CreateUpdateBigQueryType",
            mutation_parameters={
                "name": obj,
            },
            query_class="allBigquerytype",
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
            if resource.get("temporal_coverage") == []
            or resource.get("temporal_coverage") is None
            else resource.get("temporal_coverage")
        )

        if temporal_temporal_coverages != [None]:
            temporal_temporal_coverages_chain = [
                s.split(",") if "," in s else [s] for s in temporal_temporal_coverages
            ]
            temporal_temporal_coverages = list(
                itertools.chain(*temporal_temporal_coverages_chain)
            )

        for temporal_coverage in temporal_temporal_coverages:
            if temporal_coverage is not None:
                resource_to_temporal_coverage = parse_temporal_coverage(
                    temporal_coverage
                )
                resource_to_temporal_coverage["coverage"] = coverage_id

                r, id = self.create_update(
                    query_class="allDatetimerange",
                    query_parameters={"$coverage_Id: ID": coverage_id},
                    mutation_class="CreateUpdateDateTimeRange",
                    mutation_parameters=resource_to_temporal_coverage,
                )

    def _create_coverage_for_area(self, resource, coverage, area):
        coverage_type = list(coverage.keys())[0]
        coverage_value = list(coverage.values())[0]
        coverage_filter = f"{coverage_type}_Id"

        package_to_coverage = {
            coverage_type: coverage_value,
            "area": self.create_area(obj={"key": area}),
        }
        r, id = self.create_update(
            query_class="allCoverage",
            query_parameters={f"${coverage_filter}: ID": coverage_value},
            mutation_class="CreateUpdateCoverage",
            mutation_parameters=package_to_coverage,
        )

        self.create_temporal_coverage(resource=resource, coverage_id=id)

        return id

    def create_coverage(self, resource, coverage):
        area_slugs = resource.get("spatial_coverage") or ["desconhecida"]

        ids = []

        for area in area_slugs:
            id = self._create_coverage_for_area(resource, coverage, area)
            ids.append(id)

        return ids[-1]

    def get_obs_level(self, obs_levels, column_name):
        for obs in obs_levels:
            if column_name in obs.get("columns", []):
                return obs

    def _create_column(self, column, table_id, resource):
        column_name = column.get("name", "desconhecida")
        mutation_parameters = {
            "table": table_id,
            "bigqueryType": self.create_bq_type(
                column.get("bigquery_type", "desconhecida")
            ),
            "name": column_name,
            "isInStaging": column.get("is_in_staging"),
            "isPartition": column.get("is_partition"),
            "description": column.get("description"),
            "coveredByDictionary": column.get("covered_by_dictionary") == "yes",
            "measurementUnit": column.get("measurement_unit"),
            "containsSensitiveData": column.get("contains_sensitive_data"),
            "observations": column.get("observations"),
        }

        if "directory_primary_key" in column:
            mutation_parameters["directoryPrimaryKey"] = self.create_directory_columns(
                column, table_id
            )

        if resource.get("observation_level") is not None:
            obs_level = self.get_obs_level(
                resource.get("observation_level"), column_name
            )
        else:
            obs_level = None

        if obs_level is not None:
            entity_id = self.create_entity(obj=obs_level)
            obs_id = self.get_id(
                query_class="allObservationlevel",
                query_parameters={
                    "$entity_Id: ID": entity_id,
                    "$table_Id: ID": table_id,
                },
            )[1]
            mutation_parameters["observationLevel"] = obs_id

        r, id = self.create_update(
            mutation_class="CreateUpdateColumn",
            mutation_parameters=mutation_parameters,
            query_class="allColumn",
            query_parameters={
                "$name: String": column_name,
                "$table_Id: ID": table_id,
            },
        )

        if r.get("r") == "mutation":
            coverage_id = self.create_coverage(
                resource=resource, coverage={"column": id}
            )

        return id

    def create_columns(self, resource, table_id):
        objs = resource.get("columns")

        if objs is None:
            objs = [{}]

        ids = []
        for column in tqdm(objs):
            id = self._create_column(column, table_id, resource)
            ids.append(id)

        return ids

    def create_org(self, org_dict):
        dataset_remove_prefix = None
        if org_dict is None:
            response, graphql_org_id = self.create_update(
                query_class="allOrganization",
                query_parameters={"$slug: String": "desconhecida"},
                mutation_class="CreateUpdateOrganization",
                mutation_parameters={
                    "area": self.create_area(obj="desconhecida"),
                    "slug": "desconhecida",
                    "name": "desconhecida",
                    "description": "desconhecida",
                },
            )

        else:
            org_name = org_dict.get("title") or org_dict.get("name") or "desconhecida"
            org_description = org_dict.get("description", "desconhecida")
            org_id = org_dict.get("name") or org_dict.get("organization_id")
            org_slug = (
                "desconhecida"
                if org_id is None
                else org_id.replace("-", "_")
                .replace(".", "_")
                .lower()
                .replace(" ", "_")
            )
            org_slug = unidecode(org_slug)

            org_slug_parts = org_slug.split("_", 1)
            df = self.df_area
            df["possible_areas"] = df["id"].apply(
                lambda x: x.replace(".", "_").split("_", 1)[-1]
            )
            possible_areas = df["possible_areas"].to_list()
            area_prefix = "unknown"
            if len(org_slug_parts) > 1:
                prefix = org_slug_parts[0].lower()
                if prefix == "mundo":
                    prefix = "world"
                if prefix in possible_areas:
                    org_slug = org_slug_parts[1]
                    dataset_remove_prefix = prefix + "_" + org_slug + "_"
                    area_prefix = prefix

            if org_slug_parts[0].lower() == "mundo":
                dataset_remove_prefix = "mundo_" + org_slug + "_"

            area_row = df[df["possible_areas"] == area_prefix]
            area_name_pt = area_row["label__pt"].values[0]
            area_name_en = area_row["label__en"].values[0]
            print("org_slug: ", org_slug)
            package_to_part_org = {
                "area": self.create_area(
                    obj={
                        "key": area_prefix,
                        "name": area_name_pt,
                        "name_en": area_name_en,
                    }
                ),
                "slug": org_slug,
                "name": org_name,
                "description": org_description,
            }

            response, graphql_org_id = self.create_update(
                query_class="allOrganization",
                query_parameters={"$slug: String": org_slug},
                mutation_class="CreateUpdateOrganization",
                mutation_parameters=package_to_part_org,
            )
        return graphql_org_id, dataset_remove_prefix

    def create_area(self, obj):

        if obj == "desconhecida":
            obj = {
                "key": "unknown",
                "name": "Desconhecida",
                "name_en": "Unknown",
            }

        key = obj.get("key", "unknown")
        key = "unknown" if key == "desconhecida" else key
        key = "sa.br" if key == "br" else key
        df = self.df_area
        area_row = df[df["id"] == key]

        name = obj.get("name", None) or area_row["label__pt"].values[0]
        name_en = obj.get("name_en", None) or area_row["label__en"].values[0]
        slug = key.replace(".", "_")
        r, id = self.create_update(
            query_class="allArea",
            query_parameters={"$slug: String": slug},
            mutation_class="CreateUpdateArea",
            mutation_parameters={
                "name": name,
                "slug": slug,
                "nameEn": name_en,
            },
        )
        return id

    def create_language(self, obj):

        slug = obj.get("slug", "unknown")
        name = obj.get("name", 'Desconhecida"')

        r, id = self.create_update(
            query_class="allLanguage",
            query_parameters={"$slug: String": slug},
            mutation_class="CreateUpdateLanguage",
            mutation_parameters={
                "name": name,
                "slug": slug,
            },
        )
        return id

    def create_status(self, obj):

        slug = obj.get("slug")
        name = obj.get("name")

        r, id = self.create_update(
            query_class="allStatus",
            query_parameters={"$slug: String": slug},
            mutation_class="CreateUpdateStatus",
            mutation_parameters={
                "name": name,
                "slug": slug,
            },
        )
        return id

    def create_category(self, category):
        r, id = self.create_update(
            mutation_class="CreateUpdateEntityCategory",
            mutation_parameters={
                "slug": category,
                "name": category,
                "nameEn": category.capitalize(),
            },
            query_class="allEntitycategory",
            query_parameters={"$slug: String": category},
        )

        return id

    def create_enum(self, migrate_enum={}):

        if migrate_enum["AvailabilityEnum"]:
            availabilities = class_to_dict(AvailabilityEnum())
            for key in availabilities:
                obj = {
                    "availability": key,
                    "name": availabilities[key].get("label"),
                }
                self.create_availability(obj)
            print("AvailabilityEnum Done")

        if migrate_enum["LicenseEnum"]:
            licenses = class_to_dict(LicenseEnum())
            for key in licenses:
                obj = {
                    "slug": key,
                    "name": licenses[key].get("label"),
                }
                self.create_license(obj)
            print("LicenseEnum Done")

        if migrate_enum["LanguageEnum"]:
            languages = class_to_dict(LanguageEnum())
            for key in languages:
                obj = {
                    "slug": languages[key].get("abrev"),
                    "name": languages[key].get("label"),
                }
                self.create_language(obj)
            print("LanguageEnum Done")

        if migrate_enum["StatusEnum"]:
            status = class_to_dict(StatusEnum())
            for key in status:
                obj = {
                    "slug": key,
                    "name": status[key].get("label"),
                }
                self.create_status(obj)
            print("StatusEnum Done")

        if migrate_enum["BigQueryTypeEnum"]:
            bq_types = class_to_dict(BigQueryTypeEnum())
            for key in bq_types:
                self.create_bq_type(bq_types[key].get("label"))
            print("BigQueryTypeEnum Done")

        if migrate_enum["EntityEnum"]:
            entity_dict = entity_dict = {
                key: value
                for entity in EntityEnum
                for key, value in class_to_dict(entity).items()
            }
            for key in entity_dict:
                obj = {
                    "entity": key,
                    "label": entity_dict[key].get("label"),
                    "category": entity_dict[key].get("category"),
                }
                self.create_entity(obj)
            print("EntityEnum Done")

        if migrate_enum["AreaEnum"]:

            areas = self.df_area["id"].to_list()
            name_pt = self.df_area["label__pt"].to_list()
            name_en = self.df_area["label__en"].to_list()

            for key, name_pt, name_en in zip(areas, name_pt, name_en):
                obj = {
                    "key": key,
                    "name": name_pt,
                    "name_en": name_en,
                }
                # print(obj)
                self.create_area(obj)
            print("Area Done")

        print(
            "\n===================================== ENUMS DONE!!!! =====================================\n\n\n"
        )

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
