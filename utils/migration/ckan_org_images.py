import requests
from pathlib import Path

CKAN_ALL_ORGS_URL = "https://basedosdados.org/api/3/action/organization_list"
CKAN_ORG_URL = "https://basedosdados.org/api/3/action/organization_show?id={org_id}"
CKAN_IMG_URL = "https://basedosdados.org/uploads/group/{img_name}"
IMG_PATH = Path(__file__).parent / "images"


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
    org_url = CKAN_ORG_URL.format(org_id=org_id)
    r = requests.get(org_url, timeout=90)
    org_data = r.json()["result"]
    org_image = org_data.get("image_url")
    org_name = org_data.get("name")
    if org_name.startswith("br-"):
        org_name = org_name.replace("br-", "")
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
        ext = image.split(".")[-1]
        # salvar a imagem com o novo nome
        r = requests.get(CKAN_IMG_URL.format(img_name=image), timeout=90)
        new_image = f"{slug}.{ext}"
        with open(IMG_PATH / new_image, "wb") as f:
            f.write(r.content)
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
        res = r.json()["data"]["allOrganization"]["edges"][0]["node"]["_id"]
        return res, slug, rename_image(slug, image)
    except IndexError as e:
        return None, slug


def main():
    print("Migrating CKAN organization images")
    errors = []
    all_orgs = get_ckan_orgs()  # lists current slugs of all orgs
    orgs_data = [get_org_data(org) for org in all_orgs[:20]]

    res = []
    for o in orgs_data:
        org_uuid = get_org_uuid(o)
        if org_uuid[0] is None:
            errors.append(org_uuid[1])
        else:
            res.append(org_uuid)

    print("Encontrados: ", len(res))
    for r in res:
        print(r)

    print("Errors:", errors)


if __name__ == "__main__":
    main()
