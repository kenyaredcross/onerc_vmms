"""Deployment cards get both places from the same scoped listing as their status."""
import unittest
from unittest.mock import patch

import frappe
from vmmsx.api import deployment as api


class TestListingPlaces(unittest.TestCase):
 def test_scoped_names_keep_both_journey_endpoints_and_grouped_counts(self):
  doc = frappe._dict(name='DEP-DEMO', site_name='Field hospital', site_address='Field address',
   site_latitude=-1.28, site_longitude=36.82, meeting_point='Branch office',
   meeting_address='Meeting address', meeting_latitude=-1.3, meeting_longitude=36.8,
   travel_notes='Report to reception', local_contact_name=None, local_contact_phone=None)
  counts = {'DEP-DEMO': {'total': 3}}
  with patch('frappe.get_doc', return_value=doc) as get_doc, \
    patch('vmmsx.deployment.services.assignment.counts_for_many', return_value=counts) as tally, \
    patch.object(api.deployment_service, 'status_dto', return_value={'name':'DEP-DEMO','status':'Active'}) as summary:
   rows = api._status_rows(['DEP-DEMO'])
  self.assertEqual(rows[0]['where']['meeting_point']['name'], 'Branch office')
  self.assertEqual(rows[0]['where']['site']['latitude'], -1.28)
  self.assertEqual(rows[0]['status'], 'Active')
  self.assertTrue(rows[0]['where']['site']['has_point'])
  tally.assert_called_once_with(['DEP-DEMO'])
  summary.assert_called_once_with(doc, counts=counts['DEP-DEMO'])
  get_doc.assert_called_once_with(api.DEPLOYMENT_DOCTYPE, 'DEP-DEMO')
