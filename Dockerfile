# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.11-slim
FROM python:${PYTHON_VERSION}

# Select which CLI to default-run: modelless | full
ARG FLAVOR=modelless
ENV FLAVOR=${FLAVOR}

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System dependencies for building and running (pygraphviz, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates curl \
    build-essential gcc g++ make pkg-config \
    graphviz libgraphviz-dev \
    python3-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Only copy what we need to build the wheel to leverage Docker layer caching
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip setuptools wheel \
 && pip install .

# Provide a simple, predictable entrypoint
COPY docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["--help"]
