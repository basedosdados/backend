import requests
import json

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


class Migration:
    def __init__(self, token):
        self.base_url = "https://staging.backend.dados.rio/api/v1/graphql"
        self.header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def create_update(self, classe, parameters):
        query = f"""
            mutation($input:{classe}Input!){{
                {classe}(input: $input){{
                errors {{
                    field,
                    messages
                }},
                clientMutationId,
                dataset {{
                    id,
                    slug,
                }}
            }}
            }}
        """

        return requests.post(
            self.base_url,
            json={"query": query, "variables": {"input": parameters}},
            headers=self.header,
        ).json()

    def get_id(self, classe, parameters):
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

        return (
            requests.get(
                url=self.base_url,
                json={"query": query, "variables": dict(zip(keys, values))},
                headers=self.header,
            )
            .json()["data"][classe]["edges"][0]["node"]["id"]
            .split(":")[1]
        )


if __name__ == "__main__":
    # TOKEN = get_token(USERNAME, PASSWORD)
    # packages = get_bd_packages()
    p = get_package_model()
    m = Migration(TOKEN)
    for dataset in [p]:
        print("CreateDataset")

        package_to_dataset = {
            "organization": m.get_id(
                classe="allOrganization", parameters={"$slug: String": "basedosdados"}
            ),
            "id": m.get_id(
                classe="allDataset",
                parameters={
                    "$slug: String": dataset["name"],
                    "$organization_Slug: String": "basedosdados",
                },
            ),
            "slug": dataset["name"],
            "nameEn": "teste3",
            "namePt": dataset["title"],
        }
        r = m.create_update(classe="CreateUpdateDataset", parameters=package_to_dataset)

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
