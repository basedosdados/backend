### TODO fazer coverage para os trez tipos de recurso utilizando parse_temporal_coverage

import requests
import json
import re
from datetime import datetime

j = json.load(open("./credentials.json"))
USERNAME = j["username"]
PASSWORD = j["password"]


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


def get_bd_packages():
    url = "https://basedosdados.org"
    api_url = f"{url}/api/3/action/package_search?q=&rows=2000"
    return requests.get(api_url, verify=False).json()["result"]["results"]


def get_package_model():
    url = "https://basedosdados.org/api/3/action/package_show?name_or_id=br-sgp-informacao"
    return requests.get(url, verify=False).json()["result"]


from datetime import datetime
import re


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
        if id is None:
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
                print(
                    "create: input\n", json.dumps(mutation_parameters, indent=4), "\n"
                )
                print("create: error\n", json.dumps(r, indent=4), "\n")
                raise Exception("create: Error")
        else:
            return r, id

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
            r, id = self.create_update(
                mutation_class="CreateUpdateTag",
                mutation_parameters={
                    "slug": obj.get("name"),
                    "name": obj.get("display_name"),
                },
                query_class="allTag",
                query_parameters={"$slug: String": obj.get("name")},
            )
            ids.append(id)

        return ids

    def create_availability(self, obj):
        r, id = self.create_update(
            mutation_class="CreateUpdateAvailability",
            mutation_parameters={
                "slug": obj.get("availability"),
                "name": obj.get("availability").capitalize(),
            },
            query_class="allAvailability",
            query_parameters={"$slug: String": obj.get("availability")},
        )

        return id

    def create_entity(self, obj=None):
        if obj is None:
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
            "day ": 1,
            "week": 1,
            "month ": 1,
            "quarter ": 1,
            "semester": 1,
            "one_year": 1,
            "two_years ": 2,
            "three_years ": 3,
            "four_years": 4,
            "five_years": 5,
            "ten_years ": 10,
            "unique": 0,
            "recurring ": 0,
            "uncertain ": 0,
            "other ": 0,
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
                if ob["entity"] in update_frequency_entity_dict:
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

        return id

    def create_observation_level(self, observation_levels=None):

        if observation_levels is None:
            r, id = self.create_update(
                mutation_class="CreateUpdateObservationLevel",
                mutation_parameters={
                    "entity": self.create_entity(obj=None)[1],
                },
                query_class="allObservationlevel",
                query_parameters={
                    "$id: ID": self.create_entity(obj=None)[1],
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
        ids = []
        for column in objs:
            r, id = self.create_update(
                mutation_class="CreateUpdateColumn",
                mutation_parameters={
                    "table": table_id,
                    "bigqueryType": self.create_bq_type(column.get("bigquery_type")),
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


if __name__ == "__main__":
    TOKEN = get_token(USERNAME, PASSWORD)
    # packages = get_bd_packages()
    package = get_package_model()
    m = Migration(TOKEN)
    entity_id = m.create_entity()
    update_frequency_id = m.create_update_frequency()
    # r = m.delete(classe="Dataset", id="77239376-6662-4d64-8950-2f57f1225e53")

    for p in [package]:
        # create tags
        tags_ids = m.create_tags(objs=p.get("tags"))
        themes_ids = m.create_themes(objs=p.get("groups"))

        ## create organization

        print("\nCreate Organization")
        org_slug = p.get("organization").get("name").replace("-", "_")
        package_to_org = {
            "area": m.create_update(
                query_class="allArea",
                query_parameters={"$slug: String": "desconhecida"},
                mutation_class="CreateUpdateArea",
                mutation_parameters={"slug": "desconhecida"},
            )[1],
            "slug": org_slug,
            "name": p.get("organization").get("title"),
            "description": p.get("organization").get("description"),
        }
        r, org_id = m.create_update(
            query_class="allOrganization",
            query_parameters={"$slug: String": org_slug},
            mutation_class="CreateUpdateOrganization",
            mutation_parameters=package_to_org,
        )

        ## create dataset
        print("\nCreate Dataset")
        package_to_dataset = {
            "organization": org_id,
            "slug": p["name"].replace("-", "_"),
            "name": p["title"],
            "description": p["notes"],
            "tags": tags_ids,
            "themes": themes_ids,
        }
        r, dataset_id = m.create_update(
            query_class="allDataset",
            query_parameters={"$slug: String": p["name"].replace("-", "_")},
            mutation_class="CreateUpdateDataset",
            mutation_parameters=package_to_dataset,
        )

        for resource in p["resources"]:
            resource_type = resource["resource_type"]

            if resource_type == "bdm_table":
                print("\nCreate Table")
                package_to_part_org = {
                    "area": m.create_update(
                        query_class="allArea",
                        query_parameters={"$slug: String": "desconhecida"},
                        mutation_class="CreateUpdateArea",
                        mutation_parameters={"slug": "desconhecida"},
                    )[1],
                    "slug": resource["partner_organization"]
                    .get("organization_id")
                    .replace("-", "_"),
                    "name": resource["partner_organization"].get("name"),
                    "description": "",
                }
                r, part_org_id = m.create_update(
                    query_class="allOrganization",
                    query_parameters={
                        "$slug: String": resource["partner_organization"]
                        .get("organization_id")
                        .replace("-", "_")
                    },
                    mutation_class="CreateUpdateOrganization",
                    mutation_parameters=package_to_part_org,
                )
                update_frequency_id = m.create_update_frequency(
                    observation_levels=resource["observation_level"],
                    update_frequency=resource["update_frequency"],
                )
                resource_to_table = {
                    "dataset": dataset_id,
                    "license": m.create_license(),
                    "partnerOrganization": part_org_id,
                    "updateFrequency": update_frequency_id,
                    "slug": resource["table_id"],
                    "name": resource["name"],
                    "pipeline": m.create_update(
                        query_class="allPipeline",
                        query_parameters={"$githubUrl: String": "todo.com"},
                        mutation_class="CreateUpdatePipeline",
                        mutation_parameters={"githubUrl": "todo.com"},
                    )[1],
                    "description": resource["description"],
                    "isDirectory": False,
                    "dataCleaningDescription": resource["data_cleaning_description"],
                    "dataCleaningCodeUrl": resource["data_cleaning_code_url"],
                    "rawDataUrl": resource["raw_files_url"],
                    "auxiliaryFilesUrl": resource["auxiliary_files_url"],
                    "architectureUrl": resource["architecture_url"],
                    "sourceBucketName": resource["source_bucket_name"],
                    "uncompressedFileSize": resource["uncompressed_file_size"],
                    "compressedFileSize": resource["compressed_file_size"],
                    "numberRows": 0,
                    "numberColumns": len(p["resources"][0]["columns"]),
                    "observationLevel": m.create_observation_level(
                        observation_levels=resource["observation_level"]
                    ),
                }

                r, table_id = m.create_update(
                    mutation_class="CreateUpdateTable",
                    mutation_parameters=resource_to_table,
                    query_class="allTable",
                    query_parameters={
                        "$slug: String": resource["table_id"],
                        "$name: String": resource["name"],
                    },
                )
                if "columns" in resource:
                    print("\nCreate Column")
                    columns_ids = m.create_columns(
                        objs=resource["columns"], table_id=table_id
                    )

                    resource_to_cloud_table = {
                        "table": table_id,
                        "gcpProjectId": resource["source_bucket_name"],
                        "gcpDatasetId": resource["dataset_id"],
                        "gcpTableId": resource["table_id"],
                        "columns": columns_ids,
                    }
                    print("\nCreate CloudTable")
                    r, cloud_table_id = m.create_update(
                        mutation_class="CreateUpdateCloudTable",
                        mutation_parameters=resource_to_cloud_table,
                        query_class="allCloudtable",
                        query_parameters={
                            "$gcpDatasetId: String": resource["dataset_id"],
                            "$gcpTableId: String": resource["table_id"],
                        },
                    )

            elif resource_type == "external_link":

                print("\nCreate RawDataSource")
                resource_to_raw_data_source = {
                    "dataset": dataset_id,
                    # "coverages": "",
                    "availability": m.create_availability(resource),
                    # "languages": "",
                    "license": m.create_license(),
                    "updateFrequency": update_frequency_id,
                    "areaIpAddressRequired": m.create_update(
                        query_class="allArea",
                        query_parameters={"$slug: String": "desconhecida"},
                        mutation_class="CreateUpdateArea",
                        mutation_parameters={"slug": "desconhecida"},
                    )[1],
                    # "createdAt": "",
                    # "updatedAt": "",
                    "url": resource["url"],
                    "name": resource["name"],
                    "description": "TO DO"
                    if resource["description"] is None
                    else resource["description"],
                    # "containsStructureData": "",
                    # "containsApi": "",
                    # "isFree": "",
                    # "requiredRegistration": "",
                    # "observationLevel": "",
                }

                r, raw_source_id = m.create_update(
                    mutation_class="CreateUpdateRawDataSource",
                    mutation_parameters=resource_to_raw_data_source,
                    query_class="allRawdatasource",
                    query_parameters={"$url: String": resource["url"]},
                )

                print(r)

            elif resource_type == "information_request":
                print("\nCreate InformationRequest")

                resource_to_information_request = {
                    "dataset": dataset_id,
                    "status": m.create_update(
                        query_class="allStatus",
                        query_parameters={"$slug: String": resource["state"]},
                        mutation_class="CreateUpdateStatus",
                        mutation_parameters={
                            "slug": resource["state"],
                            "name": resource["state"],
                        },
                    )[1],
                    "updateFrequency": update_frequency_id,
                    "origin": resource["origin"],
                    "slug": resource["name"],
                    "url": resource["url"],
                    "startedAt": datetime.strptime(
                        resource["opening_date"], "%d/%m/%Y"
                    ).strftime("%Y-%m-%d")
                    + "T00:00:00",
                    "dataUrl": resource["data_url"],
                    "observations": resource["department"],
                    "startedBy": 1,
                    # "observationLevel": "",
                }
                r, raw_source_id = m.create_update(
                    mutation_class="CreateUpdateInformationRequest",
                    mutation_parameters=resource_to_information_request,
                    query_class="allInformationrequest",
                    query_parameters={"$url: String": resource["url"]},
                )
                print(r)
