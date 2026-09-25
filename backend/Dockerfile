FROM python:3.14-slim

WORKDIR /app

# Install system deps for asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Dependencies come from uv.lock (the source of truth — see scripts/lock.sh).
# The export never touches the lock (--frozen); pip then installs with hash
# checking, so the image only ever contains the exact audited versions. uv is
# removed afterwards — it is a build tool, not a runtime dependency.
# This layer is cached until pyproject.toml or uv.lock change.
COPY pyproject.toml uv.lock ./
# renovate: datasource=pypi depName=uv
RUN pip install --no-cache-dir uv==0.12.10 \
    && uv pip install --system --no-cache -e ".[dev]" \
    && pip uninstall -y uv

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
