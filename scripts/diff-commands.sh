#!/bin/bash
# diff-commands.sh - Compare active commands against upstream course references
#
# Usage: ./scripts/diff-commands.sh [command-name]
#   Without arguments: shows summary of all differences
#   With argument: shows full diff for that command (e.g., ./scripts/diff-commands.sh plan-feature)

UPSTREAM=".agents/reference/upstream-commands"
ACTIVE=".claude/commands"

# Color output (if terminal supports it)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# Command mappings (parallel arrays for bash 3 compatibility)
UPSTREAM_PATHS=(
    "core_piv_loop/plan-feature.md"
    "core_piv_loop/execute.md"
    "core_piv_loop/prime.md"
    "core_piv_loop/prime-tools.md"
    "validation/validate.md"
    "commit.md"
    "init-project.md"
)

ACTIVE_NAMES=(
    "plan-feature.md"
    "execute.md"
    "prime.md"
    "prime-tools.md"
    "validate.md"
    "commit.md"
    "init-project.md"
)

# If a specific command was requested
if [ -n "$1" ]; then
    cmd_name="$1"
    # Add .md if not present
    case "$cmd_name" in
        *.md) ;;
        *) cmd_name="${cmd_name}.md" ;;
    esac

    # Find the upstream path for this command
    found=false
    for i in "${!ACTIVE_NAMES[@]}"; do
        if [ "${ACTIVE_NAMES[$i]}" = "$cmd_name" ]; then
            upstream_path="${UPSTREAM_PATHS[$i]}"
            if [ -f "$UPSTREAM/$upstream_path" ] && [ -f "$ACTIVE/$cmd_name" ]; then
                printf "${BLUE}=== Diff: $cmd_name ===${NC}\n"
                printf "${YELLOW}Upstream: $UPSTREAM/$upstream_path${NC}\n"
                printf "${YELLOW}Active:   $ACTIVE/$cmd_name${NC}\n"
                echo ""
                diff --color=auto -u "$UPSTREAM/$upstream_path" "$ACTIVE/$cmd_name" || true
                found=true
            fi
            break
        fi
    done

    if [ "$found" = false ]; then
        printf "${RED}Command '$1' not found in mapping or files missing${NC}\n"
        exit 1
    fi
    exit 0
fi

# Summary mode - compare all commands
printf "${BLUE}Command Drift Summary${NC}\n"
printf "${BLUE}=====================${NC}\n"
echo ""

identical_count=0
different_count=0
missing_count=0

for i in "${!UPSTREAM_PATHS[@]}"; do
    upstream_path="${UPSTREAM_PATHS[$i]}"
    active_name="${ACTIVE_NAMES[$i]}"
    upstream_file="$UPSTREAM/$upstream_path"
    active_file="$ACTIVE/$active_name"

    # Extract just the command name for display
    display_name="${active_name%.md}"

    if [ ! -f "$upstream_file" ]; then
        printf "${RED}[MISSING UPSTREAM]${NC} $display_name\n"
        missing_count=$((missing_count + 1))
    elif [ ! -f "$active_file" ]; then
        printf "${YELLOW}[NOT ADOPTED]${NC} $display_name (available in upstream)\n"
        missing_count=$((missing_count + 1))
    elif diff -q "$upstream_file" "$active_file" > /dev/null 2>&1; then
        printf "${GREEN}[IDENTICAL]${NC} $display_name\n"
        identical_count=$((identical_count + 1))
    else
        # Count lines changed
        changes=$(diff "$upstream_file" "$active_file" | grep -c '^[<>]' || echo "0")
        printf "${YELLOW}[CUSTOMIZED]${NC} $display_name (~$changes lines different)\n"
        different_count=$((different_count + 1))
    fi
done

echo ""
printf "${BLUE}Summary:${NC} $identical_count identical, $different_count customized, $missing_count not adopted/missing\n"
echo ""
echo "Run with command name for full diff: ./scripts/diff-commands.sh plan-feature"
