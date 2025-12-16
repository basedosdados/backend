ARG PYTHON_VERSION=3.11-slim

FROM python:$PYTHON_VERSION

# Define where Poetry virtual environments will be stored
ARG POETRY_VIRTUALENVS_PATH=/opt/pypoetry/virtualenvs

# Ensure that the python output is sent straight to terminal (e.g. your container log)
# without being first buffered and that you can see the output of your application (e.g. django logs)
# in real time. Equivalent to python -u: https://docs.python.org/3/using/cmdline.html#cmdoption-u
ENV PYTHONUNBUFFERED=1

# Prevent Python from writing .pyc files to disc
# https://docs.python.org/3/using/cmdline.html#envvar-PYTHONDONTWRITEBYTECODE
ENV PYTHONDONTWRITEBYTECODE=1

# Install make, nginx and copy configuration
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl make nginx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm /etc/nginx/sites-enabled/default
RUN apt-get update && apt-get install -y postgresql postgresql-contrib
COPY nginx.conf /etc/nginx/nginx.conf

# Install Poetry and add it to PATH so its commands can be executed
# from anywhere, without specifying the full path to its executable.
RUN set -o pipefail && curl -sSL https://install.python-poetry.org | python3 - --version 2.1.3
ENV PATH="/root/.local/bin:$PATH"

# Create the folder where Poetry virtual environments will be stored and make it
# accessible to all users. This is needed by the 'www-data' user during server startup
RUN mkdir -p $POETRY_VIRTUALENVS_PATH && chmod 755 $POETRY_VIRTUALENVS_PATH
ENV POETRY_VIRTUALENVS_PATH=$POETRY_VIRTUALENVS_PATH

# Copy and install project
WORKDIR /app
COPY . .
RUN poetry install --only main && rm nginx.conf

# Generate static and set permissions
RUN poetry run python manage.py collectstatic --no-input --settings=backend.settings.base && \
    chown -R www-data:www-data /app

# Expose and run app
EXPOSE 80
STOPSIGNAL SIGKILL
CMD ["poetry", "run", "/app/start-server.sh"]
