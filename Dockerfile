ARG PYTHON_VERSION=3.11-slim

FROM python:${PYTHON_VERSION}

# Install virtualenv and create a virtual environment
RUN pip install --no-cache-dir -U virtualenv>=20.13.1 && virtualenv /env --python=python3.11
ENV PATH /env/bin:$PATH

# Install make, nginx and copy configuration
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl g++ libpq-dev make nginx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm /etc/nginx/sites-enabled/default
COPY nginx.conf /etc/nginx/nginx.conf

# Install pip requirements
WORKDIR /app
COPY . .
RUN /env/bin/pip install --no-cache-dir . && rm nginx.conf
RUN /env/bin/pip install --no-cache-dir ./chatbot

# Prevents Python from writing .pyc files to disc
# https://docs.python.org/3/using/cmdline.html#envvar-PYTHONDONTWRITEBYTECODE
ENV PYTHONDONTWRITEBYTECODE 1

# Ensures that the python output is sent straight to terminal (e.g. your container log)
# without being first buffered and that you can see the output of your application (e.g. django logs)
# in real time. Equivalent to python -u: https://docs.python.org/3/using/cmdline.html#cmdoption-u
ENV PYTHONUNBUFFERED 1

# Copy app, generate static and set permissions
RUN /env/bin/python manage.py collectstatic --no-input --settings=backend.settings.base && \
    chown -R www-data:www-data /app

# Expose and run app
EXPOSE 80
STOPSIGNAL SIGKILL
CMD ["/app/start-server.sh"]
