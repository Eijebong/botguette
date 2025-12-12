FROM ghcr.io/astral-sh/uv:python3.13-alpine

RUN mkdir -p /builds && \
    groupadd -g 1000 -o worker && \
    useradd -d /builds/worker -s /bin/bash -m worker -g 1000 -o -u 1000 && \
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
