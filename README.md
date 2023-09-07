# Base dos Dados API

## Configuração de ambiente para desenvolvimento

### Requisitos

- Um editor de texto (recomendado VS Code)
- Python 3.10
- `pip`
- (Opcional, mas recomendado) Um ambiente virtual para desenvolvimento (`miniconda`, `virtualenv` ou similares)

### Procedimentos

- Clonar esse repositório

  ```
  git clone https://github.com/basedosdados/backend.git
  ```

- Abrí-lo no seu editor de texto

- No seu ambiente de desenvolvimento, instalar [poetry](https://python-poetry.org/) para gerenciamento de dependências

    ```
    pip3 install poetry
    ```

- Instalar as dependências para desenvolvimento

    ```
    poetry install
    ```

- Instalar os hooks de pré-commit (ver https://pre-commit.com/ para entendimento dos hooks)

    ```
    pre-commit install
    ```

- Pronto! Seu ambiente está configurado para desenvolvimento.

* OBS.: É possível realizar a execução do servidor django um dos alias
```sh
    make run_local
    make run_docker
```

* OBS2: É possível realizar a execução do servidor django via
```sh
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py runserver 8080
```

* OBS3: É possível realizar a load e dump de fixtures via
```sh
    python manage.py dumpdata > data.json
    python manage.py loadfixture data.json
```
