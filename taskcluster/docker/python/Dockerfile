FROM ghcr.io/astral-sh/uv:python3.13-alpine

RUN mkdir -p /builds && \
    addgroup -g 1000 worker && \
    adduser -D -h /builds/worker -s /bin/sh -G worker -u 1000 worker && \
    mkdir -p /builds/worker/artifacts && \
    chown worker:worker /builds/worker /builds/worker/artifacts

# %include-run-task

ENV SHELL=/bin/bash \
    HOME=/builds/worker \
    PATH=/builds/worker/.local/bin:$PATH

VOLUME /builds/worker/checkouts
VOLUME /builds/worker/.task-cache/uv
WORKDIR /builds/worker

CMD ["/bin/bash", "--login"]
