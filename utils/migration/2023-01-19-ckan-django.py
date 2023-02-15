import requests
import json
import re

j = json.load(open("./credentials.json"))
USERNAME = j["username"]
PASSWORD = j["password"]
TOKEN = j["token"]


def get_token(username, password):
    r = requests.post(
        "https://staging.backend.dados.rio/api/v1/graphql",
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


def create_tags(m, ckan_tags):  # sourcery skip: instance-method-first-arg-name
    tags_ids = []
    if ckan_tags != []:
        for tag in ckan_tags:
            tag_id = m.get_id(
                classe="CreateUpdateTag",
                parameters={"$slug: String": tag.get("name")},
            )
            if tag_id is None:
                r, created_tag_id = m.create_update(
                    classe="CreateUpdateTag",
                    parameters={
                        "slug": tag.get("name"),
                        "name": tag.get("display_name"),
                    },
                )
                if created_tag_id is None:
                    print(r)
                else:
                    tags_ids.append(created_tag_id)
            else:
                tags_ids.append(tag_id)
    return tags_ids


def create_themes(m, ckan):
    ids = []
    if ckan != []:
        for obj in ckan:
            obj_id = m.get_id(
                classe="allTheme",
                parameters={"$slug: String": obj.get("name")},
            )
            if obj_id is None:
                r, created_id = m.create_update(
                    classe="CreateUpdateTheme",
                    parameters={
                        "slug": obj.get("name"),
                        "name": obj.get("title"),
                        "logoUrl": obj.get("image_display_url"),
                    },
                )
                if created_id is None:
                    print(r)
                else:
                    ids.append(created_id)
            else:
                ids.append(obj_id)
    return ids


class Migration:
    def __init__(self, token):
        self.base_url = "https://staging.backend.dados.rio/api/v1/graphql"
        self.header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def create_update(self, classe, parameters):
        # sourcery skip: avoid-builtin-shadow

        _classe = re.findall("[A-Z][^A-Z]*", classe)[-1].lower()
        query = f"""
            mutation($input:{classe}Input!){{
                {classe}(input: $input){{
                errors {{
                    field,
                    messages
                }},
                clientMutationId,
                {_classe} {{
                    id,
                    slug,
                }}
            }}
            }}
        """
        r = requests.post(
            self.base_url,
            json={"query": query, "variables": {"input": parameters}},
            headers=self.header,
        ).json()

        if r["data"][classe]["errors"] != []:
            print(f"not found {classe}", parameters)
            id = None
        else:
            id = r["data"][classe][_classe]["id"]
            print(f"created {id}")
            id = id.split(":")[1]

        return r, id

    def get_id(self, classe, parameters):  # sourcery skip: avoid-builtin-shadow
        _filter = ", ".join(list(parameters.keys()))
        keys = [
            parameter.replace("$", "").split(":")[0]
            for parameter in list(parameters.keys())
        ]
        values = list(parameters.values())
        _input = ", ".join([f"{key}:${key}" for key in keys])

        query = f"""
            query({_filter}) {{
                {classe}({_input}){{
                edges{{
                    node{{
                    slug,
                    id,
                    }}
                }}
                }}
            }}
        """

        response = requests.get(
            url=self.base_url,
            json={"query": query, "variables": dict(zip(keys, values))},
            headers=self.header,
        ).json()["data"][classe]["edges"]

        if response == []:
            id = None
            print(f"not found {classe}", dict(zip(keys, values)))
        else:
            id = response[0]["node"]["id"]
            print(f"found {id}")
            id = id.split(":")[1]

        return id

    def delete(self, classe, id):
        query = f"""
            mutation {{
                Delete{classe}(id: "{id}") {{
                    ok,
                    errors
            }}
        """
        r = requests.post(
            self.base_url,
            json={"query": query},
            headers=self.header,
        ).json()
        
        return r


if __name__ == "__main__":
    TOKEN = get_token(USERNAME, PASSWORD)
    # packages = get_bd_packages()
    package = get_package_model()
    m = Migration(TOKEN)
    r = m.delete(classe="Dataset", id="77239376-6662-4d64-8950-2f57f1225e53")
    print(r)
    # for p in [package]:
    #     ## create tags
    #     tags_ids = create_tags(m, p.get("tags"))
    #     themes_ids = create_themes(m, p.get("groups"))

    #     # ## check if organization exists
    #     org_slug = p.get("organization").get("name").replace("-", "_")
    #     org_id = m.get_id(
    #         classe="allOrganization",
    #         parameters={"$slug: String": org_slug},
    #     )
    #     if org_id is None:
    #         package_to_org = {
    #             "area": m.get_id(
    #                 classe="allArea", parameters={"$slug: String": "Desconhecida"}
    #             ),
    #             "slug": org_slug,
    #             "name": p.get("organization").get("title"),
    #             "description": p.get("organization").get("description"),
    #         }
    #         r, created_org_id = m.create_update(
    #             classe="CreateUpdateOrganization", parameters=package_to_org
    #         )

    #     dataset_id = m.get_id(
    #         classe="allDataset", parameters={"$slug: String": p["name"]}
    #     )

    #     if dataset_id is None:
    #         package_to_dataset = {
    #             "organization": org_id if org_id is not None else created_org_id,
    #             "slug": p["name"].replace("-", "_"),
    #             "name": p["title"],
    #             "description": p["notes"],
    #             "tags": tags_ids,
    #             "themes": themes_ids,
    #         }

    #         r, dataset_id = m.create_update(
    #             classe="CreateUpdateDataset", parameters=package_to_dataset
    #         )

    #     print(dataset_id)
    # for resource in dataset['resources']:
    #     resource_type = resource['resource_type']
    #     if resource_type == 'bdm_table':
    #         print('  CreateTable | CreateCloudTable')
    #         if 'columns' in resource:
    #             print('    CreateColumn')
    #     if resource_type == 'external_link':
    #         print('  CreateRawDataSource')
    #     if resource_type == 'information_request':
    #         print('  CreateInformationRequest')
