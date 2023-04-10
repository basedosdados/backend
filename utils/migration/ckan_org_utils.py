from datetime import datetime
import cairosvg

import requests
import json


def get_credentials(mode="local") -> tuple:
    with open("./credentials.json", "r") as f:
        j = json.load(f)

    return j[mode]["url"], j[mode]["email"], j[mode]["password"]


def get_token(url, email, password):
    query = """
        mutation tokenAuth($email: String!, $password: String!) {
            tokenAuth(email: $email, password: $password) {
                payload,
                refreshExpiresIn,
                token
            }
        }
        """
    variables = {"email": email, "password": password}
    r = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json={
            "query": query,
            "variables": variables,
        },
    )
    r.raise_for_status()
    return r.json()["data"]["tokenAuth"]["token"]


def refresh_token(token, mode="local") -> dict:
    """
    If token is expired, refresh it
    """
    url, email, password = get_credentials(mode)
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
        return get_token(*get_credentials(mode))
    return r.json()["data"]["refreshToken"]["token"]


def verify_token(token, mode="local") -> bool:
    """Verify if token is valid using unix timestamp"""
    url, username, password = get_credentials(mode)
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

    if token and verify_token(token, mode):
        return token
    elif token:
        token = refresh_token(token, mode)
    else:
        token = get_token(*get_credentials(mode))
        print("New token: ", token)
        with open("./credentials.json", "r") as f:
            credentials = json.load(f)

        with open("./credentials.json", "w") as f:
            credentials[mode]["token"] = token
            json.dump(credentials, f)

    return token


def get_url(mode="local"):
    with open("./credentials.json", "r") as f:
        url = json.load(f)[mode]["url"]

    return url


def convert_svg_to_png(svg_file, png_file):
    print(f"Converting {svg_file} to {png_file}")
    with open(svg_file, "rb") as f:
        svg_file = f.read()
    cairosvg.svg2png(bytestring=svg_file, write_to=png_file)
    return png_file
