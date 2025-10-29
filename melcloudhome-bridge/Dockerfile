# Use build argument to select the correct base image
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.11-alpine3.18
FROM ${BUILD_FROM}

# Install system dependencies including Chromium
# Chromium is required for pymelcloudhome authentication on all architectures
RUN apk add --no-cache \
    chromium \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    bash \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    python3-dev

# Set environment variable to skip pyppeteer browser download (we use system Chromium)
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# Create app directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
# Note: pymelcloudhome 0.3.1 is available on PyPI
# ARM builds may fall back to source if not yet on piwheels
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Copy entrypoint script
COPY run.sh /
RUN chmod +x /run.sh

# Set labels for Home Assistant
LABEL \
    io.hass.name="MELCloud Home Bridge" \
    io.hass.description="Bridge Mitsubishi MELCloud devices to Home Assistant via MQTT" \
    io.hass.arch="amd64|aarch64|armv7" \
    io.hass.type="addon" \
    io.hass.version="1.0.0" \
    maintainer="MELCloud Home Bridge <https://github.com/MHultman/melcloudhome-addon>"

# Expose health check port
EXPOSE 8099

# Run the application
CMD ["/run.sh"]
