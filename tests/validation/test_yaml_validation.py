"""
Validation test for example configuration files.

Verifies that example YAML files are valid and complete per T191.
"""

import yaml
from pathlib import Path


def test_basic_config_exists():
    """Verify basic-config.yaml exists."""
    config_path = Path(__file__).parent.parent.parent / "examples" / "basic-config.yaml"
    assert config_path.exists(), "examples/basic-config.yaml not found"


def test_basic_config_valid_yaml():
    """Verify basic-config.yaml is valid YAML."""
    config_path = Path(__file__).parent.parent.parent / "examples" / "basic-config.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    assert isinstance(config, dict), "basic-config.yaml should parse to dictionary"


def test_basic_config_required_fields():
    """Verify basic-config.yaml has required fields."""
    config_path = Path(__file__).parent.parent.parent / "examples" / "basic-config.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    assert "melcloud_email" in config, "Missing melcloud_email"
    assert "melcloud_password" in config, "Missing melcloud_password"
    assert "mqtt_host" in config, "Missing mqtt_host"


def test_advanced_config_exists():
    """Verify advanced-config.yaml exists."""
    config_path = Path(__file__).parent.parent.parent / "examples" / "advanced-config.yaml"
    assert config_path.exists(), "examples/advanced-config.yaml not found"


def test_advanced_config_valid_yaml():
    """Verify advanced-config.yaml is valid YAML."""
    config_path = Path(__file__).parent.parent.parent / "examples" / "advanced-config.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    assert isinstance(config, dict), "advanced-config.yaml should parse to dictionary"


def test_advanced_config_all_options():
    """Verify advanced-config.yaml has all configuration options."""
    config_path = Path(__file__).parent.parent.parent / "examples" / "advanced-config.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    expected_options = [
        "melcloud_email",
        "melcloud_password",
        "mqtt_host",
        "mqtt_port",
        "mqtt_username",
        "mqtt_password",
        "mqtt_base_topic",
        "poll_interval",
        "log_level",
    ]
    
    for option in expected_options:
        assert option in config, f"Missing option: {option}"


def test_docker_compose_exists():
    """Verify docker-compose.yaml exists."""
    compose_path = Path(__file__).parent.parent.parent / "examples" / "docker-compose.yaml"
    assert compose_path.exists(), "examples/docker-compose.yaml not found"


def test_docker_compose_valid_yaml():
    """Verify docker-compose.yaml is valid YAML."""
    compose_path = Path(__file__).parent.parent.parent / "examples" / "docker-compose.yaml"
    
    with open(compose_path, "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)
    
    assert isinstance(compose, dict), "docker-compose.yaml should parse to dictionary"


def test_docker_compose_structure():
    """Verify docker-compose.yaml has proper structure."""
    compose_path = Path(__file__).parent.parent.parent / "examples" / "docker-compose.yaml"
    
    with open(compose_path, "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)
    
    assert "version" in compose or "services" in compose, "Missing version or services"
    assert "services" in compose, "Missing services section"
    assert "mosquitto" in compose["services"], "Missing mosquitto service"
    assert "melcloud-bridge" in compose["services"], "Missing melcloud-bridge service"


def test_mock_config_fixture_exists():
    """Verify mock_config.yaml test fixture exists."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "mock_config.yaml"
    assert fixture_path.exists(), "tests/fixtures/mock_config.yaml not found"


def test_mock_config_fixture_valid():
    """Verify mock_config.yaml test fixture is valid YAML."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "mock_config.yaml"
    
    with open(fixture_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    assert isinstance(config, dict), "mock_config.yaml should parse to dictionary"
    assert "melcloud_email" in config, "Missing melcloud_email"
    assert "melcloud_password" in config, "Missing melcloud_password"


def test_all_yaml_files_valid():
    """Test all YAML files in project can be parsed."""
    project_root = Path(__file__).parent.parent.parent
    
    yaml_files = [
        project_root / "examples" / "basic-config.yaml",
        project_root / "examples" / "advanced-config.yaml",
        project_root / "examples" / "docker-compose.yaml",
        project_root / "tests" / "fixtures" / "mock_config.yaml",
        project_root / "config.yaml",  # Home Assistant add-on config
    ]
    
    for yaml_file in yaml_files:
        if not yaml_file.exists():
            continue  # Skip if file doesn't exist (optional)
        
        with open(yaml_file, "r", encoding="utf-8") as f:
            try:
                yaml.safe_load(f)
                print(f"✓ {yaml_file.name} is valid YAML")
            except yaml.YAMLError as e:
                assert False, f"Invalid YAML in {yaml_file}: {e}"


def test_yaml_files_have_comments():
    """Verify example YAML files have helpful comments."""
    config_files = [
        Path(__file__).parent.parent.parent / "examples" / "basic-config.yaml",
        Path(__file__).parent.parent.parent / "examples" / "advanced-config.yaml",
    ]
    
    for config_file in config_files:
        content = config_file.read_text(encoding="utf-8")
        
        # Should have comments (lines starting with #)
        comment_lines = [line for line in content.split("\n") if line.strip().startswith("#")]
        assert len(comment_lines) > 0, f"{config_file.name} should have comments"
        
        print(f"✓ {config_file.name} has {len(comment_lines)} comment lines")
