# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Seed the configured Tanzania presentation site with dense demo activity."""

from vmmsx.patches.seed_society import SITE_CONFIG_KEY, configured


def execute():
	if configured() != "tanzania":
		print(f"vmmsx: {SITE_CONFIG_KEY} is not 'tanzania'; presentation scale seed skipped.")
		return

	from vmmsx.seed import tanzania_deployments, tanzania_operations, tanzania_people, tanzania_scale

	# The detailed records prove the lifecycles; operations supplies all open
	# vocabularies; scale makes the dashboards and branch comparisons substantial.
	tanzania_operations.main(commit=False)
	tanzania_people.main(commit=False)
	tanzania_deployments.main(commit=False)
	tanzania_scale.main(commit=False)

