from csv import DictReader
from os import getenv

from utils.graphql import gql


query = """
query ($offset: Int!) {
  allAccount(offset: $offset) {
    edges {
      node {
        id
        email
        description
        firstName
        lastName
        fullName
      }
    }
    edgeCount
  }
}
"""


mutation_account = """
mutation UpdateAccount($input: CreateUpdateAccountInput!) {
  CreateUpdateAccount(input: $input) {
    account {
      id
      description
      twitter
      github
      website
      linkedin
      picture
    }
  }
}
"""


mutation_career = """
mutation CreateCareer($input: CreateUpdateCareerInput!) {
  CreateUpdateCareer(input: $input) {
    career {
      account {
        email
      }
      team
      role
      level
      endAt
      startAt
    }
  }
}
"""


def read(filepath: str):
    with open(filepath, "r") as file:
        reader = DictReader(file)
        data = [r for r in reader]
    return data


def parse(id_: str = ""):
    if type(id_) == str:
        id_ = id_.replace("AccountNode:", "")
        id_ = id_ or "0"
    return id_ or "0"


def get_emails(url: str, key: str):
    count = 1
    offset = 0
    emails = {}
    while count > 0:
      variables = {"offset": offset}
      response = gql(url=url, query=query, variables=variables)
      response = response.json()
      users = response["data"]["allAccount"]["edges"]
      count = response["data"]["allAccount"]["edgeCount"]
      emails.update({u["node"]["email"]: parse(u["node"]["id"]) for u in users})
      offset += 1500
    return emails


def create_careers(url: str, key: str, users_filepath: str, teams_filepath: str):
    users = read(users_filepath)
    teams = read(teams_filepath)
    emails_to_ids = get_emails(url, key)

    for user in users:
        id_ = emails_to_ids.get(user["email"])
        id_ = parse(id_)
        description = user["descricao"]
        github = user["github"]
        twitter = user["twitter"]
        linkedin = user["linkedin"]
        website = user["website"]

        if id_ == "0":
            continue

        variables = {
            "id": id_,
            "description": description,
            "github": github,
            "twitter": twitter,
            "linkedin": linkedin,
            "website": website,
        }
        variables = {"input": variables}
        response = gql(url, key, mutation_account, variables)
        if "errors" in response.text:
            print(f"ACCOUNT:\n\t{response.text}\n\t{variables}")

        for team in teams:
            if (
                True
                and user["id"]
                and team["id_pessoa"]
                and int(user["id"]) == int(float(team["id_pessoa"]))
            ):
                role = team["cargo"]
                team_ = team["equipe"]
                level = team["nivel"]
                end_at = team["data_fim"]
                start_at = team["data_inicio"]

                variables = {
                    "account": id_,
                    "role": role,
                    "team": team_,
                    "level": level,
                    "endAt": end_at,
                    "startAt": start_at,
                }
                if not end_at:
                    variables.pop("endAt")
                if not start_at:
                    variables.pop("startAt")
                variables = {"input": variables}
                response = gql(url, key, mutation_career, variables)
                if "errors" in response.text:
                    print(f"CAREERS:\n\t{response.text}\n\t{variables}")


def run():
    """
    Steps to execute:
    - Set the environment variables
    - Run the script
    """
    GRAPHQL_URL = getenv("GRAPHQL_URL")
    GRAPHQL_KEY = getenv("GRAPHQL_KEY")
    USERS_SRC_FILEPATH = getenv("USERS_SRC_FILEPATH")
    TEAMS_SRC_FILEPATH = getenv("TEAMS_SRC_FILEPATH")
    create_careers(
        GRAPHQL_URL,
        GRAPHQL_KEY,
        USERS_SRC_FILEPATH,
        TEAMS_SRC_FILEPATH,
    )


if __name__ == "__main__":
    run()
