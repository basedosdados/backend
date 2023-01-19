import requests
import json

j = json.load(open("./credentials.json"))
USERNAME = j["username"]
PASSWORD = j["password"]


def get_token():
    r = requests.post(
        "https://staging.backend.dados.rio/api/token/",
        json={"username": USERNAME, "password": PASSWORD},
        headers={"Content-Type": "application/json"},
    )
    r.raise_for_status()
    return r.json()["access"]


def get_bd_packages():
    url = "https://basedosdados.org"
    api_url = f"{url}/api/3/action/package_search?q=&rows=2000"
    packages = requests.get(api_url, verify=False).json()["result"]["results"]
    return packages


class Migration:
    def __init__(self):
        self.base_url = "https://staging.backend.dados.rio/api/v1/private/"
        self.token = get_token()

    def get(self, endpoint):
        r = requests.get(
            url=self.base_url + endpoint,
            headers={"Authorization": f"Bearer {self.token}"},
        )
        return r.json()["results"]

    def post(self, endpoint, parameters):
        r = requests.post(
            url=self.base_url + endpoint,
            headers={"Authorization": f"Bearer {self.token}"},
            json=parameters,
        )
        if r.status_code == 400:
            print(r.content)
        r.raise_for_status()
        return r.json()

    def put(self, endpoint, parameters):
        r = requests.put(
            url=self.base_url + endpoint,
            headers={"Authorization": f"Bearer {self.token}"},
            json=parameters,
        )
        if r.status_code == 400:
            print(r.content)
        r.raise_for_status()
        return r.json()


if __name__ == "__main__":

    packages = get_bd_packages()
    print(packages[0])

    # m = Migration()
    # orgs = m.get("organizations/")
    # for org in orgs:
    #     dataset = org["datasets"][0]
    #     print(dataset)
    #     dataset["slug"] = "teste"

    #     print(dataset)
    # id = dataset["id"]
    # r = m.put(f"datasets/{id}", dataset)
    # print(r)
