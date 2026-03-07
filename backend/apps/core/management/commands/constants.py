# -*- coding: utf-8 -*-
from enum import Enum
from pathlib import Path


class LocalPolulate(Enum):
    FOLDER = "backups"
    FILE_NAME = "backup_prod_v1.xml"
    URL_JSON = "https://storage.googleapis.com/basedosdados-website/dados/backup_prod_v1.xml"
    PATH_FILE = Path(FOLDER) / FILE_NAME
