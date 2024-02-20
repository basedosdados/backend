# -*- coding: utf-8 -*-
from os.path import join
from typing import Any

from django.core.files.storage import get_storage_class
from django.core.validators import FileExtensionValidator


def upload_to(instance: Any, filename: str):
    """Get upload path as model primary key with extension"""
    extension = filename.split(".")[-1]
    folder = instance.__class__.__name__.lower()
    return join(folder, f"{instance.pk}.{extension}")


def validate_image(file):
    """Validate if image format is allowed"""
    FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])(file)


class OverwriteStorage(get_storage_class()):
    def _save(self, name, content):
        self.delete(name)
        return super(OverwriteStorage, self)._save(name, content)

    def get_available_name(self, name, max_length=None):
        return name
