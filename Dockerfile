# Build arguments
ARG PYTHON_VERSION=3.9

# Start from the official Python base image on version: 3.9
# First stage, build the application with the dependencies that
# managed by Poetry.
FROM python:${PYTHON_VERSION} as requirements-stage

# Set python virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Set /tmp as the current working directory. Here's where we will
# generate the file requirements.txt.
WORKDIR /tmp

# Update pip and install Poetry in this Docker stage.
RUN pip install --upgrade pip && \
    pip install poetry

# Copy the pyproject.toml and poetry.lock files to the /tmp directory.
# Because it uses ./poetry.lock* (ending with a *), it won't crash if
# that file is not available yet.
COPY ./pyproject.toml ./poetry.lock* /tmp/

# Generate the requirements.txt file.
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

# This is the final stage, anything here will be preserved in the final
# container image.
FROM python:${PYTHON_VERSION}

# Set python virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Set the current working directory to /code. This is where
# we'll put the code for our application.
WORKDIR /code

# Copy the requirements.txt file from the requirements-stage to the
# /code directory.
COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

# Upgrade pip and install the dependencies from the requirements.txt file.
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the api directory to the /code directory.
COPY /api /code/api

# Run the uvicorn command, telling it to use the app object imported
# from api.main.
# TODO: Remove hard coded host and port
CMD uvicorn api.main:app --host 0.0.0.0 --port 80
