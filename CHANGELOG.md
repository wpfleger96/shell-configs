# CHANGELOG


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
