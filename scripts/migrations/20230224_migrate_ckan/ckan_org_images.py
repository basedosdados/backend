# -*- coding: utf-8 -*-

import json
from pathlib import Path
from typing import Union

import requests
import urllib3
from ckan_org_utils import convert_svg_to_png, get_url, load_token

CKAN_ALL_ORGS_URL = "https://basedosdados.org/api/3/action/organization_list"
CKAN_ORG_URL = "https://basedosdados.org/api/3/action/organization_show?id={org_id}"
CKAN_IMG_URL = "https://basedosdados.org/uploads/group/{img_name}"
IMG_PATH = Path(__file__).parent / "images"
LOG_PATH = Path(__file__).parent / "logs"


class OrganizationError(Exception):
    """Organization error"""


def get_org_data(org_id: str) -> tuple:
    """
    Get organization name and image from CKAN API
    Args:
        org_id (str): organization ID
    Returns:
        tuple: organization name and image
    Raises:

    """
    print("Getting org data:", org_id)
    org_url = CKAN_ORG_URL.format(org_id=org_id)
    r = requests.get(org_url, timeout=90)
    org_data = r.json()["result"]
    org_image = org_data.get("image_url")
    org_name = org_data.get("name")
    prefix = org_name.split("-")[0] + "-"
    prefixes_to_remove = [
        "al-",
        "br-",
        "brasil-",
        "ca-",
        "ch-",
        "de-",
        "es-",
        "eu-",
        "hm-",
        "mundo-",
        "nl-",
        "se-",
        "tv-",
        "uk-",
        "us-",
        "world-",
    ]
    if org_name.startswith(prefix) and prefix in prefixes_to_remove:
        org_name = org_name.replace(prefix, "")
    org_name = org_name.replace("-", "_")
    return org_name, org_image


def get_ckan_orgs() -> list:
    """Get all CKAN organizations"""
    r = requests.get(CKAN_ALL_ORGS_URL, timeout=90)
    return r.json()["result"]


def rename_image(slug: str, image: str) -> Union[Path, str]:
    """Rename image to match new slug"""
    if image is None:
        return None
    else:
        print("Downloading image from org:", slug)
        ext = image.split(".")[-1]
        if ext not in ["png", "jpg", "jpeg", "gif", "svg"]:
            return "Invalid format"
        # salvar a imagem com o novo nome
        new_image = f"{slug}.{ext}"
        if (IMG_PATH / new_image).exists():
            print("Image already exists:", new_image)
        else:
            r = requests.get(CKAN_IMG_URL.format(img_name=image), timeout=90)
            with open(IMG_PATH / new_image, "wb") as f:
                f.write(r.content)
            print("Saved image:", new_image)
        return IMG_PATH / new_image


def get_org_uuid(org: tuple) -> tuple:
    """Get organization UUID from API"""
    slug = org[0]
    image = org[1]
    query = f"""
        query {{
            allOrganization(slug: "{slug}") {{
                edges{{
                    node{{
                        _id
                        slug
                        hasPicture
                    }}
                }}
            }}
        }}
    """
    try:
        r = requests.post(
            "https://staging.api.basedosdados.org/api/v1/graphql", json={"query": query}
        )
        r.raise_for_status()
        uuid = r.json()["data"]["allOrganization"]["edges"][0]["node"]["_id"]
        has_image = r.json()["data"]["allOrganization"]["edges"][0]["node"]["hasPicture"]
        return uuid, rename_image(slug, image), has_image
    except IndexError as e:  # noqa
        return None, None, None


def upload_image(uuid, image, slug, mode="local"):
    token = load_token(mode=mode)
    url = get_url(mode=mode)
    picture_fname = image.strip("\n")

    query = f"""
        mutation ($picture: Upload){{
            CreateUpdateOrganization(input: {{id: "{uuid}", picture: $picture}}) {{
                errors {{
                    field
                    messages
                }}
                organization {{
                    id
                    picture
                }}
            }}
        }}
    """
    variables = {"picture": None}
    with open(picture_fname, "rb") as f:
        picture = f.read()

    files = [
        ("operations", (None, json.dumps({"query": query, "variables": variables}))),
        ("map", (None, json.dumps({"0": ["variables.picture"]}))),
        ("0", (picture_fname, picture, "image/*")),
    ]

    boundary = "-----011000010111000001101001"
    body, content_type = urllib3.encode_multipart_formdata(files, boundary=boundary)

    headers = {
        "Content-Type": content_type,
        "Authorization": "Bearer " + token,
    }

    try:
        response = requests.post(url, data=body, headers=headers)
        err = response.json().get("data", {}).get("CreateUpdateOrganization", {}).get("errors")
        print(response.text)
        print(uuid, image, url)

        if not err:
            return True, f"{uuid}, {slug}, OK"
        else:
            return False, f"{uuid}, {slug}, {err}"
    except Exception as e:
        return False, f"{uuid}, {slug}, {e}"


def main():
    mode = "staging"
    if not LOG_PATH.exists():
        LOG_PATH.mkdir()

    if (LOG_PATH / "orgs.csv").exists():
        print("Uploading organization images")
        with open(LOG_PATH / "orgs.csv", "r") as f:
            if (LOG_PATH / "upload_log.csv").exists():
                (LOG_PATH / "upload_log.csv").unlink()

            for line in f:
                uuid, slug, image, has_picture = line.split(",")
                flist = image.split(".")
                ext = flist.pop()
                if has_picture.strip() == "false":
                    if ext == "svg":
                        filename = ".".join(flist)
                        image = convert_svg_to_png(image, f"{filename}.png")
                    print("Uploading image:", image)
                    try:
                        status, msg = upload_image(uuid, image, slug, mode=mode)
                        with open(LOG_PATH / "upload_log.csv", "a") as f:
                            f.write(f"{msg}\n")
                    except FileNotFoundError as e:
                        print(e)
                        with open(LOG_PATH / "upload_log.csv", "a") as f:
                            f.write(f"{uuid}, {slug}, {e}\n")
    else:
        print("Downloading CKAN organization images")
        errors = []
        all_orgs = get_ckan_orgs()  # lists current slugs of all orgs

        if (LOG_PATH / "errors.txt").exists():
            (LOG_PATH / "errors.txt").unlink()

        found = []

        for slug in all_orgs:
            org_data = get_org_data(slug)
            uuid, image, has_image = get_org_uuid(org_data)
            if uuid is None:
                print("Não encontrado:", slug)
                errors.append(slug)
                with open(LOG_PATH / "errors.txt", "a") as f:
                    f.write(f"{slug}\n")
            else:
                found.append(slug)
                with open(LOG_PATH / "orgs.csv", "a") as f:
                    f.write(f"{uuid},{slug},{image},{has_image}\n")

        print("Encontrados: ", len(found))
        print("Não encontrados: ", len(errors))


if __name__ == "__main__":
    main()