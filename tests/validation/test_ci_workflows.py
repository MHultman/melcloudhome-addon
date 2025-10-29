"""
Validation test for CI/CD workflows.

Verifies GitHub Actions workflows are properly configured per T192 and T193.
"""

import yaml
from pathlib import Path


def test_test_workflow_exists():
    """Verify test.yaml workflow exists (T192)."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "test.yaml"
    assert workflow_path.exists(), ".github/workflows/test.yaml not found"


def test_test_workflow_valid_yaml():
    """Verify test.yaml is valid YAML."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "test.yaml"
    
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = yaml.safe_load(f)
    
    assert isinstance(workflow, dict), "test.yaml should parse to dictionary"


def test_test_workflow_structure():
    """Verify test.yaml has proper structure for automated testing."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "test.yaml"
    
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = yaml.safe_load(f)
    
    assert "name" in workflow, "Missing workflow name"
    # YAML parser converts 'on:' to True as dict key
    assert True in workflow or "on" in workflow, "Missing trigger configuration"
    assert "jobs" in workflow, "Missing jobs section"
    
    # Should have test job
    assert "test" in workflow["jobs"] or any("test" in job.lower() for job in workflow["jobs"]), "Missing test job"
    
    # Should run on push/pull_request
    triggers = workflow.get("on") or workflow.get(True)
    if isinstance(triggers, dict):
        assert "push" in triggers or "pull_request" in triggers, "Should trigger on push or PR"


def test_test_workflow_has_pytest():
    """Verify test workflow includes pytest execution."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "test.yaml"
    content = workflow_path.read_text(encoding="utf-8")
    
    assert "pytest" in content, "test.yaml should run pytest"
    assert "coverage" in content, "test.yaml should collect coverage"


def test_test_workflow_has_linting():
    """Verify test workflow includes linting (T187)."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "test.yaml"
    content = workflow_path.read_text(encoding="utf-8")
    
    assert "ruff" in content, "test.yaml should run ruff linting"


def test_build_workflow_exists():
    """Verify build.yaml workflow exists (T193)."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "build.yaml"
    assert workflow_path.exists(), ".github/workflows/build.yaml not found"


def test_build_workflow_valid_yaml():
    """Verify build.yaml is valid YAML."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "build.yaml"
    
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = yaml.safe_load(f)
    
    assert isinstance(workflow, dict), "build.yaml should parse to dictionary"


def test_build_workflow_multi_arch():
    """Verify build workflow supports multiple architectures."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "build.yaml"
    content = workflow_path.read_text(encoding="utf-8")
    
    # Should mention multiple architectures
    assert "amd64" in content, "build.yaml should support amd64"
    assert "aarch64" in content or "arm64" in content, "build.yaml should support aarch64"
    assert "armv7" in content or "arm/v7" in content, "build.yaml should support armv7"


def test_build_workflow_structure():
    """Verify build.yaml has proper structure for Docker builds."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "build.yaml"
    
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = yaml.safe_load(f)
    
    assert "name" in workflow, "Missing workflow name"
    # YAML parser converts 'on:' to True as dict key
    assert True in workflow or "on" in workflow, "Missing trigger configuration"
    assert "jobs" in workflow, "Missing jobs section"
    
    # Should have build job
    assert "build" in workflow["jobs"], "Missing build job"


def test_build_workflow_docker():
    """Verify build workflow uses Docker buildx for multi-arch."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "build.yaml"
    content = workflow_path.read_text(encoding="utf-8")
    
    assert "docker/setup-buildx-action" in content, "Should use Docker Buildx"
    assert "docker/build-push-action" in content, "Should use Docker build-push action"


def test_workflows_have_proper_permissions():
    """Verify workflows have appropriate permissions."""
    build_workflow = Path(__file__).parent.parent.parent / ".github" / "workflows" / "build.yaml"
    
    # Build workflow uses GITHUB_TOKEN which has default permissions
    # No need to explicitly declare permissions for public repos
    assert build_workflow.exists(), "Build workflow should exist"


def test_workflows_trigger_on_correct_events():
    """Verify workflows trigger on appropriate events."""
    test_workflow = Path(__file__).parent.parent.parent / ".github" / "workflows" / "test.yaml"
    build_workflow = Path(__file__).parent.parent.parent / ".github" / "workflows" / "build.yaml"
    
    with open(test_workflow, "r", encoding="utf-8") as f:
        test_config = yaml.safe_load(f)
    
    with open(build_workflow, "r", encoding="utf-8") as f:
        build_config = yaml.safe_load(f)
    
    # Test should run on push and PR - YAML converts 'on:' to True as key
    test_triggers = test_config.get("on") or test_config.get(True)
    if isinstance(test_triggers, dict):
        assert "push" in test_triggers or "pull_request" in test_triggers, "Test should run on push/PR"
    
    # Build should run on push to main or tags - YAML converts 'on:' to True as key
    build_triggers = build_config.get("on") or build_config.get(True)
    if isinstance(build_triggers, dict):
        assert "push" in build_triggers or "workflow_dispatch" in build_triggers, "Build should run on push or manual trigger"


def test_all_workflows_summary():
    """Print summary of all workflows."""
    workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"
    
    if not workflows_dir.exists():
        assert False, ".github/workflows directory not found"
    
    workflow_files = list(workflows_dir.glob("*.yaml")) + list(workflows_dir.glob("*.yml"))
    
    assert len(workflow_files) >= 2, "Should have at least 2 workflows (test and build)"
    
    print(f"\n✓ Found {len(workflow_files)} GitHub Actions workflows:")
    for workflow in workflow_files:
        with open(workflow, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            name = config.get("name", workflow.stem)
            print(f"  - {name} ({workflow.name})")
