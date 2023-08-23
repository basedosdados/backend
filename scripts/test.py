# -*- coding: utf-8 -*-
from subprocess import run as _run

def run(*args):
    process = _run(*args)
    return process.returncode
    

def main():
    """Test all python files in the project"""
    code = run(["pytest", "."])
    exit(code)
