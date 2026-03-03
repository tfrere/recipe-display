FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | bash \
    && apt-get update \
    && apt-get install -y git-lfs \
    && git lfs install \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

WORKDIR /app

COPY . .

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

RUN mkdir -p /app/data/recipes/images \
    && chown -R nobody:nogroup /app/data \
    && chmod -R 755 /app/data

EXPOSE $PORT

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-3001} --timeout-keep-alive 120 --limit-concurrency 100"]