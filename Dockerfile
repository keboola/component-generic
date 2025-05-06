FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /code/

COPY pyproject.toml .
COPY uv.lock .

# Keboola running containers with "-u 1000:1000" causes permission problems with uv's venvs
# Using the system Python environment as a workaround until we find a better way
ENV UV_PROJECT_ENVIRONMENT="/usr/local/"
RUN uv sync --all-groups

COPY component_config/ component_config
COPY src/ src
COPY tests/ tests
COPY flake8.cfg .
COPY deploy.sh .

CMD ["python", "-u", "/code/src/component.py"]
