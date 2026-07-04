"""Tests for platform detection."""

import pytest

from shell_configs.platform import Platform, detect_platform


@pytest.fixture(autouse=True)
def clear_platform_cache():
    detect_platform.cache_clear()
    yield
    detect_platform.cache_clear()


@pytest.mark.unit
class TestDetectPlatform:
    def test_detect_platform_darwin(self, monkeypatch):
        monkeypatch.setattr("shell_configs.platform._platform.system", lambda: "Darwin")
        assert detect_platform() == Platform.MACOS

    def test_detect_platform_windows(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.platform._platform.system", lambda: "Windows"
        )
        assert detect_platform() == Platform.WINDOWS

    def test_detect_platform_linux(self, monkeypatch):
        import platform as _platform

        monkeypatch.setattr("shell_configs.platform._platform.system", lambda: "Linux")
        monkeypatch.setattr(
            "shell_configs.platform._platform.uname",
            lambda: _platform.uname_result(
                "Linux", "host", "5.15.0-generic", "#1 SMP", "x86_64"
            ),
        )
        monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
        assert detect_platform() == Platform.LINUX

    def test_detect_platform_wsl_via_release(self, monkeypatch):
        import platform as _platform

        monkeypatch.setattr("shell_configs.platform._platform.system", lambda: "Linux")
        monkeypatch.setattr(
            "shell_configs.platform._platform.uname",
            lambda: _platform.uname_result(
                "Linux", "host", "5.15.0-microsoft-standard-WSL2", "#1 SMP", "x86_64"
            ),
        )
        monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
        assert detect_platform() == Platform.WSL

    def test_detect_platform_wsl_via_env(self, monkeypatch):
        import platform as _platform

        monkeypatch.setattr("shell_configs.platform._platform.system", lambda: "Linux")
        monkeypatch.setattr(
            "shell_configs.platform._platform.uname",
            lambda: _platform.uname_result(
                "Linux", "host", "5.15.0-generic", "#1 SMP", "x86_64"
            ),
        )
        monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
        assert detect_platform() == Platform.WSL

    def test_detect_platform_unknown_falls_back_to_linux(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.platform._platform.system", lambda: "FreeBSD"
        )
        assert detect_platform() == Platform.LINUX


@pytest.mark.unit
class TestOverlayChain:
    def test_linux_chain(self):
        assert Platform.LINUX.overlay_chain == ["linux"]

    def test_wsl_chain(self):
        assert Platform.WSL.overlay_chain == ["linux", "wsl"]

    def test_macos_chain(self):
        assert Platform.MACOS.overlay_chain == ["macos"]

    def test_windows_chain(self):
        assert Platform.WINDOWS.overlay_chain == ["windows"]
