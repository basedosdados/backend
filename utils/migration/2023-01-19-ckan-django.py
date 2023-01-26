import requests
import json

j = json.load(open("./credentials.json"))
USERNAME = j["username"]
PASSWORD = j["password"]


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

    def get_organization_id(self, slug):
        query = """
        
        query($slug: String) {
            allOrganization(slug:$slug){
            edges{
                node{
                id,
                }
            }
            }
        }
        """
        variables = {"slug": slug}
        return (
            requests.get(
                url=self.base_url,
                json={"query": query, "variables": variables},
                headers=self.header,
            )
            .json()["data"]["allOrganization"]["edges"][0]["node"]["id"]
            .split(":")[1]
        )

    def get_dataset_id(self, dataset_slug, org_slug):
        query = """
        
        query($slug: String,$organization_Slug:String) {
            allDataset(
                slug:$slug, 
                organization_Slug:$organization_Slug
            ){
            edges{
                node{
                id,
                }
            }
            }
        }
        """
        variables = {"slug": dataset_slug, "organization_Slug": org_slug}
        return (
            requests.get(
                url=self.base_url,
                json={"query": query, "variables": variables},
                headers=self.header,
            )
            .json()["data"]["allDataset"]["edges"][0]["node"]["id"]
            .split(":")[1]
        )

    def create_update_dataset(self, parameters):
        query = """
            mutation($input:CreateUpdateDatasetInput!){
                CreateUpdateDataset(input: $input){
                errors {
                    field,
                    messages
                },
                clientMutationId,
                dataset {
                    id,
                    slug,
                    nameEn,
                    namePt,
                }
            }
            }
        """

        return requests.post(
            self.base_url,
            json={"query": query, "variables": {"input": parameters}},
            headers=self.header,
        ).json()


if __name__ == "__main__":
    TOKEN = get_token(USERNAME, PASSWORD)
    packages = get_bd_packages()
    p = get_package_model()
    m = Migration(TOKEN)
    for dataset in [p]:
        print("CreateDataset")

        package_to_dataset = {
            "organization": m.get_organization_id("basedosdados"),
            "id": m.get_dataset_id(dataset["name"], "basedosdados"),
            "slug": dataset["name"],
            "nameEn": "teste2",
            "namePt": dataset["title"],
        }
        r = m.create_update_dataset(package_to_dataset)

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
