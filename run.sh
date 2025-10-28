#!/usr/bin/with-contenv bashio
set -e

# Display startup banner
bashio::log.info "Starting MELCloud Home Bridge v1.0.0..."

# Check if configuration exists
if ! bashio::config.exists 'melcloud_email'; then
    bashio::log.fatal "MELCloud email is required!"
    exit 1
fi

if ! bashio::config.exists 'melcloud_password'; then
    bashio::log.fatal "MELCloud password is required!"
    exit 1
fi

# Export configuration as environment variables for Python app
export MELCLOUD_EMAIL="$(bashio::config 'melcloud_email')"
export MELCLOUD_PASSWORD="$(bashio::config 'melcloud_password')"
export MQTT_HOST="$(bashio::config 'mqtt_host')"
export MQTT_PORT="$(bashio::config 'mqtt_port')"
export MQTT_USERNAME="$(bashio::config 'mqtt_username' '')"
export MQTT_PASSWORD="$(bashio::config 'mqtt_password' '')"
export MQTT_BASE_TOPIC="$(bashio::config 'mqtt_base_topic')"
export POLL_INTERVAL="$(bashio::config 'poll_interval')"
export LOG_LEVEL="$(bashio::config 'log_level')"

# Run the Python application
bashio::log.info "Launching MELCloud Home Bridge..."
cd /app
exec python -m app.main
