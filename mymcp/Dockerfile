# Use a slim Python base image
FROM python:3.12-slim-bookworm

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

COPY pyproject.toml uv.lock ./   

RUN uv sync --no-cache

COPY mymcp/server.py mymcp/utils.py ./

# Expose the default FastMCP HTTP port
EXPOSE 8080

# Run the server using the HTTP transport
# Replace 'server.py' with your main entry file
# ENTRYPOINT ["/bin/bash"]
ENTRYPOINT ["uv", "run", "python", "server.py", "--transport", "http"]