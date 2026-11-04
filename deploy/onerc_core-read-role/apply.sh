#!/usr/bin/env bash
# Lets a region's oversight role (Head of Region) READ the scoped registers in
# its region, by giving onerc_core's geo scope an optional reading role.
#
# Kept here rather than committed to onerc_core, which serves many sites. On a
# site that registers no reading role (anything other than vmmsx) the patch
# changes nothing: core only consults it where a registration names one.
#
# Without it vmmsx still runs. A Head of Region simply sees nothing on the
# Region tab and cannot open the memberships routed to them.
#
# Usage, from the bench directory:
#   apps/vmmsx/deploy/onerc_core-read-role/apply.sh check    # would it apply? (default)
#   apps/vmmsx/deploy/onerc_core-read-role/apply.sh apply    # apply it
#   apps/vmmsx/deploy/onerc_core-read-role/apply.sh revert   # take it out
#   apps/vmmsx/deploy/onerc_core-read-role/apply.sh status   # applied or not
#
# Then restart the bench (`bench restart`, or `supervisorctl restart all`).
# Re-run `apply` after every update of onerc_core: an update replaces the files.
# Written against onerc_core vmmsx-edition at 8b8334e.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCH="$HERE/read-role.patch"
CORE="${ONERC_CORE:-$(cd "$HERE/../../.." && pwd)/onerc_core}"

[ -d "$CORE/onerc_core/access" ] || { echo "onerc_core not found at $CORE (set ONERC_CORE=/path/to/apps/onerc_core)"; exit 1; }
cd "$CORE"

applied() { git apply --reverse --check "$PATCH" >/dev/null 2>&1; }

case "${1:-check}" in
	status)
		if applied; then echo "applied"; else echo "not applied"; fi ;;
	check)
		if applied; then echo "Already applied."; exit 0; fi
		git apply --check "$PATCH" && echo "Applies cleanly. Run with 'apply'." ;;
	apply)
		if applied; then echo "Already applied. Nothing to do."; exit 0; fi
		git apply "$PATCH"
		echo "Applied to $CORE. Restart the bench so the workers load it." ;;
	revert)
		if ! applied; then echo "Not applied. Nothing to do."; exit 0; fi
		git apply --reverse "$PATCH"
		echo "Reverted. Restart the bench." ;;
	*)
		echo "Usage: $0 [check|apply|revert|status]"; exit 2 ;;
esac
