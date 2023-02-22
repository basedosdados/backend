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
                print(f"not found {query_class}", dict(zip(keys, values)))
            else:
                id = r["data"][query_class]["edges"][0]["node"]["id"]
                print(f"found {id}")
                id = id.split(":")[1]
            return r, id
        else:
            print("Error:", json.dumps(r, indent=4))
            raise Exception("Error")

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
                    print(f"not found {mutation_class}", mutation_parameters)
                    id = None
                else:
                    id = r["data"][mutation_class][_classe]["id"]
                    print(f"created {id}")
                    id = id.split(":")[1]
                return r, id
            else:
                print("\n", "query\n", query, "\n")
                print("input\n", json.dumps(mutation_parameters, indent=4), "\n")
                print("error\n", json.dumps(r, indent=4), "\n")
                raise Exception("Error")
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

    def create_entity(self):
        r, id = self.create_update(
            mutation_class="CreateUpdateEntity",
            mutation_parameters={
                "slug": "desconhecida",
                "name": "todo",
            },
            query_class="allEntity",
            query_parameters={"$slug: String": "desconhecida"},
        )

        return id

    def create_update_frequency(self, entity_id):
        r, id = self.create_update(
            mutation_class="CreateUpdateUpdateFrequency",
            mutation_parameters={
                "entity": entity_id,
                "number": 0,
            },
            query_class="allUpdatefrequency",
            query_parameters={"$number: Int": 0},
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
    update_frequency_id = m.create_update_frequency(entity_id)
    # r = m.delete(classe="Dataset", id="77239376-6662-4d64-8950-2f57f1225e53")

    for p in [package]:
        #     # create tags
        #     tags_ids = m.create_tags(objs=p.get("tags"))
        #     themes_ids = m.create_themes(objs=p.get("groups"))

        #     ## create organization
        #     org_slug = p.get("organization").get("name").replace("-", "_")
        #     package_to_org = {
        #         "area": m.create_update(
        #             query_class="allArea",
        #             query_parameters={"$slug: String": "desconhecida"},
        #             mutation_class="CreateUpdateArea",
        #             mutation_parameters={"slug": "desconhecida"},
        #         )[1],
        #         "slug": org_slug,
        #         "name": p.get("organization").get("title"),
        #         "description": p.get("organization").get("description"),
        #     }
        #     r, org_id = m.create_update(
        #         query_class="allOrganization",
        #         query_parameters={"$slug: String": org_slug},
        #         mutation_class="CreateUpdateOrganization",
        #         mutation_parameters=package_to_org,
        #     )

        #     ## create dataset
        #     package_to_dataset = {
        #         "organization": org_id,
        #         "slug": p["name"].replace("-", "_"),
        #         "name": p["title"],
        #         "description": p["notes"],
        #         "tags": tags_ids,
        #         "themes": themes_ids,
        #     }
        #     r, dataset_id = m.create_update(
        #         query_class="allDataset",
        #         query_parameters={"$slug: String": p["name"].replace("-", "_")},
        #         mutation_class="CreateUpdateDataset",
        #         mutation_parameters=package_to_dataset,
        #     )
        #     print(dataset_id)
        dataset_id = "da237d91-b2a4-4193-ae96-395f8bcdd004"
        for resource in p["resources"]:
            resource_type = resource["resource_type"]

            if resource_type == "bdm_table":
                print("  CreateTable | CreateCloudTable")

                resource_to_table = {
                    "dataset": dataset_id,
                }

                r, raw_source_id = m.create_update(
                    mutation_class="CreateUpdateTable",
                    mutation_parameters=resource_to_table,
                    query_class="allTable",
                    query_parameters={"$slug: String": resource["table_id"]},
                )
                if "columns" in resource:
                    print("    CreateColumn")

            elif resource_type == "external_link":

                print("  CreateRawDataSource")
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
                print("  CreateInformationRequest")

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
