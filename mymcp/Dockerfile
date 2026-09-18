# Use a slim Python base image
FROM python:3.12-slim-bookworm

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

RUN uv venv

RUN uv pip install \
        --no-cache-dir \
        fastmcp>=3.2.4 \
        googlemaps>=4.10.0 \
        redis>=8.1.0 \
        pymongo==4.17.0

COPY mymcp/server.py mymcp/utils.py ./

# Expose the default FastMCP HTTP port
EXPOSE 8080

# Run the server using the HTTP transport
# Replace 'server.py' with your main entry file
# ENTRYPOINT ["/bin/bash"]
ENTRYPOINT ["uv", "run", "python", "server.py", "--transport", "http"]