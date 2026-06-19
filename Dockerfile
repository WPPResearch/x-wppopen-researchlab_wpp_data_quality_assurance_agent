FROM python:3.15-rc-alpine

# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1
# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install system deps needed for building native extensions
RUN apk add --no-cache build-base

WORKDIR /app

# Install uv via multi-stage copy (faster & no pip needed)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy only dependency files first for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies (cached unless pyproject.toml/uv.lock change)
RUN uv sync --frozen

# Copy the rest of the code
COPY . .

# Create a non-root user to avoid running as root
RUN adduser -D appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "data_science.agent:a2a_app", "--host", "0.0.0.0", "--port", "8000"]
