FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /code/

RUN uv pip install --system flake8

COPY requirements.txt .
RUN uv pip install --system -r /code/requirements.txt

COPY tests-requirements.txt .
RUN uv pip install --system -r /code/tests-requirements.txt

COPY component_config/ component_config
COPY src/ src
COPY tests/ tests
COPY flake8.cfg .
COPY deploy.sh .

CMD ["python", "-u", "/code/src/component.py"]
