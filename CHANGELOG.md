# CHANGELOG

<!-- version list -->

## v0.43.0 (2026-05-21)

### Bug Fixes

- **tests**: Format _collect_scan_results signature for ruff
  ([`f927db8`](https://github.com/wpfleger96/shell-configs/commit/f927db860f98ed2dc25a47fe493ec96143fa92ba))

### Features

- **disk-cleanup**: Add Rich output, interactive mode, size cache, and parallel scan
  ([`fcb9f93`](https://github.com/wpfleger96/shell-configs/commit/fcb9f93e26daecd663cec31a54d943992a61ac95))


## v0.42.1 (2026-05-20)

### Bug Fixes

- Format test_disk_cleanup.py ([#41](https://github.com/wpfleger96/shell-configs/pull/41),
  [`a89f78f`](https://github.com/wpfleger96/shell-configs/commit/a89f78fbc76377fb6b4bf88bde3da4529a2a1acf))

### Chores

- Add uv.lock for reproducible installs ([#41](https://github.com/wpfleger96/shell-configs/pull/41),
  [`a89f78f`](https://github.com/wpfleger96/shell-configs/commit/a89f78fbc76377fb6b4bf88bde3da4529a2a1acf))

- **git**: Ignore Claude Code research report artifacts
  ([`6294224`](https://github.com/wpfleger96/shell-configs/commit/62942244c12f9a5d7192c4075472c5def3b51f2e))

### Refactoring

- Rewrite disk-cleanup as cross-platform Python script
  ([`ce64d98`](https://github.com/wpfleger96/shell-configs/commit/ce64d9840f696fde5ec6e0146e577e8881aa7b82))


## v0.42.0 (2026-05-20)

### Bug Fixes

- Import rvm GPG keys before install instead of skipping verification
  ([#40](https://github.com/wpfleger96/shell-configs/pull/40),
  [`6e1a1e1`](https://github.com/wpfleger96/shell-configs/commit/6e1a1e1b8b14f0972774f26fabe14e9467dab308))

- Skip rvm GPG verification during install
  ([#40](https://github.com/wpfleger96/shell-configs/pull/40),
  [`6e1a1e1`](https://github.com/wpfleger96/shell-configs/commit/6e1a1e1b8b14f0972774f26fabe14e9467dab308))

### Features

- Add LanguagesComponent and fix IDE extension false positives
  ([#40](https://github.com/wpfleger96/shell-configs/pull/40),
  [`6e1a1e1`](https://github.com/wpfleger96/shell-configs/commit/6e1a1e1b8b14f0972774f26fabe14e9467dab308))


## v0.41.1 (2026-05-18)

### Bug Fixes

- Restore custom prompt after Hermit chpwd hook clobbers PS1
  ([`7c47ce1`](https://github.com/wpfleger96/shell-configs/commit/7c47ce12329a6d8691153102f4655c08143fd116))

### Chores

- **deps**: Update astral-sh/setup-uv action to v8
  ([#38](https://github.com/wpfleger96/shell-configs/pull/38),
  [`eb13977`](https://github.com/wpfleger96/shell-configs/commit/eb13977fc56420fb302148b4c8c258eb8428e299))

- **deps**: Update python Docker tag to v3.14
  ([#37](https://github.com/wpfleger96/shell-configs/pull/37),
  [`ce39222`](https://github.com/wpfleger96/shell-configs/commit/ce392226295c705b8a3bcaf26d18070931d0bead))


## v0.41.0 (2026-05-18)

### Features

- Add print_hint helper and dim background successes
  ([#35](https://github.com/wpfleger96/shell-configs/pull/35),
  [`43fbd8d`](https://github.com/wpfleger96/shell-configs/commit/43fbd8d70f516dc930e607dc9ba10b2daa943b98))

### Refactoring

- Complete display helper migration across all CLI modules
  ([#35](https://github.com/wpfleger96/shell-configs/pull/35),
  [`43fbd8d`](https://github.com/wpfleger96/shell-configs/commit/43fbd8d70f516dc930e607dc9ba10b2daa943b98))

- Complete display helper migration and golden path alignment
  ([#35](https://github.com/wpfleger96/shell-configs/pull/35),
  [`43fbd8d`](https://github.com/wpfleger96/shell-configs/commit/43fbd8d70f516dc930e607dc9ba10b2daa943b98))

- Eliminate all raw Rich markup via display helpers
  ([#35](https://github.com/wpfleger96/shell-configs/pull/35),
  [`43fbd8d`](https://github.com/wpfleger96/shell-configs/commit/43fbd8d70f516dc930e607dc9ba10b2daa943b98))

- Expand display helpers to cover all symbol patterns
  ([#35](https://github.com/wpfleger96/shell-configs/pull/35),
  [`43fbd8d`](https://github.com/wpfleger96/shell-configs/commit/43fbd8d70f516dc930e607dc9ba10b2daa943b98))

- Refine display API and fix review findings
  ([#35](https://github.com/wpfleger96/shell-configs/pull/35),
  [`43fbd8d`](https://github.com/wpfleger96/shell-configs/commit/43fbd8d70f516dc930e607dc9ba10b2daa943b98))


## v0.40.1 (2026-05-16)

### Bug Fixes

- Raise nosleep default timeout to 24 hours
  ([#36](https://github.com/wpfleger96/shell-configs/pull/36),
  [`6239033`](https://github.com/wpfleger96/shell-configs/commit/6239033dc931c7bb5d73467ebda91d8579da9de0))


## v0.40.0 (2026-05-15)

### Bug Fixes

- Address crossfire code review findings for parallel execution and CLI output
  ([#33](https://github.com/wpfleger96/shell-configs/pull/33),
  [`a185313`](https://github.com/wpfleger96/shell-configs/commit/a185313b4bbed4091f1808bb27458b802cc2dd4e))

- Normalize inter-section spacing in buffered output replay
  ([#33](https://github.com/wpfleger96/shell-configs/pull/33),
  [`a185313`](https://github.com/wpfleger96/shell-configs/commit/a185313b4bbed4091f1808bb27458b802cc2dd4e))

### Features

- Parallelize status command across components
  ([#33](https://github.com/wpfleger96/shell-configs/pull/33),
  [`a185313`](https://github.com/wpfleger96/shell-configs/commit/a185313b4bbed4091f1808bb27458b802cc2dd4e))

- Parallelize status command and standardize CLI output rendering
  ([#33](https://github.com/wpfleger96/shell-configs/pull/33),
  [`a185313`](https://github.com/wpfleger96/shell-configs/commit/a185313b4bbed4091f1808bb27458b802cc2dd4e))

### Refactoring

- Standardize CLI output rendering across all commands
  ([#33](https://github.com/wpfleger96/shell-configs/pull/33),
  [`a185313`](https://github.com/wpfleger96/shell-configs/commit/a185313b4bbed4091f1808bb27458b802cc2dd4e))


## v0.39.0 (2026-05-15)

### Features

- Add backup-resmed script for SD card data backup
  ([#34](https://github.com/wpfleger96/shell-configs/pull/34),
  [`d068d6a`](https://github.com/wpfleger96/shell-configs/commit/d068d6abaca12cac1961d6597ad05ec3d1a219c9))


## v0.38.2 (2026-05-15)

### Bug Fixes

- Add go to STUB_COMMANDS in test conftest
  ([#32](https://github.com/wpfleger96/shell-configs/pull/32),
  [`9dbda96`](https://github.com/wpfleger96/shell-configs/commit/9dbda96d735b17dfc474e0283a7d72aa62c8b7a0))

- Move pylance to vscode-only config and fix gh-infra fork installation
  ([#32](https://github.com/wpfleger96/shell-configs/pull/32),
  [`9dbda96`](https://github.com/wpfleger96/shell-configs/commit/9dbda96d735b17dfc474e0283a7d72aa62c8b7a0))


## v0.38.1 (2026-05-15)

### Bug Fixes

- Revert ci.yml to split lint/format recipe names
  ([`131a4ea`](https://github.com/wpfleger96/shell-configs/commit/131a4ea1e3ff01e567526ee577d2f11a697f36dd))


## v0.38.0 (2026-05-15)

### Bug Fixes

- Add missing lint-check/format-check Justfile recipes for CI
  ([`f2c35d1`](https://github.com/wpfleger96/shell-configs/commit/f2c35d1940727399576857d5f2201a9a9d6c5773))

### Chores

- Remove Dependabot config (migrated to Renovate)
  ([#31](https://github.com/wpfleger96/shell-configs/pull/31),
  [`3cf9b99`](https://github.com/wpfleger96/shell-configs/commit/3cf9b99a4bab19a061fdd9491b8012970bdbe7a4))

### Continuous Integration

- Sync shared files
  ([`8d502db`](https://github.com/wpfleger96/shell-configs/commit/8d502db1bb73ce351bb7b6499a0711a7d7bef163))

- Sync shared files
  ([`3cff678`](https://github.com/wpfleger96/shell-configs/commit/3cff67836c6cba248e8b79c9aa89dbabe07f81e7))

### Features

- Add Cursor Local (Windows-side) extension management on WSL
  ([`4b4eb72`](https://github.com/wpfleger96/shell-configs/commit/4b4eb72d9276a2a4415665b24a3732696866adc9))


## v0.37.1 (2026-05-14)

### Bug Fixes

- Add --script flag to transcribe shebang for uv 0.11+
  ([`0f561d4`](https://github.com/wpfleger96/shell-configs/commit/0f561d493786c9472e4928667e9ace97d9856766))


## v0.37.0 (2026-05-13)

### Bug Fixes

- Install -y should run gh auth refresh, not suppress it
  ([#30](https://github.com/wpfleger96/shell-configs/pull/30),
  [`90706b4`](https://github.com/wpfleger96/shell-configs/commit/90706b462b595f612883ab94183e1eebb6f52efd))

- Migrate GhAuthComponent to plan/apply, fix scope reporting
  ([#30](https://github.com/wpfleger96/shell-configs/pull/30),
  [`90706b4`](https://github.com/wpfleger96/shell-configs/commit/90706b462b595f612883ab94183e1eebb6f52efd))

### Features

- Add configurable gh CLI auth scope management
  ([#30](https://github.com/wpfleger96/shell-configs/pull/30),
  [`90706b4`](https://github.com/wpfleger96/shell-configs/commit/90706b462b595f612883ab94183e1eebb6f52efd))


## v0.36.5 (2026-05-13)

### Bug Fixes

- Address code review findings for parallel executor
  ([#26](https://github.com/wpfleger96/shell-configs/pull/26),
  [`74c7b10`](https://github.com/wpfleger96/shell-configs/commit/74c7b108588e583d30af22d6099443585b706ca3))

### Chores

- Remove unused Any import from context.py
  ([#26](https://github.com/wpfleger96/shell-configs/pull/26),
  [`74c7b10`](https://github.com/wpfleger96/shell-configs/commit/74c7b108588e583d30af22d6099443585b706ca3))

### Refactoring

- Add plan/apply component interface and plan dataclasses
  ([#26](https://github.com/wpfleger96/shell-configs/pull/26),
  [`74c7b10`](https://github.com/wpfleger96/shell-configs/commit/74c7b108588e583d30af22d6099443585b706ca3))

- Parallel plan/apply architecture for CLI components
  ([#26](https://github.com/wpfleger96/shell-configs/pull/26),
  [`74c7b10`](https://github.com/wpfleger96/shell-configs/commit/74c7b108588e583d30af22d6099443585b706ca3))

- Rewrite commands to use parallel plan/apply flow
  ([#26](https://github.com/wpfleger96/shell-configs/pull/26),
  [`74c7b10`](https://github.com/wpfleger96/shell-configs/commit/74c7b108588e583d30af22d6099443585b706ca3))

- Split all components into plan/apply and add parallel executor
  ([#26](https://github.com/wpfleger96/shell-configs/pull/26),
  [`74c7b10`](https://github.com/wpfleger96/shell-configs/commit/74c7b108588e583d30af22d6099443585b706ca3))

- Split ConfigsComponent into plan/apply phases
  ([#26](https://github.com/wpfleger96/shell-configs/pull/26),
  [`74c7b10`](https://github.com/wpfleger96/shell-configs/commit/74c7b108588e583d30af22d6099443585b706ca3))


## v0.36.4 (2026-05-13)

### Bug Fixes

- Add PSR build_command to sync lockfile on release
  ([#28](https://github.com/wpfleger96/shell-configs/pull/28),
  [`600bdb7`](https://github.com/wpfleger96/shell-configs/commit/600bdb7ba004821c2341140fa5322d64a49097d1))

- Delete auto-generated CLI_REFERENCE.md and remove dead links
  ([#28](https://github.com/wpfleger96/shell-configs/pull/28),
  [`600bdb7`](https://github.com/wpfleger96/shell-configs/commit/600bdb7ba004821c2341140fa5322d64a49097d1))

- Install uv in PSR Docker container before lockfile sync
  ([#29](https://github.com/wpfleger96/shell-configs/pull/29),
  [`d02f3b7`](https://github.com/wpfleger96/shell-configs/commit/d02f3b7ead70e5b0130806a859ab08901460c4d9))

### Refactoring

- Remove dead code, fix stale docs and Justfile
  ([#28](https://github.com/wpfleger96/shell-configs/pull/28),
  [`600bdb7`](https://github.com/wpfleger96/shell-configs/commit/600bdb7ba004821c2341140fa5322d64a49097d1))


## v0.36.3 (2026-05-13)

### Bug Fixes

- Temporarily switch gh-infra to personal fork
  ([#27](https://github.com/wpfleger96/shell-configs/pull/27),
  [`66d5329`](https://github.com/wpfleger96/shell-configs/commit/66d53298508b85c3bf2afe015817dc3bb1b973d9))


## v0.36.2 (2026-05-13)

### Bug Fixes

- Handle bare YAML keys in profile loader
  ([`9b6b6ed`](https://github.com/wpfleger96/shell-configs/commit/9b6b6edebc44fa8d470f8f9a467a966c2c40b5e3))


## v0.36.1 (2026-05-13)

### Bug Fixes

- Add PSR v10 changelog insertion flag and backfill missing entries
  ([#25](https://github.com/wpfleger96/shell-configs/pull/25),
  [`7c24a04`](https://github.com/wpfleger96/shell-configs/commit/7c24a048221970fcbc85317b248e6ceb40244c68))


## v0.36.0 (2026-05-13)

### Features

- **extensions**: Add `list` command, remove `export`
  ([`a1426dc`](https://github.com/wpfleger96/shell-configs/commit/a1426dc592d20aab83ae9139b5f0d5401f4df140))

No command showed individual extensions with their install status — `status` only had counts,
  `diff` only showed discrepancies, and `export` dumped raw names for one IDE with no context. The
  new `extensions list` shows a per-IDE table with every extension and its status (installed,
  missing, extra, builtin).

### Bug Fixes

- Add main/master fallback to _git_default_branch
  ([`bcff354`](https://github.com/wpfleger96/shell-configs/commit/bcff354a33d2f25e33dd277f88377607b1498844))

git symbolic-ref refs/remotes/origin/HEAD is only set at clone time and never updated — repos
  created via git init + git remote add lack it entirely. Fall back to checking for main then master
  via show-ref. Removes the now-redundant inline fallback from sync-fork.

- Claude code extension keeps getting reinstalled by CLI anyway
  ([`bd685af`](https://github.com/wpfleger96/shell-configs/commit/bd685af5be97aea0eb527203f58bd1c8ad4a5def))


## v0.35.0 (2026-05-13)

### Features

- Add VS Code Local (Windows-side) extension management on WSL
  ([`0e297ae`](https://github.com/wpfleger96/shell-configs/commit/0e297aeef758384e84092938ff70bca53b327534))

VS Code on WSL has two separate extension hosts — WSL:Ubuntu (remote) and Local (Windows-side) —
  but shell-configs only managed WSL extensions. UI-only extensions like tomoki1207.pdf and
  mathiasfrohlich.kotlin were installed into WSL where VS Code couldn't run them ("Install
  Locally").

Introduces ExtensionInvoker abstraction to support PowerShell-based CLI invocation for the
  Windows-side code.cmd from WSL. Adds VSCodeLocalShell (registered on WSL only) with a dedicated
  extensions-local.txt config. Also adds ms-vscode.powershell, ms-python.vscode-python-envs, and
  ms-python.vscode-pylance to the shared extension config.


## v0.34.2 (2026-05-11)

### Bug Fixes

- Backfill missing CHANGELOG entry for v0.34.1
  ([`b623c45`](https://github.com/wpfleger96/shell-configs/commit/b623c45b6d10b827ef7afe5ed980919e9b8bf7a1))


## v0.34.1 (2026-05-11)

### Bug Fixes

- Prevent shell_overrides["shared"] from injecting into gitconfig
  ([#23](https://github.com/wpfleger96/shell-configs/pull/23),
  [`1bfb0a5`](https://github.com/wpfleger96/shell-configs/commit/1bfb0a591d02788b95a9d98624a9b927808ea518))

get_shared_config_content() appended profile.shell_overrides["shared"]
(shell script) to all shell types including git (INI format), corrupting
~/.gitconfig and breaking all git commands. The SHELL_CONFIGS_DIR export
at line 127 already had the correct guard; the profile override block
didn't. Latent since the method was written — PR #22 was the first time
a profile defined shell_overrides["shared"], triggering it.

Also restores PSR v10 changelog generation (missing since the v9→v10
upgrade in 9cfc1ba silently dropped the now-required explicit config)
and backfills the three skipped entries (v0.33.0, v0.33.1, v0.34.0).


## v0.34.0 (2026-05-11)

### Features

- Add direnv to auto-override corporate index vars in personal repos
  ([#22](https://github.com/wpfleger96/shell-configs/pull/22),
  [`43989f5`](https://github.com/wpfleger96/shell-configs/commit/43989f5e53e3b91553fcc63b51c6f21fed2430a1))

Corporate Artifactory can't handle Metadata-Version 2.4 wheels (hatchling >= 1.27.0), breaking uv
  resolution in personal repos when UV_INDEX_URL points to Artifactory. direnv overrides these vars
  when entering ~/Development/Personal/ so uv resolves from public PyPI. The .envrc content is managed
  in work.yaml and deployed to disk on shell startup with content comparison.

### Bug Fixes

- Use explicit PyPI URLs instead of unset in .envrc
  ([`78c8de3`](https://github.com/wpfleger96/shell-configs/commit/78c8de31e1f5ef9a6307ebe55a2a315c978cdf6a))

~/.config/uv/uv.toml has index-url pointing to Artifactory. unset removes the env var but uv falls
  through to the config file, still hitting Artifactory. Explicit PyPI URLs override the config file
  since env vars beat config in uv's precedence chain.


## v0.33.1 (2026-05-11)

### Bug Fixes

- Add wsl_only package gate and harden extension CLI error handling
  ([`c89c8f3`](https://github.com/wpfleger96/shell-configs/commit/c89c8f3c5f07569d7ce1e49c894fa00eca2323ef))

get_installed_extensions() returned an empty set on CLI failure, silently passing invalid data to
  compute_diff() and causing confusing results. Changed to return None so callers can distinguish
  failure from "no extensions." Added wsl_only field to Package so WSL-specific packages (wslu) are
  gated at both get_config_for_platform() and load_packages().


## v0.33.0 (2026-05-11)

### Features

- Add declarative gh CLI extension management
  ([#21](https://github.com/wpfleger96/shell-configs/pull/21),
  [`8698abb`](https://github.com/wpfleger96/shell-configs/commit/8698abb81e441169480c2a9b8fc6778ab926ce55))

New GhExtensionsComponent reads a YAML manifest and installs missing gh CLI extensions idempotently.
  Supports version pinning via pin: field, validates extension names against owner/repo format,
  reports unmanaged extensions in diff/status, and handles missing gh CLI and subprocess timeouts
  gracefully.

### Chores

- Align CI/CD with golden path
  ([`9cfc1ba`](https://github.com/wpfleger96/shell-configs/commit/9cfc1ba4ab6643753142c816fccd62ecee15608a))

Standardize workflows to match the battle-tested pattern from ai-agent-rules: GitHub App token for
  release (replacing SSH deploy key), Dependabot with auto-merge for both uv and github-actions
  ecosystems, least-privilege permissions, and consistent job naming.

- **deps**: Bump astral-sh/setup-uv from 3 to 7
  ([#20](https://github.com/wpfleger96/shell-configs/pull/20),
  [`5184aa7`](https://github.com/wpfleger96/shell-configs/commit/5184aa797417ef141bbefb6e4bc65adddf5a63f7))

- **deps**: Bump actions/create-github-app-token from 2 to 3
  ([#19](https://github.com/wpfleger96/shell-configs/pull/19),
  [`8e3b168`](https://github.com/wpfleger96/shell-configs/commit/8e3b16877005abd3e9f6ad92a55eff1486cd8289))

- **deps**: Bump mfinelli/setup-shfmt from 3 to 4
  ([#18](https://github.com/wpfleger96/shell-configs/pull/18),
  [`7a9c2c1`](https://github.com/wpfleger96/shell-configs/commit/7a9c2c1f29cff0358bc6978fa9c37ab7b6176918))


## v0.32.2 (2026-05-08)

### Bug Fixes

- Address code review findings for INI merge and WSL fixes
  ([`5e6091b`](https://github.com/wpfleger96/shell-configs/commit/5e6091b650306a14189a2c40ca0441c8e8d07d41))

configparser.write() destroyed user comments and formatting in mimeapps.list on every install.
  Replaced with line-oriented _apply_ini_keys/_remove_ini_keys that edit only managed key lines
  in-place. Also fixed: dry-run mutating files via marker cleanup, migration path skipping sidecar
  creation, stale keys never pruned on source update, mangled diff output, unvalidated sidecar JSON,
  private manager methods exposed to helpers.py, and extension ID regex admitting non-extension
  lines.

- Resolve mypy type error in helpers.py ini_merge branch
  ([`bc55e68`](https://github.com/wpfleger96/shell-configs/commit/bc55e68357e70b3bf87dc215fa81518d61123144))

diff_ini_file returns str | None which shadowed the str-typed diff_text variable used later in the
  function. Renamed to ini_diff to avoid the type incompatibility.

- Resolve three WSL-specific bugs in extension, SSH, and INI handling
  ([`0aee4f4`](https://github.com/wpfleger96/shell-configs/commit/0aee4f4af4054d75ed240db333697ce92f6c7fda))

Extension detection used every non-empty line from --list-extensions as an extension ID. On WSL,
  remote CLIs prepend a header line that became a bogus entry. Cursor's CLI also resolved to the
  Windows executable instead of the WSL remote CLI, missing WSL-side extensions entirely.

ensure_gh_scopes() relied on gh ssh-key list exit code to verify OAuth scopes, but that command
  exits 0 even when the /user/keys endpoint returns 404 due to missing admin:public_key scope.
  upload_auth_key() also skipped uploading when it found the key data in any key type rather than
  specifically in authentication keys.

_parse_ini(strict=True) crashed on corrupted mimeapps.list files with duplicate sections — a
  regression from d3e8baf that blocked the diff and uninstall code paths.

- Use INI key merging for mimeapps.list instead of comment markers
  ([`d3e8baf`](https://github.com/wpfleger96/shell-configs/commit/d3e8baf45df1450d0ad4d6ec8f65efdda231c348))

System tools (xdg-mime, update-desktop-database) parse and rewrite mimeapps.list as INI, breaking
  the comment-based managed section markers every time. This caused the same wslview.desktop diff to
  appear on every shell-configs run.

Replace managed-section approach with configparser-based key merging that writes clean INI output
  surviving external rewrites. A sidecar file (.shell-configs-keys) tracks managed keys for clean
  uninstall. Includes one-time migration to strip corrupted markers from existing installs.

### Chores

- Remove vestigial .pre-commit-config.yaml
  ([`84b8fa8`](https://github.com/wpfleger96/shell-configs/commit/84b8fa8e90a450193711190ee5bb8b1c422b2e38))

The pre-commit Python framework config was unused — .hooks/pre-commit runs all checks via just
  directly. The framework's `pre-commit install` likely set a local core.hooksPath override to
  .git/hooks, which shadowed the global .hooks setting from shared.gitconfig and prevented the hook
  from firing.

- **deps**: Update pydantic requirement from >=2.13.3 to >=2.13.4
  ([#15](https://github.com/wpfleger96/shell-configs/pull/15),
  [`f797940`](https://github.com/wpfleger96/shell-configs/commit/f797940ec682ed3962b5892bc3492d1b613c4d43))

- **deps-dev**: Update mypy requirement from >=1.20.2 to >=2.0.0
  ([#14](https://github.com/wpfleger96/shell-configs/pull/14),
  [`ebf3b40`](https://github.com/wpfleger96/shell-configs/commit/ebf3b405c82f77ca644d8caff21e11d55d625b11))

### Refactoring

- Split monolithic cli.py into component registry package
  ([#13](https://github.com/wpfleger96/shell-configs/pull/13),
  [`161b92d`](https://github.com/wpfleger96/shell-configs/commit/161b92dfb12762ea992596991d4a4be9d6ec17f0))

Two bugs caused by "forgot to wire it up" — SSH signing and IDE extensions were both implemented as
  subcommands but missing from the install command. The monolithic install function had 10
  hand-wired sections across 360 lines; every new feature required editing install, status, and diff
  manually.

Introduces a Component base class with install/status/diff/uninstall methods and two ordered
  component lists (INSTALL_COMPONENTS, STATUS_COMPONENTS). Adding a future managed thing requires
  one class file and one list entry — install, status, diff, and uninstall pick it up automatically.

Also fixes a regression where install cancellation didn't abort remaining components
  (Component.install() now returns bool), and a profile-save bug where the active profile was always
  overwritten even without --profile flag.


## v0.32.1 (2026-05-06)

### Bug Fixes

- Parse worktree metadata from porcelain output
  ([`0cab15d`](https://github.com/wpfleger96/shell-configs/commit/0cab15ddfe8d47aca898da6478988947f234a52c))

wt list was treating trailing status tokens like "prunable" as branch names, which made external
  worktrees display incorrectly and leaked bad metadata into related helper flows. Switch to
  porcelain parsing so branch names and Git-native statuses stay accurate while cleanup remains
  scoped to managed .worktrees entries.


## v0.32.0 (2026-05-06)

### Bug Fixes

- Ignore builtin IDE extensions during sync
  ([`0d22118`](https://github.com/wpfleger96/shell-configs/commit/0d221184e2d646f5fd35e782c2a4210246712684))

VS Code bundles GitHub Copilot Chat but does not report it in code --list-extensions, which caused
  extension sync to treat it as missing and fail on a forced downgrade attempt. Treat builtin
  extensions as ignored managed entries, warn when config still lists them, and keep them out of
  exported desired extension lists.

### Features

- Add open-folder shortcut for VS Code and Cursor
  ([`60ad5de`](https://github.com/wpfleger96/shell-configs/commit/60ad5de4d2d51a5cd0e0aefae81711c6328244a0))

Add a shared Ctrl+Alt+O keybinding for Open Folder so the shortcut works consistently across macOS
  and Windows setups. This keeps the editor shortcut model aligned with the existing cross-platform
  terminal shortcuts in the managed keybindings file.


## v0.31.0 (2026-05-04)

### Bug Fixes

- Ssh-keygen stub writes dummy key files to prevent FileNotFoundError
  ([`a4b9348`](https://github.com/wpfleger96/shell-configs/commit/a4b934877157a115ee02f64351d56cc24123cae8))

The guard_subprocess fixture stubbed ssh-keygen to return success without writing files.
  generate_ssh_key() then called os.chmod() on the nonexistent key file, crashing 6 integration
  tests. The stub now honors the command's postcondition by writing dummy key + .pub files when -f
  is in the args.

### Features

- Add Kotlin extension, install extensions via `install` command, guard subprocess in tests
  ([`2caf6c6`](https://github.com/wpfleger96/shell-configs/commit/2caf6c61ac335a08cd967e9114e3fadb10079548))

Kotlin syntax highlighting (`mathiasfrohlich.Kotlin`) was identified as the safe alternative to full
  Java/Kotlin LSP extensions that caused 25+ GB memory consumption and kernel panics in the
  cash-server monorepo. Added to the shared extension list for both IDEs. Also added
  `anthropic.claude-code` to the work profile (MDM keeps reinstalling it via Settings Sync).

The `install` command previously skipped extensions entirely — configs, packages, SSH keys, and
  scripts were installed but extensions required a separate `shell-configs extensions install`. Now
  `install` handles missing extensions as part of its normal flow.

Added a subprocess guard fixture in test conftest that prevents tests from hitting real system
  commands. Shell validation commands (bash, zsh, git) pass through; known external tools (brew,
  code, cursor, ssh-keygen, etc.) get stubbed no-op results; unknown commands raise RuntimeError.
  Tests went from hanging for minutes to completing in 1.4 seconds.


## v0.30.0 (2026-05-01)

### Features

- Add 21 exclusion patterns to rsync-backup
  ([`b723413`](https://github.com/wpfleger96/shell-configs/commit/b72341339b6887cb11b7c35943f933943b8ad49c))

First real-world backup revealed missing excludes for caches, AI IDE state, and package stores
  totaling ~6 GB of unnecessary transfer. Covers pnpm/bun stores, Maven .m2, bundler cache,
  Windsurf/Codeium/ Copilot state, kubectl/minikube caches, ML model weights, and Square-internal
  tool artifacts.


## v0.29.1 (2026-04-30)

### Bug Fixes

- Prevent status flow from mutating SSH agent state
  ([`21eeb09`](https://github.com/wpfleger96/shell-configs/commit/21eeb09a9149f5251e88b7e42a7690d04be99328))

ensure_ssh_agent() unconditionally called ssh-add when the key wasn't loaded, even from
  _validate_all_steps() which is the read-only validation path. Repeated status/install invocations
  accumulated ghost keys in the macOS agent (which never evicts), eventually exceeding MaxAuthTries
  6.

Gate the ssh-add call behind auto_fix, matching _resolve_key_path's existing pattern for
  non-interactive mutation control.


## v0.29.0 (2026-04-30)

### Chores

- **deps**: Update pydantic requirement from >=2.12.5 to >=2.13.3
  ([#8](https://github.com/wpfleger96/shell-configs/pull/8),
  [`acd05fc`](https://github.com/wpfleger96/shell-configs/commit/acd05fc8404fca78877c1803f5cee77156a0ce92))

Updates the requirements on [pydantic](https://github.com/pydantic/pydantic) to permit the latest
  version. - [Release notes](https://github.com/pydantic/pydantic/releases) -
  [Changelog](https://github.com/pydantic/pydantic/blob/main/HISTORY.md) -
  [Commits](https://github.com/pydantic/pydantic/compare/v2.12.5...v2.13.3)

--- updated-dependencies: - dependency-name: pydantic dependency-version: 2.13.3

dependency-type: direct:production ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps-dev**: Update pytest requirement from >=8.4.2 to >=9.0.3
  ([#11](https://github.com/wpfleger96/shell-configs/pull/11),
  [`4b08354`](https://github.com/wpfleger96/shell-configs/commit/4b0835427431a6d18fd5f465abebe9c5b0d9ab6f))

Updates the requirements on [pytest](https://github.com/pytest-dev/pytest) to permit the latest
  version. - [Release notes](https://github.com/pytest-dev/pytest/releases) -
  [Changelog](https://github.com/pytest-dev/pytest/blob/main/CHANGELOG.rst) -
  [Commits](https://github.com/pytest-dev/pytest/compare/8.4.2...9.0.3)

--- updated-dependencies: - dependency-name: pytest dependency-version: 9.0.3

dependency-type: direct:development ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps-dev**: Update pytest-cov requirement from >=7.0.0 to >=7.1.0
  ([#9](https://github.com/wpfleger96/shell-configs/pull/9),
  [`fd8ffbd`](https://github.com/wpfleger96/shell-configs/commit/fd8ffbd05ae2ebafad0164e87bef063f06c7de59))

Updates the requirements on [pytest-cov](https://github.com/pytest-dev/pytest-cov) to permit the
  latest version. - [Changelog](https://github.com/pytest-dev/pytest-cov/blob/master/CHANGELOG.rst)
  - [Commits](https://github.com/pytest-dev/pytest-cov/compare/v7.0.0...v7.1.0)

--- updated-dependencies: - dependency-name: pytest-cov dependency-version: 7.1.0

dependency-type: direct:development ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps-dev**: Update ruff requirement from >=0.14.3 to >=0.15.12
  ([#12](https://github.com/wpfleger96/shell-configs/pull/12),
  [`3fa9e04`](https://github.com/wpfleger96/shell-configs/commit/3fa9e04b35d980d39a40309f10d23e77fb456e46))

Updates the requirements on [ruff](https://github.com/astral-sh/ruff) to permit the latest version.
  - [Release notes](https://github.com/astral-sh/ruff/releases) -
  [Changelog](https://github.com/astral-sh/ruff/blob/main/CHANGELOG.md) -
  [Commits](https://github.com/astral-sh/ruff/compare/0.14.3...0.15.12)

--- updated-dependencies: - dependency-name: ruff dependency-version: 0.15.12

dependency-type: direct:development ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps-dev**: Update setuptools requirement from >=61 to >=82.0.1
  ([#10](https://github.com/wpfleger96/shell-configs/pull/10),
  [`317d77f`](https://github.com/wpfleger96/shell-configs/commit/317d77fbadd574bf2f6e62cbcd8ed9f7d1ade00a))

Updates the requirements on [setuptools](https://github.com/pypa/setuptools) to permit the latest
  version. - [Release notes](https://github.com/pypa/setuptools/releases) -
  [Changelog](https://github.com/pypa/setuptools/blob/main/NEWS.rst) -
  [Commits](https://github.com/pypa/setuptools/compare/v61.0.0...v82.0.1)

--- updated-dependencies: - dependency-name: setuptools dependency-version: 82.0.1

dependency-type: direct:development ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

### Features

- Add rsync-backup function for standardized file backups
  ([`3528515`](https://github.com/wpfleger96/shell-configs/commit/35285155f2554fda660aa0cd1a83dfdae3116bf0))

Long rsync backup commands with 50+ exclude flags are error-prone and inconsistent across machines.
  Centralizes the exclude list and standard flags so backups between servers/laptops use the same
  filtering. All user-supplied args pass through to rsync directly.


## v0.28.0 (2026-04-29)

### Chores

- **deps**: Update click requirement from >=8.1 to >=8.3.3
  ([#7](https://github.com/wpfleger96/shell-configs/pull/7),
  [`c9068ed`](https://github.com/wpfleger96/shell-configs/commit/c9068ed411cbf54fb7ebe3020eb969a7e42ab083))

Updates the requirements on [click](https://github.com/pallets/click) to permit the latest version.
  - [Release notes](https://github.com/pallets/click/releases) -
  [Changelog](https://github.com/pallets/click/blob/main/CHANGES.rst) -
  [Commits](https://github.com/pallets/click/compare/8.1.0...8.3.3)

--- updated-dependencies: - dependency-name: click dependency-version: 8.3.3

dependency-type: direct:production ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Update packaging requirement from >=21.0 to >=26.2
  ([#3](https://github.com/wpfleger96/shell-configs/pull/3),
  [`a4a1c7e`](https://github.com/wpfleger96/shell-configs/commit/a4a1c7e77b27f9b7c763d74f582f12c99ef0c49b))

Updates the requirements on [packaging](https://github.com/pypa/packaging) to permit the latest
  version. - [Release notes](https://github.com/pypa/packaging/releases) -
  [Changelog](https://github.com/pypa/packaging/blob/main/CHANGELOG.rst) -
  [Commits](https://github.com/pypa/packaging/compare/21.0...26.2)

--- updated-dependencies: - dependency-name: packaging dependency-version: '26.2'

dependency-type: direct:production ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Update pyyaml requirement from >=6.0 to >=6.0.3
  ([#6](https://github.com/wpfleger96/shell-configs/pull/6),
  [`f0663ac`](https://github.com/wpfleger96/shell-configs/commit/f0663acc22b5318a7b2475c6c8be5305b6c850d2))

Updates the requirements on [pyyaml](https://github.com/yaml/pyyaml) to permit the latest version. -
  [Release notes](https://github.com/yaml/pyyaml/releases) -
  [Changelog](https://github.com/yaml/pyyaml/blob/6.0.3/CHANGES) -
  [Commits](https://github.com/yaml/pyyaml/compare/6.0...6.0.3)

--- updated-dependencies: - dependency-name: pyyaml dependency-version: 6.0.3

dependency-type: direct:production ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Update rich requirement from >=13.0 to >=15.0.0
  ([#4](https://github.com/wpfleger96/shell-configs/pull/4),
  [`857eb35`](https://github.com/wpfleger96/shell-configs/commit/857eb35a1c494e4d18f4d9421b7c1e96b5903b3c))

Updates the requirements on [rich](https://github.com/Textualize/rich) to permit the latest version.
  - [Release notes](https://github.com/Textualize/rich/releases) -
  [Changelog](https://github.com/Textualize/rich/blob/master/CHANGELOG.md) -
  [Commits](https://github.com/Textualize/rich/compare/v13.0.0...v15.0.0)

--- updated-dependencies: - dependency-name: rich dependency-version: 15.0.0

dependency-type: direct:production ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps-dev**: Update mypy requirement from >=1.18.2 to >=1.20.2
  ([#5](https://github.com/wpfleger96/shell-configs/pull/5),
  [`bb9a32a`](https://github.com/wpfleger96/shell-configs/commit/bb9a32a6fc3b342fabb71dccb9965095e9443a64))

Updates the requirements on [mypy](https://github.com/python/mypy) to permit the latest version. -
  [Changelog](https://github.com/python/mypy/blob/master/CHANGELOG.md) -
  [Commits](https://github.com/python/mypy/compare/v1.18.2...v1.20.2)

--- updated-dependencies: - dependency-name: mypy dependency-version: 1.20.2

dependency-type: direct:development ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

### Features

- Add IDE extension management for VSCode and Cursor
  ([`65d6d07`](https://github.com/wpfleger96/shell-configs/commit/65d6d072e655c91033ba72ef83bd42e5fe5d224f))

VSCode and Cursor extensions drift across machines with no way to reconcile. Cursor has no built-in
  Settings Sync, making external management the only option. This adds declarative extension lists
  with the same layered merge strategy used for settings.json (shared base + IDE-specific + profile
  overrides).

New `shell-configs extensions` subcommand group with status, diff, install (with --prune), and
  export commands. Extensions section integrated into `shell-configs status`. Builtin extensions
  like Cursor's anysphere.cursorpyright are excluded from diff/export to prevent config poisoning on
  re-import.


## v0.27.0 (2026-04-24)

### Features

- Package utility scripts and consolidate SSH key lifecycle
  ([#2](https://github.com/wpfleger96/shell-configs/pull/2),
  [`00820b0`](https://github.com/wpfleger96/shell-configs/commit/00820b02c3b854686fd6fe28aed42f8337de7f6b))

Scripts were only usable from a repo checkout — now they're packaged and installed to ~/.local/bin
  via convention-based discovery. Adding a new script = dropping a file in scripts/; scripts.toml
  lists the 5 platform-restricted exceptions. install/uninstall commands manage scripts alongside
  shell configs.

The SSH key lifecycle was split between shell-configs (signing only) and homelabconfigs (generation
  + auth upload). Now shell-configs owns it end-to-end via signing --fix, using GitHub fingerprint
  matching to discover the managed key instead of hardcoding ~/.ssh/id_rsa. Decision matrix: 0 keys
  → generate, 1 key → use it, fingerprint match → use match, 2+ unmatched → interactive prompt.

All subprocess calls in signing.py go through _run() which catches TimeoutExpired. ssh-add no longer
  captures output so passphrase prompts work. register_signing_key and generate_allowed_signers_file
  are idempotent. config/script/ renamed to config/lib/ to distinguish support libraries from
  distributable scripts.


## v0.26.1 (2026-04-24)

### Bug Fixes

- Terminal title persisting after Claude Code exit, add iTerm2 support
  ([`4467d78`](https://github.com/wpfleger96/shell-configs/commit/4467d78b3e514fe6bb0bd8421a0da59a1b664202))

VS Code ignores empty OSC 2 sequences because empty string is falsy in JS (microsoft/vscode#312403).
  The precmd hook now emits the shell name via OSC 0 instead, which also sets iTerm2 tab titles (OSC
  2 was window only). TERM_PROGRAM gate broadened from hardcoded allowlist to existence check.
  iTerm2 profile updated to allow title setting and disable profile name prepending.

### Refactoring

- Add github_repo to ToolSpec, remove global constant from cli
  ([`b7b605b`](https://github.com/wpfleger96/shell-configs/commit/b7b605b5f5d314e16ff29a97d3f5673a49cf5822))

check_tool_updates() hardcoded the module-level GITHUB_REPO constant instead of reading it from the
  ToolSpec it was passed, forcing cli.py to separately import and reconstruct the URL at three call
  sites. ToolSpec now carries its own github_repo field.


## v0.26.0 (2026-04-23)

### Features

- Add VS Code terminal tab title support for Claude Code sessions
  ([`a18f848`](https://github.com/wpfleger96/shell-configs/commit/a18f848cc9424e4a574f1b345aaa2c34dc488f8e))

Adds ${sequence}${separator}${process} template so OSC-set titles are visible in VS Code/Cursor
  terminal tabs. Adds _reset_terminal_title() precmd hook to clear stale titles when returning to
  the shell prompt. Companion to claude-code-status-line's opt-in OSC 2 emission feature.

### Refactoring

- Backport ai-rules bootstrap and completion improvements
  ([`a1f91ab`](https://github.com/wpfleger96/shell-configs/commit/a1f91abafddb01dc13d0821a3473a433f2fdd0aa))

shell-configs and ai-rules share the same bootstrap/completion architecture. ai-rules evolved
  several improvements that shell-configs never received; this closes the quality gap without
  extracting a shared library.

Key changes: - ToolSource enum replaces raw "pypi"/"github"/"local" strings in get_tool_source();
  LOCAL variant correctly identifies path-key receipts - make_github_install_url() replaces
  hardcoded GITHUB_REPO_URL constant; GITHUB_REPO (owner/repo) imported by updater instead of
  duplicated - get_version lambda now uses get_tool_version() instead of
  importlib.metadata.version(), which can diverge for uvx invocations - deep_merge() uses
  copy.deepcopy throughout — prevents aliasing when callers share mutable override values -
  completions: regex-based uninstall/update replaces fragile line-scanner; install_completion
  delegates to update_completion for existing blocks so users get the new command -v guard without
  reinstalling; lambda form for re.sub replacements prevents accidental backreference
  interpretation; uninstall now errors instead of silently succeeding when end marker missing


## v0.25.0 (2026-04-23)

### Features

- **transcribe**: Include timestamps in txt output
  ([`eb8fe38`](https://github.com/wpfleger96/shell-configs/commit/eb8fe38a857a36b53abe9016ad7028419852c840))

openai-whisper's WriteTXT strips timestamps, producing a wall of text with no way to locate specific
  moments. Now txt output mirrors the terminal display with right-aligned timestamps per segment,
  and the "all" format overwrites the plain txt with the timestamped version.


## v0.24.1 (2026-04-22)

### Bug Fixes

- Resolve git prompt tuning in worktree directories
  ([`74ed244`](https://github.com/wpfleger96/shell-configs/commit/74ed244f2882ce24e86756baf5dc565a5f8ac165))

In worktrees .git is a file (gitdir: pointer), not a directory, so $git_root/.git/index fails with
  "not a directory" in zsh. Use git rev-parse --git-dir which follows worktree indirection.


## v0.24.0 (2026-04-22)

### Features

- Add Codex, Gemini, and Amp CLI aliases
  ([`421b7e5`](https://github.com/wpfleger96/shell-configs/commit/421b7e529bf0f4ab54fbd5c8c654983efad80f35))

Convenience aliases for three additional coding agents, mirroring the existing Claude Code
  ccy/ccry/cccy pattern. Prefixes: cx (Codex), gm (Gemini CLI), am (Amp). Suffix semantics are
  consistent across all four agents: c = continue last, r = resume picker, f = fork, y = yolo.


## v0.23.0 (2026-04-21)

### Bug Fixes

- Auto-detect large repos for git prompt tuning
  ([`b3bf5d9`](https://github.com/wpfleger96/shell-configs/commit/b3bf5d96c5af573a6e4cf696d75bdeb47f653a3e))

The previous approach used hardcoded LARGE_REPO_PATTERNS with glob matching in a case statement, but
  zsh treats $pattern as a literal string in case expressions — the globs never matched and the
  expensive GIT_PS1_SHOW* flags were never disabled. Replaced with dynamic detection based on
  .git/index file size (>5 MB = large repo), which works correctly in both bash and zsh without
  maintaining a list of known repos.

### Features

- Add profile system for per-machine configuration
  ([`d255301`](https://github.com/wpfleger96/shell-configs/commit/d255301e967bba87170e963132f850c7dd8f7c5e))

Adds YAML-based profiles with single inheritance so configs can vary between work and personal
  laptops. The work profile adds Block CPE compliance keys to VS Code settings; the default profile
  is the clean baseline. Profiles affect shell content (appended), JSON settings (deep-merged), and
  package lists (add/remove).

Moves workbench.startupEditor into the base VS Code override layer since it applies to both
  machines. Also fixes install --dry-run to show actual diffs instead of only listing file paths.


## v0.22.1 (2026-04-08)

### Bug Fixes

- Correct VS Code terminal scrollback and font size settings
  ([`f07d719`](https://github.com/wpfleger96/shell-configs/commit/f07d7196eaf05ab77dc29c8bdf5498cb483c489e))

scrollback=0 caused xterm.js to convert mouse wheel events to cursor key sequences (no buffer to
  scroll), making the mouse wheel navigate zsh command history instead of scrolling terminal output.
  The default terminal font size on macOS is 12pt, not 14 — setting 15pt was a 25% increase that
  made the terminal text disproportionately large.

Changes scrollback to 50000 (VS Code has no unlimited option) and removes the explicit fontSize to
  inherit the macOS default. Keeps Monaco as fontFamily since it renders correctly at the default
  size.


## v0.22.0 (2026-04-08)

### Features

- Add iTerm2 configuration management
  ([`0d2a601`](https://github.com/wpfleger96/shell-configs/commit/0d2a60186361b998f06979ecc91044316b2f6d8c))

iTerm2 is macOS-only and uses two distinct config surfaces that can't be managed with the existing
  file-copy pattern alone. Dynamic Profiles (JSON files auto-watched by iTerm2) handle profile
  settings, while global preferences require `defaults import` into the macOS preferences domain.
  This introduces a PreferencesFile dataclass and ConfigManager methods for the defaults-based
  workflow, extending the Shell ABC without changing existing handlers.

Manages only non-default settings (verified against factory DefaultBookmark.plist): font size,
  terminal type, unlimited scrollback, sync title, keyboard navigation shortcuts, and global key
  bindings including Cmd+Shift+T (duplicate tab) and Cmd+Shift+N (duplicate window). Adds backup_dir
  to AdditionalFile so DynamicProfiles backups go to ~/.config/shell-configs/backups/iterm2/ instead
  of polluting the watched directory. The preferences install/uninstall methods accept app_name for
  running-app detection, validate null JSON values before plistlib, and check defaults delete return
  codes.

- Add iTerm2 shell integration and terminal parity settings
  ([`0eda4ae`](https://github.com/wpfleger96/shell-configs/commit/0eda4ae1f95790ce5d8b0561e1c6c7eaf7396401))

Vendor iTerm2 shell integration scripts for zsh and bash, sourced via the macOS platform overlay.
  Shell integration adds prompt marks for Cmd+Shift+Up/Down navigation between commands, automatic
  per-command status indicators, and Cmd+click file opening. Scripts are placed in shell-specific
  directories (config/zsh/, config/bash/) to avoid cross-pollution between shell handlers.

Add integrated terminal settings to the shared editor config for VS Code/Cursor parity with iTerm2:
  Monaco 15pt font, unlimited scrollback, block cursor without blinking, and macOptionIsMeta for
  Opt+arrow word navigation.


## v0.21.1 (2026-04-02)

### Bug Fixes

- Run post-upgrade install in new process to avoid stale code
  ([`c9f8b2e`](https://github.com/wpfleger96/shell-configs/commit/c9f8b2e55afe0ef5304facf27dbcaf9a727c9375))

The upgrade command called ctx.invoke(install) in the same Python process after installing the new
  package. Python's module cache meant the old version's code ran against the new version's config
  files, which caused destructive behavior when config file formats changed (e.g., editor settings
  consolidation wrote {} as VSCode settings).

Spawning shell-configs as a subprocess ensures fresh module imports from the upgraded package on
  disk.


## v0.21.0 (2026-04-02)

### Features

- Consolidate editor settings and add liveshare security config
  ([`bf7099f`](https://github.com/wpfleger96/shell-configs/commit/bf7099f9994220be5bbf4bb06ef69fe5237f6ac2))

VSCode and Cursor settings were ~75% duplicated, causing config drift when shared settings were
  added to one editor but not the other. The liveshare security settings (guest approval, anonymous
  rejection, external file sharing) were also getting wiped on each install because the mechanism is
  full-file replacement.

Introduces a shared editor base config (config/editor/) with a shallow JSON merge at install time:
  final settings = shared base + editor overrides. Refactors install_additional_file to delegate to
  a new content-based install method, eliminating ~60 lines of duplication.


## v0.20.0 (2026-04-02)

### Features

- Add claude code experimental features
  ([`eb0cbc1`](https://github.com/wpfleger96/shell-configs/commit/eb0cbc1c48d1fe047a13e3e15adb81cbdbdbb579))


## v0.19.0 (2026-03-26)

### Features

- Disable expensive git prompt options in large repos
  ([`972ed40`](https://github.com/wpfleger96/shell-configs/commit/972ed4069643f7bcb1994d9032a0e2ab3d1d2741))

__git_ps1 with SHOWDIRTYSTATE, SHOWSTASHSTATE, SHOWUNTRACKEDFILES, and SHOWUPSTREAM runs four git
  operations per prompt render. In monorepos like cash-server (118k+ files) this adds ~640ms+ per
  prompt even with fsmonitor enabled. Configurable LARGE_REPO_PATTERNS array disables these flags
  via chpwd/PROMPT_COMMAND hooks when inside matched paths.


## v0.18.0 (2026-03-17)

### Features

- Port over work laptop scripts
  ([`541c9cc`](https://github.com/wpfleger96/shell-configs/commit/541c9cc283c2be257531cb454ba33d8bc46ae87c))


## v0.17.1 (2026-03-10)

### Bug Fixes

- Check current branch's remote tracking ref after checking default branch to ensure
  --force-with-lease has accurate info for subsequent pushes
  ([`445f935`](https://github.com/wpfleger96/shell-configs/commit/445f935645764f7d3c62f5f997e5f59eb6f5a01c))


## v0.17.0 (2026-03-07)

### Features

- Add VS Code editor support
  ([`e35c722`](https://github.com/wpfleger96/shell-configs/commit/e35c72210f85b1088ef1852eb3220ab57b843b34))


## v0.16.2 (2026-03-06)

### Bug Fixes

- Set correct upstream tracking in _wt_add for new branches
  ([`b71fb89`](https://github.com/wpfleger96/shell-configs/commit/b71fb8972b7228b72ef193bc0eb92f42e2c6ece9))


## v0.16.1 (2026-03-01)

### Bug Fixes

- Installs on fresh WSL machine
  ([`d113404`](https://github.com/wpfleger96/shell-configs/commit/d1134045e87efce2f50d01331d62e47988bd7204))


## v0.16.0 (2026-02-28)

### Features

- Runlog function
  ([`c5dd9c3`](https://github.com/wpfleger96/shell-configs/commit/c5dd9c3f19dbf1557f62be1f413bbe525e235459))


## v0.15.0 (2026-02-27)

### Features

- Nosleep function
  ([`b404f6a`](https://github.com/wpfleger96/shell-configs/commit/b404f6a7ef793df6191e5b4ffdf9b2bc1bb69444))


## v0.14.0 (2026-02-25)

### Features

- Add gpuf alias
  ([`16b5e83`](https://github.com/wpfleger96/shell-configs/commit/16b5e83e64aa356f956cc01f3e88c8bed245f326))


## v0.13.2 (2026-02-24)

### Bug Fixes

- Resolve main repo root from inside worktrees
  ([`4032ecd`](https://github.com/wpfleger96/shell-configs/commit/4032ecdf67b4ba6c96a619703e37538062ec44b1))


## v0.13.1 (2026-02-23)

### Bug Fixes

- Wt cd forward/backward
  ([`ff6970a`](https://github.com/wpfleger96/shell-configs/commit/ff6970a4c5c49972d2a7faf01c4863dce533b32d))


## v0.13.0 (2026-02-23)

### Features

- Make gpr/gpm auto-reset stale branches
  ([`5416efc`](https://github.com/wpfleger96/shell-configs/commit/5416efc866948b17df1ccc182062e3b32c9bf36c))

Rebasing a branch whose commits are already on main (squash-merged or otherwise superseded) causes
  spurious conflicts with no real fix. Revives the detection logic from the old pull_rebase_master
  script: if the branch diverges from main but has no actual file differences, reset to origin/main
  instead of rebasing.

Also handles re-running gpr during a failed rebase — aborts the in-progress state before detection
  runs.


## v0.12.4 (2026-02-12)

### Bug Fixes

- Cc aliases
  ([`7e0f0e8`](https://github.com/wpfleger96/shell-configs/commit/7e0f0e8877e5ca1e6f66e90bbbc2911f43423cff))


## v0.12.3 (2026-02-11)

### Bug Fixes

- Add pull/rebase helper aliases
  ([`ef0fa98`](https://github.com/wpfleger96/shell-configs/commit/ef0fa984d20311fbe3d2559d76615f8ac2e7a7ea))


## v0.12.2 (2026-02-04)

### Bug Fixes

- Ignore local/repo-level Claude Code configs
  ([`246fbb2`](https://github.com/wpfleger96/shell-configs/commit/246fbb25a205fcc7b321415b974c0e2ea5aec54f))


## v0.12.1 (2026-02-03)

### Bug Fixes

- Worktree pruning should also detect squash/rebase merged worktree branches
  ([`2a21103`](https://github.com/wpfleger96/shell-configs/commit/2a211039032dbd6ef8d3f2f0c5c82a663d8256ba))


## v0.12.0 (2026-02-03)

### Documentation

- Add automated full CLI reference docs
  ([`da99f00`](https://github.com/wpfleger96/shell-configs/commit/da99f002a6e140167b38289da65acd7715405734))

### Features

- Add shell aliases for difit local git diff viewing
  ([`42b360f`](https://github.com/wpfleger96/shell-configs/commit/42b360f96481231038ad493df94112265dc44790))


## v0.11.0 (2026-01-23)

### Features

- Gchp alias
  ([`310403c`](https://github.com/wpfleger96/shell-configs/commit/310403c15deb0e4bcef4689bfc9f7f3510e1f14e))


## v0.10.15 (2026-01-22)

### Bug Fixes

- Standardize --yes vs --force flags
  ([`0548540`](https://github.com/wpfleger96/shell-configs/commit/0548540df9dc9e99406da935423fe0bba82d2e52))


## v0.10.14 (2026-01-22)

### Bug Fixes

- Autoload SSH key for git commit signing in WSL
  ([`550ef51`](https://github.com/wpfleger96/shell-configs/commit/550ef511fce37d3a767095ca4875871d3e3ef8fd))


## v0.10.13 (2026-01-21)

### Bug Fixes

- Add unified diff aliases for deleted/added files
  ([`d79851c`](https://github.com/wpfleger96/shell-configs/commit/d79851ca507bb3df7c82ede898c5d04a1997311c))


## v0.10.12 (2026-01-20)

### Bug Fixes

- Remove auto background update feature since it's causing bugs
  ([`0b55f1a`](https://github.com/wpfleger96/shell-configs/commit/0b55f1abad1d7fc6db978d2a8bf7869a0cdb054d))

- Show changelogs during upgrade
  ([`2460396`](https://github.com/wpfleger96/shell-configs/commit/2460396adf303f8619f16b4331f64880ec0afe36))

- Tweak git log aliases
  ([`674834b`](https://github.com/wpfleger96/shell-configs/commit/674834b20b294498f1bfe3dbdae17c82f5ec7840))

### Chores

- Docs
  ([`5e169f6`](https://github.com/wpfleger96/shell-configs/commit/5e169f6d36788956353ed6a7b576ae4eaa21a77a))


## v0.10.11 (2026-01-19)

### Bug Fixes

- Auto clean up old backup files
  ([`a8bb7fa`](https://github.com/wpfleger96/shell-configs/commit/a8bb7faebbd51d49830a3cab88673bea92f90d34))


## v0.10.10 (2026-01-18)

### Bug Fixes

- Dont backup/overwrite files unnecessaily and show diffs before backup
  ([`1e1dfde`](https://github.com/wpfleger96/shell-configs/commit/1e1dfdebc67809ee96c1a9d27bbbe65442dbfc0f))


## v0.10.9 (2026-01-18)

### Bug Fixes

- Cursor test isolation issue on WSL
  ([`03a430d`](https://github.com/wpfleger96/shell-configs/commit/03a430db8be87e6af4a282f756867bc7762d6beb))

- Remove duplicates
  ([`bc2a4df`](https://github.com/wpfleger96/shell-configs/commit/bc2a4df8e34cf5783fdd2833e8e74bc47df3c55d))


## v0.10.8 (2026-01-18)

### Bug Fixes

- Lazyify imports for completion performance
  ([`b24462c`](https://github.com/wpfleger96/shell-configs/commit/b24462c931d85f8b1147c25e0818935e92dd8097))


## v0.10.7 (2026-01-18)

### Bug Fixes

- Dont overwrite/update files unnecessarily
  ([`880d4cb`](https://github.com/wpfleger96/shell-configs/commit/880d4cbcf238dc392a4064ea35b53a6836486bb6))

- Give SSH keys unique names
  ([`caa63b3`](https://github.com/wpfleger96/shell-configs/commit/caa63b3ee5565555ac160a21f3e5bba0f1ce45b4))


## v0.10.6 (2026-01-18)

### Bug Fixes

- Duplicate error message
  ([`2687e59`](https://github.com/wpfleger96/shell-configs/commit/2687e59505e2ddd47ac5e4654ee5abdc45b74ea9))


## v0.10.5 (2026-01-12)

### Bug Fixes

- Cc alias
  ([`3155530`](https://github.com/wpfleger96/shell-configs/commit/31555300b0a7c32cea6cbf23c073705a15726382))


## v0.10.4 (2026-01-09)

### Bug Fixes

- Uvr alias
  ([`1d2338d`](https://github.com/wpfleger96/shell-configs/commit/1d2338dd191153d51e0b6488c519c2983bd57bc0))

### Chores

- Docs
  ([`3cc899c`](https://github.com/wpfleger96/shell-configs/commit/3cc899c3c1616657a36d392ff543cb0052e196b6))


## v0.10.3 (2026-01-09)

### Bug Fixes

- Google chrome alias on mac
  ([`2ec170c`](https://github.com/wpfleger96/shell-configs/commit/2ec170c72d488c0423991d34d8bd90b8b0cc2748))


## v0.10.2 (2026-01-09)

### Bug Fixes

- Use gh api for key registration for compatibility
  ([`a6f9e67`](https://github.com/wpfleger96/shell-configs/commit/a6f9e67b6a45d01f753a5dcfb2681de6ef7e0e4c))


## v0.10.1 (2026-01-09)

### Bug Fixes

- Git-delta install on WSL
  ([`46fba81`](https://github.com/wpfleger96/shell-configs/commit/46fba81028c96fdb3c2254bf1eb20d1b5c4a4c67))

- Wsl compatibility
  ([`2d26aa3`](https://github.com/wpfleger96/shell-configs/commit/2d26aa37e725ab9f25b72f32f281279f19786dc7))


## v0.10.0 (2026-01-08)

### Features

- Add corp SSL fix helper for Ruby scripts
  ([`628197c`](https://github.com/wpfleger96/shell-configs/commit/628197c0a2b63ba595641dd7e20a06b2df3f2163))


## v0.9.0 (2026-01-08)

### Features

- Consolidate git configs and add SSH commit signing automation
  ([`901ecdc`](https://github.com/wpfleger96/shell-configs/commit/901ecdc2330464080137ed46d417db2e8ba0fc20))


## v0.8.0 (2026-01-06)

### Features

- Claude code aliases
  ([`22458de`](https://github.com/wpfleger96/shell-configs/commit/22458dec8e9f86659b30c070ea2caafcd011ede1))


## v0.7.1 (2025-12-24)

### Bug Fixes

- Sync-fork should respect default branch
  ([`cdd8ae2`](https://github.com/wpfleger96/shell-configs/commit/cdd8ae27dcf2e06e765596e140e02130264f1ca8))


## v0.7.0 (2025-12-22)

### Features

- Add grename git alias
  ([`1147aa7`](https://github.com/wpfleger96/shell-configs/commit/1147aa747bc98c591778485506122fe333dc4925))


## v0.6.0 (2025-12-20)

### Features

- Add cursor configs ported from ai-rules
  ([`013fc84`](https://github.com/wpfleger96/shell-configs/commit/013fc8491ab282a155df71851afb9d82bf7f9ac1))

### Refactoring

- Add platform autodetection module with per-env resolved config
  ([`efcc953`](https://github.com/wpfleger96/shell-configs/commit/efcc9534b9ad4c7f0ea5e08f4afad94fead1c82f))


## v0.5.0 (2025-12-19)

### Features

- Add package management support with platform-dependent auto install
  ([`1613719`](https://github.com/wpfleger96/shell-configs/commit/16137198dbbac5ee0d67b89be2f7ac1c12f4f610))


## v0.4.8 (2025-12-19)

### Bug Fixes

- Dont instantly prune just-created worktrees, and denote both orphans and pruneable worktrees in
  list output
  ([`bde3b09`](https://github.com/wpfleger96/shell-configs/commit/bde3b090e380a5f4f3762f08dc668b83cb29b92e))


## v0.4.7 (2025-12-18)

### Bug Fixes

- Add completions status command
  ([`bffa83c`](https://github.com/wpfleger96/shell-configs/commit/bffa83ca0d6b93e8d45e271372bc8ba481effdce))


## v0.4.6 (2025-12-18)

### Bug Fixes

- Expose completions functionality in CLI and cleanup dead/duplicated code
  ([`07f3532`](https://github.com/wpfleger96/shell-configs/commit/07f35323228204389f4c4afae21d8fc5169f1525))

### Chores

- Docs
  ([`0bd2265`](https://github.com/wpfleger96/shell-configs/commit/0bd2265c4d0d5a6012d1e837d317f8d0729bdc9f))

- More docs and cleanup
  ([`c7163d5`](https://github.com/wpfleger96/shell-configs/commit/c7163d565cbec8a20526b5e450878af5265ef881))


## v0.4.5 (2025-12-18)

### Bug Fixes

- Remove unneccessary hook
  ([`6349bed`](https://github.com/wpfleger96/shell-configs/commit/6349bed937556a8c1df17910af3863322af8e42b))


## v0.4.4 (2025-12-18)

### Bug Fixes

- Copying ideas from ai-rules (add info command and setup should upgrade)
  ([`ffbe028`](https://github.com/wpfleger96/shell-configs/commit/ffbe0286b5b563b71b64834099c4098ef40e7e7d))


## v0.4.3 (2025-12-18)

### Bug Fixes

- More git aliases
  ([`36165b4`](https://github.com/wpfleger96/shell-configs/commit/36165b4480ecec939bce8b376ece89d5c70db955))


## v0.4.2 (2025-12-11)

### Bug Fixes

- Cant query public API for private repo
  ([`dfd1d4f`](https://github.com/wpfleger96/shell-configs/commit/dfd1d4fea4749d1805638db451df6ad6583db37d))


## v0.4.1 (2025-12-11)

### Bug Fixes

- Remove auto fetch
  ([`beeb310`](https://github.com/wpfleger96/shell-configs/commit/beeb3101c770cdd1038bfef5da0d9db452afdd88))

### Chores

- Docs
  ([`406a5fb`](https://github.com/wpfleger96/shell-configs/commit/406a5fba773289934ea5b6ec40c09b3300ab86d9))


## v0.4.0 (2025-12-10)

### Features

- Make package private and only support github install
  ([`507c321`](https://github.com/wpfleger96/shell-configs/commit/507c32135b6916d8e4964e00e810736824153aa8))


## v0.3.5 (2025-12-10)

### Bug Fixes

- Add pypi helper env var
  ([`76397fc`](https://github.com/wpfleger96/shell-configs/commit/76397fcf8d7c2ba1120365da0f5c647bdc394448))


## v0.3.4 (2025-12-10)

### Bug Fixes

- Merged branches not getting pruned
  ([`bf4931d`](https://github.com/wpfleger96/shell-configs/commit/bf4931dc3f0b02ec3eefc564c146ee5ba7cdcaa3))


## v0.3.3 (2025-12-10)

### Bug Fixes

- Auto install after update
  ([`7152500`](https://github.com/wpfleger96/shell-configs/commit/7152500cb7ff514199d95637e03986651ae20ddd))


## v0.3.2 (2025-12-10)

### Bug Fixes

- Git command confusion
  ([`bfb3b60`](https://github.com/wpfleger96/shell-configs/commit/bfb3b60cbbcdee189fc471d1c2780db1a4a511a4))


## v0.3.1 (2025-12-10)

### Bug Fixes

- Sanitize dir names
  ([`8810a0d`](https://github.com/wpfleger96/shell-configs/commit/8810a0dbde9a52dd3f5d37daedcf66b6aaebfd35))


## v0.3.0 (2025-12-08)

### Chores

- Add AGENTS.md
  ([`5fc0825`](https://github.com/wpfleger96/shell-configs/commit/5fc08258d74bb6944862b7ffd6e283fb97da4e1b))

### Features

- Auto fetch git remote after cd into local repo dir
  ([`a8987e8`](https://github.com/wpfleger96/shell-configs/commit/a8987e80423e0cf175cb83e2367b8dc274d0af12))


## v0.2.0 (2025-12-05)

### Features

- Add setup command to streamline package based install and auto install completions
  ([`70548bc`](https://github.com/wpfleger96/shell-configs/commit/70548bcd2584491d44b7dd67a9c693840981f92e))


## v0.1.0 (2025-12-05)

### Features

- Add release/publish workflows and support package install
  ([`07a3c1d`](https://github.com/wpfleger96/shell-configs/commit/07a3c1dcf4fedef9821dbedd061bc580b296fc9e))
