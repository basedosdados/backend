# -*- coding: utf-8 -*-
from csv import DictReader
from os import getenv
from random import choice
from string import ascii_letters, digits, punctuation

from scripts.utils import gql

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


mutation = """
mutation UpdateAccount($input: CreateUpdateAccountInput!) {
  CreateUpdateAccount(input: $input) {
    account {
      uuid
      email
      username
      password
      fullName
      lastName
      firstName
      isActive
    }
  }
}
"""


def read(filepath: str):
    with open(filepath, "r") as file:
        reader = DictReader(file)
        data = [r for r in reader]
    return data


def split(s):
    parts = s.split(" ", 1)
    if len(parts) == 1:
        parts.append("")
    return parts


def make_password():
    characters = ascii_letters + digits + punctuation
    password = "".join(choice(characters) for _ in range(16))
    return password


def get_emails(url: str, key: str):
    count = 1
    offset = 0
    emails = []
    while count > 0:
        variables = {"offset": offset}
        response = gql(url=url, query=query, variables=variables)
        response = response.json()
        users = response["data"]["allAccount"]["edges"]
        count = response["data"]["allAccount"]["edgeCount"]
        emails.extend([u["node"]["email"] for u in users])
        offset += 1500
    return emails


def create_users(url: str, key: str, filepath: str):
    current_emails = get_emails(url, key)

    for datum in read(filepath):
        uuid = datum["id"]
        email = datum["email"]
        username = datum["name"]
        password = make_password()
        full_name = datum["fullname"]
        first_name, last_name = split(full_name)
        is_active = datum["state"] == "active"

        if email in current_emails:
            print(f"SKIP: {email}")
            continue

        variables = {
            "uuid": uuid,
            "email": email,
            "username": username,
            "password": password,
            "fullName": full_name,
            "lastName": last_name,
            "firstName": first_name,
            "isActive": is_active,
        }
        variables = {"input": variables}
        response = gql(url, key, mutation, variables)
        if "errors" in response.text:
            print(f"ERRR: ({response.text})")
        print(f"OKAY: {email}")


def run():
    """
    Steps to execute:
    - Set the environment variables
    - Run the script
    Observations:
    - There are 5 duplicated emails
    """
    GRAPHQL_URL = getenv("GRAPHQL_URL")
    GRAPHQL_KEY = getenv("GRAPHQL_KEY")
    SRC_FILEPATH = getenv("SRC_FILEPATH")
    create_users(
        GRAPHQL_URL,
        GRAPHQL_KEY,
        SRC_FILEPATH,
    )


if __name__ == "__main__":
    run()
