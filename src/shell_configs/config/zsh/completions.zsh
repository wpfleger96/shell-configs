# shellcheck shell=bash disable=SC2034,SC2046,SC2086,SC2128,SC2154 # zsh file; shellcheck doesn't understand zsh builtins
# Tab completions for shell-configs managed scripts and helpers.
# Sourced from zshrc after compinit; keep flags in sync with each script's CLI.

### wt (worktree helper) ###
_wt() {
    local -a subcmds
    subcmds=('add:Create a new worktree' 'rm:Remove a worktree'
        'ls:List worktrees' 'list:List worktrees'
        'cd:Navigate to worktree' 'prune:Remove merged worktrees'
        'orphans:Find stale worktrees' 'help:Show help')

    if ((CURRENT == 2)); then
        _describe 'command' subcmds
    elif ((CURRENT == 3)); then
        case "${words[2]}" in
        add)
            _values 'branches' $(git branch -r 2>/dev/null | sed 's/origin\///' | grep -v HEAD)
            ;;
        rm | cd)
            _values 'worktrees' $(git worktree list 2>/dev/null | {
                skip=1
                while IFS= read -r line; do
                    [[ $skip -eq 1 ]] && {
                        skip=0
                        continue
                    }
                    b="${line##* }"
                    b="${b#\[}"
                    b="${b%\]}"
                    echo "$b"
                done
            })
            ;;
        esac
    elif ((CURRENT >= 4)); then
        case "${words[2]}" in
        rm)
            _arguments '(-f --force)'{-f,--force}'[Force removal of worktree]'
            ;;
        prune)
            _arguments \
                '(-f --force)'{-f,--force}'[Force removal without confirmation]' \
                '(-o --orphans)'{-o,--orphans}'[Include stale/orphaned worktrees]'
            ;;
        esac
    fi
}
compdef _wt wt

### disk-cleanup ###
_disk_cleanup() {
    _arguments \
        '1:command:((check\:"Report disk usage" fix\:"Clean all tiers" interactive\:"Select items to clean (default)"))' \
        '(-y --yes)'{-y,--yes}'[Skip confirmation prompts]' \
        '--dev-dir[Development directory to scan]:directory:_files -/' \
        '--no-color[Disable colored output]' \
        '--workers[Parallel thread count for size computation]:count:' \
        '--cache-ttl[Cache TTL for du results in seconds]:seconds:' \
        '--no-cache[Bypass size cache and force fresh du scan]' \
        '--skip-discover[Skip discovery scan]' \
        '*--scan-dir[Root to scan for large files (repeatable)]:directory:_files -/' \
        '--discover-top[Max items per category from discovery]:count:' \
        '--discover-min-size[Min item size for discovery (e.g. 100M, 1G)]:size:' \
        '--stale-days[Days before an item is flagged as stale]:days:' \
        '*--high-risk-dir[Directory flagged for staleness (repeatable)]:directory:_files -/'
}
compdef _disk_cleanup disk-cleanup

### transcribe ###
_transcribe() {
    _arguments \
        '*:audio/video file:_files' \
        '--model[Model name (default\: turbo)]:model:' \
        '--output-format[Output format]:format:(txt vtt srt tsv json all)' \
        '--output-dir[Output directory]:directory:_files -/' \
        '--language[Language code (auto-detect if omitted)]:language:' \
        '*--set[Pass options to model.transcribe() as KEY=VALUE]:override:'
}
compdef _transcribe transcribe

### db-helper ###
_db_helper() {
    local -a subcommands common_flags
    subcommands=(
        'status:Show current database schema version and statistics'
        'migrate-to:Migrate database to a specific schema version'
        'history:Show all available migrations'
        'generate-migrations:Auto-generate migration files from Rust source'
        'backup:Create a manual backup of the current database'
        'list-backups:Show all available backups'
        'restore:Restore database from a backup file'
        'help:Show help message'
    )
    common_flags=(
        '--dry-run[Preview changes without modifying the database]'
        '(-y --yes)'{-y,--yes}'[Skip confirmation prompts]'
        '(-h --help)'{-h,--help}'[Show help message]'
    )

    if ((CURRENT == 2)); then
        _describe 'command' subcommands
    elif ((CURRENT >= 3)); then
        case "${words[2]}" in
        restore)
            _arguments $common_flags ':backup file:_files -W ~/.local/share/goose/goose-db-backups'
            ;;
        migrate-to)
            _arguments $common_flags ':version:'
            ;;
        generate-migrations)
            _arguments $common_flags '--clean[Remove all existing migrations before regenerating]'
            ;;
        *)
            _arguments $common_flags
            ;;
        esac
    fi
}
compdef _db_helper db-helper

### backup-resmed ###
_backup_resmed() {
    _arguments \
        '--source[Path to SD card root]:directory:_files -/' \
        '--dest[Path to backup destination]:directory:_files -/' \
        '--dry-run[Show what would be copied without copying]' \
        '(-h --help)'{-h,--help}'[Show this help message]'
}
compdef _backup_resmed backup-resmed
