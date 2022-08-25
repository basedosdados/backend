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
ADD ./pyproject.toml ./poetry.lock* /tmp/

# Generate the requirements.txt file.
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

# This is the final stage, anything here will be preserved in the final
# container image.
FROM python:${PYTHON_VERSION}

# Create the app user
RUN addgroup --system app && adduser --no-create-home --system --group app

# Set python virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Set the current working directory to /code. This is where
# we'll put the code for our application.
WORKDIR /code

# https://docs.python.org/3/using/cmdline.html#envvar-PYTHONDONTWRITEBYTECODE
# Prevents Python from writing .pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1

# ensures that the python output is sent straight to terminal (e.g. your container log)
# without being first buffered and that you can see the output of your application (e.g. django logs)
# in real time. Equivalent to python -u: https://docs.python.org/3/using/cmdline.html#cmdoption-u
ENV PYTHONUNBUFFERED 1

# Copy the requirements.txt file from the requirements-stage to the
# /code directory.
COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

# Upgrade pip and install the dependencies from the requirements.txt file.
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the api directory to the /code directory.
ADD /app /code/app
ADD run.sh /code/run.sh
RUN chmod +x /code/run.sh

# chown all the files to the app user
RUN chown -R app:app /code

# Change to the app user
USER app

# Run the uvicorn command, telling it to use the app object imported
# from api.main.
CMD ["sh", "/code/run.sh"]
