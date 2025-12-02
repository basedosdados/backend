# -*- coding: utf-8 -*-
from enum import Enum
from pathlib import Path


class LocalPolulate(Enum):
    FOLDER = "backups"
    FILE_NAME = "backup_prod_v1.json"
    URL_JSON = "https://storage.googleapis.com/basedosdados-dev/backend_backup/backup_prod_v1.json"
    PATH_FILE = Path(FOLDER) / FILE_NAME
