# shellcheck disable=SC2207 # COMPREPLY=($(compgen ...)) is the canonical bash completion pattern
# Tab completions for shell-configs managed scripts and helpers.
# Sourced from bashrc; keep flags in sync with each script's CLI.

### wt (worktree helper) ###
_wt_completion() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD - 1]}"

    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=($(compgen -W "add rm ls list cd prune orphans help" -- "$cur"))
    elif [[ ${COMP_CWORD} -eq 2 ]]; then
        case "$prev" in
        add)
            local branches=$(git branch -r 2>/dev/null | sed 's/origin\///' | grep -v HEAD)
            COMPREPLY=($(compgen -W "$branches" -- "$cur"))
            ;;
        rm | cd)
            local worktrees=$(git worktree list 2>/dev/null | awk 'NR>1 {print $NF}' | tr -d '[]')
            COMPREPLY=($(compgen -W "$worktrees" -- "$cur"))
            ;;
        esac
    elif [[ ${COMP_CWORD} -ge 3 ]]; then
        local cmd="${COMP_WORDS[1]}"
        case "$cmd" in
        rm)
            COMPREPLY=($(compgen -W "--force -f" -- "$cur"))
            ;;
        prune)
            COMPREPLY=($(compgen -W "--force -f --orphans -o" -- "$cur"))
            ;;
        esac
    fi
}
complete -F _wt_completion wt

### disk-cleanup ###
_disk_cleanup_completion() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD - 1]}"

    case "$prev" in
    --dev-dir | --scan-dir | --high-risk-dir)
        COMPREPLY=($(compgen -d -- "$cur"))
        return
        ;;
    --workers | --cache-ttl | --discover-top | --discover-min-size | --stale-days)
        return
        ;;
    esac

    if [[ "$cur" == -* ]]; then
        COMPREPLY=($(compgen -W "-y --yes --dev-dir --no-color --workers --cache-ttl --no-cache --skip-discover --scan-dir --discover-top --discover-min-size --stale-days --high-risk-dir" -- "$cur"))
    else
        local has_subcmd=false
        for ((i = 1; i < COMP_CWORD; i++)); do
            case "${COMP_WORDS[$i]}" in
            check | fix | interactive)
                has_subcmd=true
                break
                ;;
            esac
        done
        if [[ "$has_subcmd" == false ]]; then
            COMPREPLY=($(compgen -W "check fix interactive" -- "$cur"))
        fi
    fi
}
complete -F _disk_cleanup_completion disk-cleanup

### transcribe ###
_transcribe_completion() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD - 1]}"

    case "$prev" in
    --output-format)
        COMPREPLY=($(compgen -W "txt vtt srt tsv json all" -- "$cur"))
        return
        ;;
    --output-dir)
        COMPREPLY=($(compgen -d -- "$cur"))
        return
        ;;
    --model | --language | --set)
        return
        ;;
    esac

    if [[ "$cur" == -* ]]; then
        COMPREPLY=($(compgen -W "--model --output-format --output-dir --language --set" -- "$cur"))
    else
        COMPREPLY=($(compgen -f -- "$cur"))
    fi
}
complete -F _transcribe_completion transcribe

### db-helper ###
_db_helper_completion() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD - 1]}"
    local subcommands="status migrate-to history generate-migrations backup list-backups restore help"
    local common_flags="--dry-run --yes -y --help -h"

    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=($(compgen -W "$subcommands $common_flags" -- "$cur"))
        return
    fi

    local cmd=""
    for ((i = 1; i < COMP_CWORD; i++)); do
        local word="${COMP_WORDS[$i]}"
        if [[ "$word" != -* ]]; then
            cmd="$word"
            break
        fi
    done

    case "$cmd" in
    restore)
        if [[ "$cur" == -* ]]; then
            COMPREPLY=($(compgen -W "$common_flags" -- "$cur"))
        else
            local backup_dir="${HOME}/.local/share/goose/goose-db-backups"
            if [[ -d "$backup_dir" ]]; then
                COMPREPLY=($(compgen -f -- "${backup_dir}/${cur}"))
            fi
        fi
        ;;
    generate-migrations)
        if [[ "$cur" == -* ]]; then
            COMPREPLY=($(compgen -W "$common_flags --clean" -- "$cur"))
        fi
        ;;
    migrate-to)
        if [[ "$cur" == -* ]]; then
            COMPREPLY=($(compgen -W "$common_flags" -- "$cur"))
        fi
        ;;
    *)
        if [[ "$cur" == -* ]]; then
            COMPREPLY=($(compgen -W "$common_flags" -- "$cur"))
        fi
        ;;
    esac
}
complete -F _db_helper_completion db-helper

### backup-resmed ###
_backup_resmed_completion() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD - 1]}"

    case "$prev" in
    --source | --dest)
        COMPREPLY=($(compgen -d -- "$cur"))
        return
        ;;
    esac

    COMPREPLY=($(compgen -W "--source --dest --dry-run -h --help" -- "$cur"))
}
complete -F _backup_resmed_completion backup-resmed
