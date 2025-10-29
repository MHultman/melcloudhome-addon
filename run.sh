#!/usr/bin/with-contenv bash
# Note: In Home Assistant, this uses "#!/usr/bin/with-contenv bashio"
# but for standalone testing we use regular bash
set -e

# Display startup banner
echo "Starting MELCloud Home Bridge v1.0.0..."

# Check if we have MELCLOUD_EMAIL environment variable (standalone mode)
# or if we need to load from bashio config (Home Assistant mode)
if [ -n "$MELCLOUD_EMAIL" ]; then
    # Running standalone - environment variables already set
    echo "Running in standalone mode (using environment variables)"
    
    if [ -z "$MELCLOUD_PASSWORD" ]; then
        echo "FATAL: MELCLOUD_PASSWORD environment variable is required!"
        exit 1
    fi
    
    # Set defaults for optional variables
    export MQTT_HOST="${MQTT_HOST:-core-mosquitto}"
    export MQTT_PORT="${MQTT_PORT:-1883}"
    export MQTT_USERNAME="${MQTT_USERNAME:-}"
    export MQTT_PASSWORD="${MQTT_PASSWORD:-}"
    export MQTT_BASE_TOPIC="${MQTT_BASE_TOPIC:-homeassistant}"
    export POLL_INTERVAL="${POLL_INTERVAL:-60}"
    export LOG_LEVEL="${LOG_LEVEL:-INFO}"
    
    echo "Configuration loaded from environment variables"
    echo "MQTT Host: $MQTT_HOST:$MQTT_PORT"
    echo "Poll Interval: $POLL_INTERVAL seconds"
    echo "Log Level: $LOG_LEVEL"
    
elif [ -f /usr/lib/bashio/bashio.sh ]; then
    # Running in Home Assistant - source bashio and use it
    echo "Running in Home Assistant Supervisor mode"
    source /usr/lib/bashio/bashio.sh
    
    bashio::log.info "Loading configuration from Home Assistant"
    
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
    
    bashio::log.info "Configuration loaded successfully"
else
    echo "FATAL: No configuration source available!"
    echo "Either set MELCLOUD_EMAIL environment variable or run in Home Assistant"
    exit 1
fi

# Run the Python application
echo "Launching MELCloud Home Bridge..."
cd /app
exec python -m app.main
