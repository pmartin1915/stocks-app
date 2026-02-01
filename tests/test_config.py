"""Tests for configuration management."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from asymmetric.config import Config
from asymmetric.core.data.exceptions import SECIdentityError


class TestConfigDefaults:
    """Tests for default configuration values."""

    def test_default_sec_identity(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            assert "Asymmetric/1.0" in cfg.sec_identity
            assert "example.com" in cfg.sec_identity

    def test_default_paths(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            assert cfg.db_path == Path("./data/asymmetric.db")
            assert cfg.bulk_dir == Path("./data/bulk")
            assert cfg.cache_dir == Path("./data/cache")

    def test_default_sec_rate_limit(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            assert cfg.sec_requests_per_second == 5.0
            assert cfg.sec_burst_allowance == 2

    def test_default_gemini_thresholds(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            assert cfg.gemini_token_warning_threshold == 180000
            assert cfg.gemini_token_cliff_threshold == 200000


class TestConfigFromEnv:
    """Tests for configuration from environment variables."""

    def test_custom_sec_identity(self):
        with patch.dict(os.environ, {"SEC_IDENTITY": "MyApp/2.0 (me@myco.com)"}):
            cfg = Config()
            assert cfg.sec_identity == "MyApp/2.0 (me@myco.com)"

    def test_custom_db_path(self):
        with patch.dict(os.environ, {"ASYMMETRIC_DB_PATH": "/custom/path.db"}):
            cfg = Config()
            assert cfg.db_path == Path("/custom/path.db")

    def test_gemini_api_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-123"}):
            cfg = Config()
            assert cfg.gemini_api_key == "test-key-123"
            assert cfg.has_gemini is True

    def test_anthropic_api_key(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-123"}):
            cfg = Config()
            assert cfg.anthropic_api_key == "sk-ant-123"
            assert cfg.has_anthropic is True

    def test_no_api_keys(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            assert cfg.has_gemini is False
            assert cfg.has_anthropic is False


class TestConfigValidation:
    """Tests for validate() method."""

    def test_validate_default_identity_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            with pytest.raises(SECIdentityError, match="not configured"):
                cfg.validate()

    def test_validate_example_email_raises(self):
        with patch.dict(os.environ, {"SEC_IDENTITY": "App/1.0 (user@example.com)"}):
            cfg = Config()
            with pytest.raises(SECIdentityError, match="not configured"):
                cfg.validate()

    def test_validate_missing_parens_raises(self):
        with patch.dict(os.environ, {"SEC_IDENTITY": "App/1.0 email@real.com"}):
            cfg = Config()
            with pytest.raises(SECIdentityError, match="Invalid SEC_IDENTITY format"):
                cfg.validate()

    def test_validate_proper_identity_passes(self):
        with patch.dict(os.environ, {"SEC_IDENTITY": "Asymmetric/1.0 (user@company.com)"}):
            cfg = Config()
            cfg.validate()  # Should not raise


class TestConfigDirectories:
    """Tests for ensure_directories() method."""

    def test_ensure_directories_creates_paths(self, tmp_path):
        db_path = tmp_path / "db" / "test.db"
        bulk_dir = tmp_path / "bulk"
        cache_dir = tmp_path / "cache"

        with patch.dict(os.environ, {
            "ASYMMETRIC_DB_PATH": str(db_path),
            "ASYMMETRIC_BULK_DIR": str(bulk_dir),
            "ASYMMETRIC_CACHE_DIR": str(cache_dir),
        }):
            cfg = Config()
            cfg.ensure_directories()

            assert db_path.parent.exists()
            assert bulk_dir.exists()
            assert cache_dir.exists()


class TestConfigMCPPorts:
    """Tests for MCP port configuration."""

    def test_default_mcp_port(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            assert cfg.mcp_default_port == 8765
            assert cfg.mcp_port_range_start == 8765
            assert cfg.mcp_port_range_end == 8785

    def test_custom_mcp_ports(self):
        with patch.dict(os.environ, {
            "ASYMMETRIC_MCP_PORT": "9000",
            "ASYMMETRIC_MCP_PORT_START": "9000",
            "ASYMMETRIC_MCP_PORT_END": "9020",
        }):
            cfg = Config()
            assert cfg.mcp_default_port == 9000
            assert cfg.mcp_port_range_start == 9000
            assert cfg.mcp_port_range_end == 9020
