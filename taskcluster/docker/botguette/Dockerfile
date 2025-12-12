FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder

WORKDIR /app

ARG SRC=topsrcdir

# %include pyproject.toml
# %include uv.lock
# %include README.md
# %include botguette
ADD ${SRC}/pyproject.toml ${SRC}/uv.lock ${SRC}/README.md /app/
ADD ${SRC}/botguette /app/botguette

RUN uv sync --locked

FROM python:3.13

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

WORKDIR /app
USER app

COPY --from=builder --chown=app:app /app /app
ENTRYPOINT ["/app/.venv/bin/python", "-m", "botguette.bot"]
