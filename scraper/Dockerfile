FROM dorowu/ubuntu-desktop-lxde-vnc:focal

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list
RUN apt-get update && apt-get install -y google-chrome-stable

RUN apt-get install -y libmagic1 build-essential
RUN apt-get install -y fonts-beng fonts-beng-extra fonts-lohit-beng-bengali

COPY pyproject.toml uv.lock ./

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/python
ENV UV_PYTHON_PREFERENCE=only-managed

RUN uv sync --frozen --no-dev --python 3.12

COPY ./ /app

ENV PATH="$PATH:/python/bin"
ENV PYTHONUNBUFFERED 1
