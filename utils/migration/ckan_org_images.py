from datetime import datetime

import requests
from pathlib import Path

CKAN_ALL_ORGS_URL = "https://basedosdados.org/api/3/action/organization_list"
CKAN_ORG_URL = "https://basedosdados.org/api/3/action/organization_show?id={org_id}"
CKAN_IMG_URL = "https://basedosdados.org/uploads/group/{img_name}"
IMG_PATH = Path(__file__).parent / "images"
LOG_PATH = Path(__file__).parent / "logs"


class OrganizationError(Exception):
    """Organization error"""

    pass


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
    if org_name.startswith("br-"):
        org_name = org_name.replace("br-", "")
    if org_name.startswith("world-"):
        org_name = org_name.replace("world-", "")
    org_name = org_name.replace("-", "_")
    return org_name, org_image


def get_ckan_orgs() -> list:
    """Get all CKAN organizations"""
    r = requests.get(CKAN_ALL_ORGS_URL, timeout=90)
    return r.json()["result"]


def rename_image(slug: str, image: str) -> Path:
    """Rename image to match new slug"""
    if image is None:
        return None
    else:
        print("Downloading image from org:", slug)
        ext = image.split(".")[-1]
        if ext not in ["png", "jpg", "jpeg"]:
            ext = "jpg"
        # salvar a imagem com o novo nome
        r = requests.get(CKAN_IMG_URL.format(img_name=image), timeout=90)
        new_image = f"{slug}.{ext}"
        if (IMG_PATH / new_image).exists():
            print("Image already exists:", new_image)
        else:
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
                    }}
                }}
            }}
        }}
    """
    try:
        r = requests.post("https://staging.api.basedosdados.org/api/v1/graphql", json={"query": query})
        r.raise_for_status()
        uuid = r.json()["data"]["allOrganization"]["edges"][0]["node"]["_id"]
        return uuid, rename_image(slug, image)
    except IndexError as e:
        return None, None


def upload_image(uuid, image):
    pass


def main():
    if not LOG_PATH.exists():
        LOG_PATH.mkdir()

    if (LOG_PATH / "orgs.csv").exists():
        print("Uploading organization images")
        with open(LOG_PATH / "orgs.csv", "r") as f:
            for line in f:
                uuid, slug, image = line.split(",")
                uploaded = upload_image(uuid, image)
    else:
        print("Downloading CKAN organization images")
        errors = []
        all_orgs = get_ckan_orgs()  # lists current slugs of all orgs
        # orgs_data = [get_org_data(org) for org in all_orgs]

        if (LOG_PATH / "errors.txt").exists():
            (LOG_PATH / "errors.txt").unlink()

        found = []
        with open(LOG_PATH / "orgs.csv", "w") as f:
            f.write("uuid,slug,image\n")

        for slug in all_orgs:
            org_data = get_org_data(slug)
            uuid, image = get_org_uuid(org_data)
            if uuid is None:
                print("Não encontrado:", slug)
                errors.append(slug)
                with open(LOG_PATH / "errors.txt", "a") as f:
                    f.write(f"{slug}\n")
            else:
                found.append(slug)
                updated = upload_image(uuid, image)
                with open(LOG_PATH / "orgs.csv", "a") as f:
                    f.write(f"{uuid},{slug},{image}\n")

        print("Encontrados: ", len(found))
        print("Não encontrados: ", len(errors))


if __name__ == "__main__":
    main()
