FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /code/

COPY pyproject.toml .
COPY uv.lock .

RUN uv sync --all-groups

COPY component_config/ component_config
COPY src/ src
COPY tests/ tests
COPY flake8.cfg .
COPY deploy.sh .

CMD ["uv", "run", "python", "-u", "/code/src/component.py"]
