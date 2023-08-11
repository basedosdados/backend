from pathlib import Path
from requests import post


token = """
mutation {
  tokenAuth(email: "email", password: "password") {
    token
    payload
    refreshExpiresIn
  }
}
"""


def gql(url: str, key: str = None, query: str | Path = None, variables: dict = None):
    """GraphQL request helper function"""

    if type(query) == Path:
        query = query.read_text()
    headers = {
        "Content-Type": "application/json",
    }
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = {
        "query": query,
    }
    if variables:
        body["variables"] = variables
    response = post(
        url,
        json=body,
        headers=headers,
    )
    return response
