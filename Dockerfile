FROM ghcr.io/astral-sh/uv:python3.14-alpine

# Security: Set environment variables to ensure safe Python execution
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Security: Create a non-root user (alpine uses addgroup/adduser)
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Install git for git dependencies, and upgrade packages for security patches
RUN apk update && \
    apk upgrade && \
    apk add --no-cache git

# Copy dependency files first to leverage caching
COPY pyproject.toml uv.lock ./

# Install dependencies without the project source
RUN uv sync --frozen --no-dev --no-install-project --compile-bytecode

COPY . .

# Install the project
RUN uv sync --frozen --no-dev --compile-bytecode

# Security: Change ownership to the non-root user
RUN chown -R appuser:appgroup /app

# Security: Switch to non-root user
USER appuser

# Ensure the virtual environment is used
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-O", "-X", "utf8", "-X", "faulthandler", "main.py"]
