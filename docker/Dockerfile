FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip wheel --no-cache-dir --wheel-dir /wheels ".[api,gotenberg]"

FROM python:3.12-slim

LABEL org.opencontainers.image.licenses="Apache-2.0" \
    org.opencontainers.image.source="https://github.com/gordonkit/gordon-doc-converter"

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install --no-install-recommends -y libreoffice-writer fonts-noto-cjk curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 gordon
COPY --from=builder /wheels /wheels
COPY LICENSE NOTICE THIRD_PARTY_NOTICES.txt /usr/share/licenses/gordon-doc-converter/
COPY docker/entrypoint.sh /usr/local/bin/gordon-doc-entrypoint
RUN pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels \
    && chmod 755 /usr/local/bin/gordon-doc-entrypoint
USER gordon
WORKDIR /work
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/home/gordon
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail http://127.0.0.1:8000/ready || exit 1
ENTRYPOINT ["gordon-doc-entrypoint"]