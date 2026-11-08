#!/usr/bin/env bash
# Lets the oversight roles READ the scoped registers, by giving onerc_core's geo
# scope two optional reading roles. Two patches, applied in this order:
#
#   read-role.patch       a regional reader (Head of Region): reads every county
#                         in the region it is assigned to
#   national-read.patch   a national reader (NSD Coordinator): holding the role
#                         reads everywhere, with no Geo Assignment
#
# Kept here rather than committed to onerc_core, which serves many sites. On a
# site that registers no reading role (anything other than vmmsx) the patches
# change nothing: core only consults them where a registration names one.
#
# Without them vmmsx still runs. A Head of Region or NSD Coordinator simply sees
# nothing on the Region and National tabs and cannot open the records there.
#
# Usage, from the bench directory:
#   apps/vmmsx/deploy/onerc_core-read-role/apply.sh check    # would they apply? (default)
#   apps/vmmsx/deploy/onerc_core-read-role/apply.sh apply    # apply what is missing
#   apps/vmmsx/deploy/onerc_core-read-role/apply.sh revert   # take them out
#   apps/vmmsx/deploy/onerc_core-read-role/apply.sh status   # which are applied
#
# A site that already has read-role.patch gets only national-read.patch on
# `apply`. Then restart the bench (`bench restart`, or `supervisorctl restart
# all`). Re-run `apply` after every update of onerc_core: an update replaces the
# files. Written against onerc_core vmmsx-edition at 8b8334e.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCHES=("$HERE/read-role.patch" "$HERE/national-read.patch")
CORE="${ONERC_CORE:-$(cd "$HERE/../../.." && pwd)/onerc_core}"

[ -d "$CORE/onerc_core/access" ] || { echo "onerc_core not found at $CORE (set ONERC_CORE=/path/to/apps/onerc_core)"; exit 1; }
cd "$CORE"

# national-read sits on top of read-role, so with it on, both are on, and
# read-role alone cannot be reversed past it. Ask the top one first.
applied() {
	git apply --reverse --check "${PATCHES[1]}" >/dev/null 2>&1 && return 0
	[ "$1" = "${PATCHES[0]}" ] && git apply --reverse --check "$1" >/dev/null 2>&1
}

case "${1:-check}" in
	status)
		for p in "${PATCHES[@]}"; do
			if applied "$p"; then echo "$(basename "$p"): applied"; else echo "$(basename "$p"): not applied"; fi
		done ;;
	check)
		# Check each missing patch on a scratch copy so the second is checked
		# against the first, as `apply` will lay them down.
		tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
		git ls-files -z onerc_core/access | xargs -0 -I{} cp --parents {} "$tmp"
		cd "$tmp"; git init -q
		missing=0
		for p in "${PATCHES[@]}"; do
			if (cd "$CORE" && applied "$p"); then echo "$(basename "$p"): already applied"; continue; fi
			missing=1
			git apply "$p" && echo "$(basename "$p"): applies cleanly"
		done
		[ "$missing" = 1 ] && echo "Run with 'apply'." || true ;;
	apply)
		for p in "${PATCHES[@]}"; do
			if applied "$p"; then echo "$(basename "$p"): already applied"; continue; fi
			git apply "$p"
			echo "$(basename "$p"): applied"
		done
		echo "Done in $CORE. Restart the bench so the workers load it." ;;
	revert)
		for ((i = ${#PATCHES[@]} - 1; i >= 0; i--)); do
			p="${PATCHES[$i]}"
			if git apply --reverse --check "$p" >/dev/null 2>&1; then
				git apply --reverse "$p"
				echo "$(basename "$p"): reverted"
			else
				echo "$(basename "$p"): not applied"
			fi
		done
		echo "Restart the bench." ;;
	*)
		echo "Usage: $0 [check|apply|revert|status]"; exit 2 ;;
esac
