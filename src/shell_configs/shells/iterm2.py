"""iTerm2 terminal emulator configuration."""

from __future__ import annotations

import re

from pathlib import Path
from typing import TYPE_CHECKING

from shell_configs.config import get_config_dir
from shell_configs.platform import Platform, is_platform
from shell_configs.shells.base import (
    AdditionalFile,
    ConfigFile,
    PreferencesFile,
    Shell,
)

if TYPE_CHECKING:
    from shell_configs.manager.core import PrefDiffFormatters

ITERM2_PREFERENCES_DOMAIN = "com.googlecode.iterm2"

# KEY_ACTION IDs from iTerm2's sources/Keyboard/iTermKeyBindingAction.h, named
# after the defaults in -[iTermKeyBindingAction displayName] (parameter omitted).
_KEY_ACTION_NAMES = {
    0: "Next Tab",
    1: "Next Window",
    2: "Previous Tab",
    3: "Previous Window",
    4: "Scroll To End",
    5: "Scroll To Top",
    6: "Scroll One Line Down",
    7: "Scroll One Line Up",
    8: "Scroll One Page Down",
    9: "Scroll One Page Up",
    10: "Send Escape Sequence",
    11: "Send Hex Codes",
    12: "Send Text",
    13: "Ignore",
    14: "Unsupported Command",
    15: "Start Instant Replay",
    16: "Send ^H Backspace",
    17: "Send ^? Backspace",
    18: "Select Split Pane on Left",
    19: "Select Split Pane on Right",
    20: "Select Split Pane Above",
    21: "Select Split Pane Below",
    22: "Do Not Remap Modifiers",
    23: "Toggle Fullscreen",
    24: "Remap Modifiers in iTerm2 Only",
    25: "Select Menu Item",
    26: "New Window with Profile",
    27: "New Tab with Profile",
    28: "Split Horizontally with Profile",
    29: "Split Vertically with Profile",
    30: "Next Pane",
    31: "Previous Pane",
    32: "Cycle Tabs Forward",
    33: "Move Tab Left",
    34: "Move Tab Right",
    35: "Run Coprocess",
    36: "Find Regex",
    37: "Change Profile",
    38: "Send Text (vim escapes)",
    39: "Cycle Tabs Backward",
    40: "Load Color Preset",
    41: "Paste",
    42: "Paste from Selection",
    43: "Toggle Pin Hotkey Window",
    44: "Undo",
    45: "Move End of Selection Left",
    46: "Move End of Selection Right",
    47: "Move Start of Selection Left",
    48: "Move Start of Selection Right",
    49: "Decrease Height",
    50: "Increase Height",
    51: "Decrease Width",
    52: "Increase Width",
    53: "Swap With Split Pane on Left",
    54: "Swap With Split Pane on Right",
    55: "Swap With Split Pane Above",
    56: "Swap With Split Pane Below",
    57: "Find Again Down",
    58: "Find Again Up",
    59: "Toggle Mouse Reporting",
    60: "Call Script Function",
    61: "Duplicate Tab",
    62: "Move to Split Pane",
    63: "Send Snippet",
    64: "Compose",
    65: "Send tmux Command",
    66: "Sequence",
    67: "Swap with Next Pane",
    68: "Swap with Previous Pane",
    69: "Copy Selection or Send ^C",
    70: "Paste or Send ^V",
    71: "Alert on Next Mark",
    72: "Copy Interpolated String",
    73: "Copy Mode",
    74: "Bypass Terminal",
    75: "Toggle Setting",
    76: "Send Text (no broadcast)",
    77: "New Floating Pane with Profile",
}

# NSEvent modifier flags, in the order iTerm2 displays them.
_MODIFIER_SYMBOLS = ((0x40000, "⌃"), (0x80000, "⌥"), (0x20000, "⇧"), (0x100000, "⌘"))

_SPECIAL_KEYS = {
    0x3: "Enter",
    0x9: "Tab",
    0xD: "Return",
    0x19: "Tab",
    0x1B: "Esc",
    0x20: "Space",
    0x7F: "Delete",
    0xF700: "↑",
    0xF701: "↓",
    0xF702: "←",
    0xF703: "→",
    0xF728: "Forward Delete",
    0xF729: "Home",
    0xF72B: "End",
    0xF72C: "Page Up",
    0xF72D: "Page Down",
    **{0xF704 + i: f"F{i + 1}" for i in range(20)},
}

# Fields the key combo already conveys.
_HIDDEN_BINDING_FIELDS = {"Keycode", "Modifiers", "Version"}

_KEY_PATTERN = re.compile(r"0x([0-9a-f]+)-0x([0-9a-f]+)(?:-0x[0-9a-f]+)?")


def _key_combo(key: str) -> str:
    """Render a GlobalKeyMap key like ``0x54-0x120000-0x11`` as ``⇧⌘T``."""
    match = _KEY_PATTERN.fullmatch(key)
    if not match:
        return f'"{key}"' if "." in key else key
    char, flags = int(match[1], 16), int(match[2], 16)
    modifiers = "".join(symbol for mask, symbol in _MODIFIER_SYMBOLS if flags & mask)
    name = _SPECIAL_KEYS.get(char)
    if name is None:
        name = chr(char).upper() if 0x20 < char < 0xF700 else hex(char)
    return modifiers + name


def _format_value(field: str, value: object) -> str:
    if value is None:
        return "(none)"
    if field == "Action" and isinstance(value, int):
        return _KEY_ACTION_NAMES.get(value, f"action {value}")
    if isinstance(value, str):
        # Keep each diff entry on one line (menu paths are newline-separated).
        return '"' + value.replace("\n", "\\n").replace("\t", "\\t") + '"'
    return str(value)


def _describe_binding(binding: object) -> str:
    if not isinstance(binding, dict):
        return _format_value("", binding)
    description = _format_value("Action", binding.get("Action"))
    if binding.get("Text"):
        description += f" {_format_value('Text', binding['Text'])}"
    return description


def diff_global_key_map(current: object, expected: object) -> list[str]:
    """Describe GlobalKeyMap changes one key binding at a time."""
    current = current if isinstance(current, dict) else {}
    expected = expected if isinstance(expected, dict) else {}
    lines: list[str] = []
    for key in sorted(current.keys() | expected.keys()):
        old, new = current.get(key), expected.get(key)
        label = f"Key binding {_key_combo(key)}"
        if old == new:
            continue
        if old is None or new is None:
            sign = "+" if old is None else "-"
            lines.append(f"  {sign} {label}: {_describe_binding(new or old)}")
            continue
        if not (isinstance(old, dict) and isinstance(new, dict)):
            lines.append(
                f"  ~ {label}: {_describe_binding(old)} → {_describe_binding(new)}"
            )
            continue
        changed = [
            f for f in sorted(old.keys() | new.keys()) if old.get(f) != new.get(f)
        ]
        shown = [f for f in changed if f not in _HIDDEN_BINDING_FIELDS] or changed
        for field in shown:
            before = _format_value(field, old.get(field))
            after = _format_value(field, new.get(field))
            lines.append(f"  ~ {label}: {field.lower()}: {before} → {after}")
    return lines


ITERM2_DIFF_FORMATTERS: PrefDiffFormatters = {"GlobalKeyMap": diff_global_key_map}


class ITerm2Shell(Shell):
    """iTerm2 terminal emulator configuration handler (macOS-only)."""

    @property
    def name(self) -> str:
        return "iterm2"

    @property
    def display_name(self) -> str:
        return "iTerm2"

    def get_config_files(self) -> list[ConfigFile]:
        return []

    def get_additional_files(self) -> list[AdditionalFile]:
        if not is_platform(Platform.MACOS):
            return []
        config_dir = get_config_dir()
        dynamic_profiles_dir = (
            Path.home()
            / "Library"
            / "Application Support"
            / "iTerm2"
            / "DynamicProfiles"
        )
        backup_dir = Path.home() / ".config" / "shell-configs" / "backups" / "iterm2"
        return [
            AdditionalFile(
                name="shell-configs.json",
                source_path=config_dir / "iterm2" / "profile.json",
                target_path=dynamic_profiles_dir / "shell-configs.json",
                backup_dir=backup_dir,
            )
        ]

    def get_preferences_files(self) -> list[PreferencesFile]:
        if not is_platform(Platform.MACOS):
            return []
        config_dir = get_config_dir()
        return [
            PreferencesFile(
                name="iTerm2 Preferences",
                source_path=config_dir / "iterm2" / "preferences.json",
                domain=ITERM2_PREFERENCES_DOMAIN,
                app_name="iTerm2",
                diff_formatters=ITERM2_DIFF_FORMATTERS,
            )
        ]

    def _get_validation_command(self, temp_file: Path) -> list[str]:
        return ["python3", "-m", "json.tool", str(temp_file)]

    def _get_temp_suffix(self) -> str:
        return ".json"
