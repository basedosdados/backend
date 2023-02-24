### TODO fazer coverage para os trez tipos de recurso utilizando parse_temporal_coverage
### TODO filtrar pelo id do modelo pai
### TODO usar dataframe para controle dos packages, coluna migrate 'e alterada para 1 quando o package 'e migrado


from datetime import datetime
import json
import re
import requests

from pathlib import Path
import pandas as pd


def get_token(username, password):
    r = requests.post(
        "http://localhost:8080/api/v1/graphql",
        # "https://staging.backend.dados.rio/api/v1/graphql",
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


def get_package_model(id):
    url = f"https://basedosdados.org/api/3/action/package_show?name_or_id={id}"
    packages = requests.get(url, verify=False).json()["result"]
    df = pd.DataFrame(data={"packages": packages})
    df["package_id"] = df["packages"].apply(lambda x: x["id"])
    return df


def pprint(msg):
    print(">>>>> ", msg)


def parse_temporal_coverage(temporal_coverage):
    # Extrai as informações de data e intervalo da string
    start_str, interval_str, end_str = re.split(r"[(|)]", temporal_coverage)

    start_len = 0 if start_str == "" else len(start_str.split("-"))
    end_len = 0 if end_str == "" else len(end_str.split("-"))

    def parse_date(position, date_str, date_len):
        result = {}
        if date_len == 3:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            result[f"{position}_year"] = date.year
            result[f"{position}_month"] = date.month
            result[f"{position}_day"] = date.month
        elif date_len == 2:
            date = datetime.strptime(date_str, "%Y-%m")
            result[f"{position}_year"] = date.year
            result[f"{position}_month"] = date.month
        elif date_len == 1:
            date = datetime.strptime(date_str, "%Y")
            result[f"{position}_year"] = date.year
        return result

    start_result = parse_date(position="start", date_str=start_str, date_len=start_len)
    end_result = parse_date(position="end", date_str=end_str, date_len=end_len)
    start_result.update(end_result)
    start_result["interval"] = int(interval_str)

    return start_result


class Migration:
    def __init__(self, token):
        self.base_url = "http://localhost:8080/api/v1/graphql"
        # "https://staging.backend.dados.rio/api/v1/graphql"
        self.header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def get_id(
        self, query_class, query_parameters
    ):  # sourcery skip: avoid-builtin-shadow
        _filter = ", ".join(list(query_parameters.keys()))
        keys = [
            parameter.replace("$", "").split(":")[0]
            for parameter in list(query_parameters.keys())
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

        if "data" in r:
            if r["data"][query_class]["edges"] == []:
                id = None
                print(f"get: not found {query_class}", dict(zip(keys, values)))
            else:
                id = r["data"][query_class]["edges"][0]["node"]["id"]
                print(f"get: found {id}")
                id = id.split(":")[1]
            return r, id
        else:
            print("get:  Error:", json.dumps(r, indent=4))
            raise Exception("get: Error")

    def create_update(
        self, mutation_class, mutation_parameters, query_class, query_parameters
    ):
        r, id = self.get_id(query_class=query_class, query_parameters=query_parameters)
        if id is not None:
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
        r = requests.post(
            self.base_url,
            json={"query": query, "variables": {"input": mutation_parameters}},
            headers=self.header,
        ).json()

        if "data" in r:
            if r["data"][mutation_class]["errors"] != []:
                print(f"create: not found {mutation_class}", mutation_parameters)
                print("create: error\n", json.dumps(r, indent=4), "\n")
                id = None
            else:
                id = r["data"][mutation_class][_classe]["id"]
                print(f"create: created {id}")
                id = id.split(":")[1]

            return r, id
        else:
            print("\n", "create: query\n", query, "\n")
            print("create: input\n", json.dumps(mutation_parameters, indent=4), "\n")
            print("create: error\n", json.dumps(r, indent=4), "\n")
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

        if r["data"][f"Delete{classe}"]["ok"] == True:
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
            tag_slug = obj.get("name")
            tag_name = obj.get("display_name")
            r, id = self.create_update(
                mutation_class="CreateUpdateTag",
                mutation_parameters={
                    "slug": "desconhecido"
                    if tag_slug is None
                    else tag_slug.replace(" ", "_"),
                    "name": "desconhecido"
                    if tag_name is None
                    else tag_name.replace(" ", "_"),
                },
                query_class="allTag",
                query_parameters={"$slug: String": tag_slug},
            )
            ids.append(id)

        return ids

    def create_availability(self, obj):
        r, id = self.create_update(
            mutation_class="CreateUpdateAvailability",
            mutation_parameters={
                "slug": obj.get("availability"),
                "name": obj.get("availability"),
            },
            query_class="allAvailability",
            query_parameters={"$slug: String": obj.get("availability")},
        )

        return id

    def create_entity(self, obj=None):
        if (obj is None) or (obj.get("entity") is None):
            r, id = self.create_update(
                mutation_class="CreateUpdateEntity",
                mutation_parameters={
                    "slug": "desconhecida",
                    "name": "todo",
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
            r, id = self.create_update(
                mutation_class="CreateUpdateUpdateFrequency",
                mutation_parameters={
                    "entity": self.create_entity(obj=None),
                    "number": update_frequency_dict[update_frequency],
                },
                query_class="allUpdatefrequency",
                query_parameters={
                    "$number: Int": update_frequency_dict[update_frequency]
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
                            "$number: Int": update_frequency_dict[update_frequency]
                        },
                    )
                elif ob.get("entity") is None:
                    r, id = self.create_update(
                        mutation_class="CreateUpdateUpdateFrequency",
                        mutation_parameters={
                            "entity": self.create_entity(obj=None),
                            "number": update_frequency_dict[update_frequency],
                        },
                        query_class="allUpdatefrequency",
                        query_parameters={
                            "$number: Int": update_frequency_dict[update_frequency]
                        },
                    )
                else:
                    r, id = self.create_update(
                        mutation_class="CreateUpdateUpdateFrequency",
                        mutation_parameters={
                            "entity": self.create_entity(obj=None),
                            "number": 0,
                        },
                        query_class="allUpdatefrequency",
                        query_parameters={"$number: Int": 0},
                    )

        return id

    def create_observation_level(self, observation_levels=None):

        if observation_levels is None:
            r, id = self.create_update(
                mutation_class="CreateUpdateObservationLevel",
                mutation_parameters={
                    "entity": self.create_entity(obj=None),
                },
                query_class="allObservationlevel",
                query_parameters={
                    "$id: ID": self.create_entity(obj=None),
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
                        "$id: ID": entity_id,
                    },
                )

        return id

    def create_license(self):
        r, id = self.create_update(
            mutation_class="CreateUpdateLicense",
            mutation_parameters={
                "slug": "desconhecida",
                "name": "todo",
                "url": "todo.com",
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

    def create_directory_columns(self, column):
        if column.get("covered_by_dictionary") == "yes":
            r, id = self.get_id(
                query_class="allColumn",
                query_parameters={
                    "$name: String": column.get("directory_column").get("column_name"),
                },
            )

            return id
        else:
            return None

    def create_columns(self, objs, table_id):

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
                query_parameters={"$name: String": "desconhecida"},
            )
            ids = [id]
        else:
            ids = []
            for column in objs:
                r, id = self.create_update(
                    mutation_class="CreateUpdateColumn",
                    mutation_parameters={
                        "table": table_id,
                        "bigqueryType": self.create_bq_type(
                            column.get("bigquery_type")
                        ),
                        "directoryPrimaryKey": self.create_directory_columns(column),
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
                    query_parameters={"$name: String": column.get("name")},
                )
                ids.append(id)

        return ids

    def create_part_org(self, partner_organization):

        part_org_name = partner_organization.get("organization_id")

        if part_org_name is None:
            r, part_org_id = self.create_update(
                query_class="allOrganization",
                query_parameters={"$slug: String": "desconhecida"},
                mutation_class="CreateUpdateOrganization",
                mutation_parameters={
                    "area": self.create_update(
                        query_class="allArea",
                        query_parameters={"$slug: String": "desconhecida"},
                        mutation_class="CreateUpdateArea",
                        mutation_parameters={"slug": "desconhecida"},
                    )[1],
                    "slug": "desconhecida",
                    "name": "desconhecida",
                    "description": "desconhecida",
                },
            )
        else:
            part_org_slug = partner_organization.get("organization_id").replace(
                "-", "_"
            )
            package_to_part_org = {
                "area": self.create_update(
                    query_class="allArea",
                    query_parameters={"$slug: String": "desconhecida"},
                    mutation_class="CreateUpdateArea",
                    mutation_parameters={"slug": "desconhecida"},
                )[1],
                "slug": part_org_slug,
                "name": partner_organization.get("name"),
                "description": "",
            }
            r, part_org_id = self.create_update(
                query_class="allOrganization",
                query_parameters={"$slug: String": part_org_slug},
                mutation_class="CreateUpdateOrganization",
                mutation_parameters=package_to_part_org,
            )
        return part_org_id

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
