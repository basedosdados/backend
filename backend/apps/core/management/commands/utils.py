# -*- coding: utf-8 -*-
import json
from pathlib import Path

import requests


def download_backup(url_arquivo: str, caminho_salvar: str) -> None:
    """
    Baixa um arquivo JSON grande usando chunks para economia de memória.

    Args:
        url_arquivo: URL do arquivo JSON
        caminho_salvar: Caminho onde salvar o arquivo
    """
    # Configurações para controle de memória
    tamanho_chunk = 1024 * 1024  # 1MB por chunk

    try:
        resposta = requests.get(url_arquivo, stream=True)

        tamanho_total = int(resposta.headers.get("content-length", 0))

        caminho_arquivo = Path(caminho_salvar)
        caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)

        with open(caminho_salvar, "wb") as arquivo:
            bytes_baixados = 0

            for chunk in resposta.iter_content(chunk_size=tamanho_chunk):
                if chunk:
                    arquivo.write(chunk)
                    bytes_baixados += len(chunk)

                    print(
                        f"\rBaixando: {bytes_baixados/tamanho_total*100:.2f}%", end="", flush=True
                    )

        print("\n\nDownload concluído!")

    except Exception as e:
        print(f"Erro ao baixar o arquivo: {str(e)}")


def remove_connection_accounts(path: str) -> None:
    """
    Remove qualquer conexão com que o JSON gerado do APP v1 tenha com account

    Args:
        path: Caminho para o path JSON
    """

    try:
        # Ler o path
        with open(path, "r", encoding="utf-8") as json_file:
            dados = json.load(json_file)

        # Processar cada registro
        for registro in dados:
            if registro.get("model") == "v1.table":
                registro.setdefault("fields", {}).update(
                    {"published_by": [], "data_cleaned_by": []}
                )
            elif registro.get("model") == "v1.informationrequest":
                registro.setdefault("fields", {})["started_by"] = None

        # Salvar alterações
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

    except FileNotFoundError:
        print(f"Erro: path '{path}' não encontrado")
    except json.JSONDecodeError:
        print(f"Erro: path '{path}' contém JSON inválido")
    except Exception as e:
        print(f"Erro inesperado ao processar '{path}': {str(e)}")
