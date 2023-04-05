from datetime import datetime

import requests
import json


def get_credentials(mode):
    j = json.load(open("./credentials.json"))
    return j[mode]["username"], j[mode]["password"], j[mode]["url"]


def get_token(url, username, password):
    r = requests.post(
        url,
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


def refresh_token(token, mode="local") -> dict:
    """
    If token is expired, refresh it
    """
    username, password, url = get_credentials(mode)
    query = '''
        mutation refreshToken($token: String!) {
            refreshToken(token: $token) {
                payload,
                refreshExpiresIn,
                token
            }
        }
    '''
    variables = {"token": token}
    r = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json={"query": query, "variables": variables},
        timeout=90
    )
    r.raise_for_status()
    if "errors" in r.json():
        message = r.json()["errors"][0]["message"]
        raise Exception(
            F"{message}. You must login again. "
        )
    return r.json()["data"]["refreshToken"]["token"]


def verify_token(token, mode="local") -> bool:
    """Verify if token is valid using unix timestamp"""
    username, password, url = get_credentials(mode)
    if token == "":
        return False
    query = '''
        mutation verifyToken($token: String!) {
            verifyToken(token: $token) {
                payload
            }
        }
    '''
    variables = {"token": token}
    r = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json={"query": query, "variables": variables},
        timeout=90
    )

    current_datetime_unix = int(datetime.now().timestamp())
    if "errors" in r.json():
        return False
    if current_datetime_unix > r.json()["data"]["verifyToken"]["payload"]["exp"]:
        return False
    return True


def load_token(mode="local"):
    with open("./credentials.json", "r") as f:
        token = json.load(f)[mode]["token"]

    if verify_token(token, mode):
        return token
    elif token is not None:
        token = refresh_token(token, mode)
    else:
        token = get_token(*get_credentials(mode))
        with open("./credentials.json", "w") as f:
            credentials = json.load(f)
            credentials[mode]["token"] = token
            json.dump(credentials, f)

    return token
