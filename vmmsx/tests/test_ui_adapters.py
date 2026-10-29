"""The live UI adapters keep workflow and stock mutations behind server checks."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from vmmsx.api import assets, tasks


class TestMockupAdapters(unittest.TestCase):
	def setUp(self):
		for module in (assets, tasks):
			translator = patch.object(module, "_", side_effect=lambda value: value)
			translator.start()
			self.addCleanup(translator.stop)

	def test_edit_asset_cannot_move_issued_stock(self):
		item = SimpleNamespace(geo_node="Branch A", total_quantity=5, available_quantity=3)
		with patch.object(assets, "_locked", return_value=item), patch.object(assets, "_manager") as manager:
			with (
				patch.object(assets.frappe, "throw", side_effect=ValueError("Issued stock")),
				self.assertRaisesRegex(ValueError, "Issued stock"),
			):
				assets.update_asset("asset", "Helmet", "Branch B")
			manager.assert_called_once_with("Branch B")

	def test_opening_stock_uses_receipt_transaction(self):
		doc = MagicMock(name="asset")
		doc.name = "ASSET-1"
		doc.get.side_effect = lambda key: {"name": "ASSET-1"}.get(key)
		with (
			patch.object(assets, "_manager"),
			patch.object(assets.frappe, "get_doc", return_value=doc),
			patch.object(assets, "receive") as receipt,
			patch.object(assets, "_row", return_value={"name": "ASSET-1"}),
		):
			assets.create_asset("Helmet", "Branch A", quantity=4)
			receipt.assert_called_once_with("ASSET-1", 4)

	def test_board_completion_reuses_signoff_after_write_permission(self):
		task = SimpleNamespace(status="submitted", percent_complete=100)
		with (
			patch.object(tasks, "_writable", return_value=task) as writable,
			patch.object(tasks.task_service, "sign_off", return_value={"status": "completed"}) as signoff,
		):
			self.assertEqual(tasks.move_board_task("task", "completed"), {"status": "completed"})
			writable.assert_called_once_with("task")
			signoff.assert_called_once_with(task)

	def test_board_cannot_complete_assigned_work(self):
		task = SimpleNamespace(status="assigned", percent_complete=0)
		with (
			patch.object(tasks, "_writable", return_value=task),
			patch.object(tasks.task_service, "sign_off") as signoff,
		):
			with (
				patch.object(tasks.frappe, "throw", side_effect=ValueError("Invalid move")),
				self.assertRaisesRegex(ValueError, "Invalid move"),
			):
				tasks.move_board_task("task", "completed")
			signoff.assert_not_called()
