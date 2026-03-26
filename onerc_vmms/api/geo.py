import frappe


@frappe.whitelist(allow_guest=True)
def get_geo_nodes(geo_level=None, parent_geo_node=None):
	filters = {"is_active": 1}
	if geo_level:
		filters["geo_level"] = geo_level
	if parent_geo_node:
		filters["parent_geo_node"] = parent_geo_node
	return frappe.get_all(
		"Geo Node",
		filters=filters,
		fields=["name", "node_name", "geo_level", "parent_geo_node"],
		order_by="node_name asc"
	)
