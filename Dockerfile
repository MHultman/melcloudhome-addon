ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.11-alpine3.18
FROM ${BUILD_FROM}

# Install system dependencies for Playwright and Chromium
RUN apk add --no-cache \
    chromium \
    chromium-chromedriver \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    nodejs \
    bash

# Set environment variables for Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# Create app directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and Chromium browser
RUN playwright install chromium && \
    playwright install-deps chromium

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
