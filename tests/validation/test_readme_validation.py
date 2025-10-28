"""
Validation test for README.md completeness.

Verifies that README.md contains all required sections per T189.
"""

import re
from pathlib import Path


def test_readme_exists():
    """Verify README.md exists in project root."""
    readme_path = Path(__file__).parent.parent.parent / "README.md"
    assert readme_path.exists(), "README.md not found in project root"


def test_readme_has_project_description():
    """Verify README.md has project description and features (T171)."""
    readme_path = Path(__file__).parent.parent.parent / "README.md"
    content = readme_path.read_text(encoding="utf-8")

    assert "# MELCloud Home Bridge" in content, "Missing project title"
    assert "## Features" in content, "Missing features section"
    assert "Home Assistant" in content, "Missing Home Assistant reference"
    assert "MQTT" in content, "Missing MQTT reference"
    assert "MELCloud" in content, "Missing MELCloud reference"


def test_readme_has_prerequisites():
    """Verify README.md has prerequisites section (T172)."""
    readme_path = Path(__file__).parent.parent.parent / "README.md"
    content = readme_path.read_text(encoding="utf-8")

    assert "## Prerequisites" in content, "Missing prerequisites section"
    assert "MQTT Broker" in content, "Missing MQTT broker prerequisite"
    assert "MELCloud Account" in content, "Missing MELCloud account prerequisite"


def test_readme_has_installation():
    """Verify README.md has installation instructions (T173)."""
    readme_path = Path(__file__).parent.parent.parent / "README.md"
    content = readme_path.read_text(encoding="utf-8")

    assert "## Installation" in content, "Missing installation section"
    assert "Step 1:" in content, "Missing step-by-step instructions"
    assert "MQTT" in content, "Missing MQTT installation"
    assert "Add-on" in content, "Missing add-on installation"


def test_readme_has_configuration():
    """Verify README.md has configuration reference (T174)."""
    readme_path = Path(__file__).parent.parent.parent / "README.md"
    content = readme_path.read_text(encoding="utf-8")

    assert "## Configuration" in content, "Missing configuration section"
    assert "melcloud_email" in content, "Missing melcloud_email option"
    assert "melcloud_password" in content, "Missing melcloud_password option"
    assert "mqtt_host" in content, "Missing mqtt_host option"
    assert "poll_interval" in content, "Missing poll_interval option"


def test_readme_has_troubleshooting():
    """Verify README.md has troubleshooting section (T175)."""
    readme_path = Path(__file__).parent.parent.parent / "README.md"
    content = readme_path.read_text(encoding="utf-8")

    assert "## Troubleshooting" in content, "Missing troubleshooting section"
    assert "won't start" in content.lower(), "Missing startup troubleshooting"
    assert "authentication" in content.lower(), "Missing auth troubleshooting"


def test_readme_has_support_info():
    """Verify README.md has support/FAQ information (T176)."""
    readme_path = Path(__file__).parent.parent.parent / "README.md"
    content = readme_path.read_text(encoding="utf-8")

    # Check for support or FAQ section
    has_support = "## Support" in content
    has_technical = "## Technical" in content
    assert (
        has_support or has_technical
    ), "Missing support or technical details section"


def test_readme_formatting():
    """Verify README.md has proper markdown formatting."""
    readme_path = Path(__file__).parent.parent.parent / "README.md"
    content = readme_path.read_text(encoding="utf-8")

    # Check for proper headers (should start with #)
    headers = re.findall(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE)
    assert len(headers) > 5, "README should have multiple headers"

    # Check for code blocks
    assert "```" in content, "README should have code examples"

    # Check for links
    assert "[" in content and "](" in content, "README should have links"


def test_readme_completeness():
    """Overall completeness check."""
    readme_path = Path(__file__).parent.parent.parent / "README.md"
    content = readme_path.read_text(encoding="utf-8")

    # Minimum length check (comprehensive README should be substantial)
    assert len(content) > 5000, "README seems too short to be comprehensive"

    # Should have multiple sections
    section_count = content.count("## ")
    assert section_count >= 8, f"README should have at least 8 sections, found {section_count}"

    print(f"✓ README.md validation passed: {len(content)} characters, {section_count} sections")
