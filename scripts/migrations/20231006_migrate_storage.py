# -*- coding: utf-8 -*-
from os import getenv
from pathlib import Path
from re import findall

import requests
from google.cloud import storage

bucket_name = getenv("BUCKET_NAME")
source_path = Path(getenv("SOURCE_PATH", "."))

url_prefix = "https://basedosdados-static.s3.us-east-2.amazonaws.com/"
url_prefix_exp = r'(https:\/\/basedosdados-static\.s3\.us-east-2\.amazonaws\.com\/[^\\" ]*)'

icon_url = (
    "https://basedosdados-static.s3.us-east-2.amazonaws.com/category_icons/2022/icone_${icon}.svg"
)
icon_themes = [
    "agropecuaria",
    "ciencia-tec-inov",
    "comunicacao",
    "cultura-arte",
    "diversidade",
    "economia",
    "educacao",
    "energia",
    "esportes",
    "gov-fin-pub",
    "historia",
    "infra-transp",
    "justica",
    "meio-ambiente",
    "politica",
    "populacao",
    "religiao",
    "saude",
    "seguranca",
    "territorio",
    "turismo",
    "urbanizacao",
]


def run():
    """
    Steps to execute:
    - Set the environment variables
    - Run the script
    """

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    def download_and_upload(url, urlpath: Path, filepath: Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        if not filepath.exists():
            response = requests.get(url)
            if response.status_code == 200:
                with filepath.open("wb") as f:
                    f.write(response.content)
        if not bucket.blob(urlpath).exists():
            blob = bucket.blob(urlpath)
            blob.upload_from_filename(filepath)

    for path in source_path.glob("**/*.html"):
        for url in findall(url_prefix_exp, path.read_text()):
            urlpath = url.replace(url_prefix, "").lower()
            filepath = Path(".").resolve() / ".blobs" / urlpath
            download_and_upload(url, urlpath, filepath)

    for icon_theme in icon_themes:
        url = icon_url.replace("${icon}", icon_theme)
        urlpath = url.replace(url_prefix, "").lower()
        filepath = Path(".").resolve() / ".blobs" / urlpath
        download_and_upload(url, urlpath, filepath)


if __name__ == "__main__":
    run()
