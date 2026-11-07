"""Focused offline regressions for the reliability fixes."""
import copy
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from src import database
from src.ai_explainer import validate_brief, verified_fields
from src.evaluate_agent import grade_answer
from src.openai_agent import execute_tool
from tests.support import FakeFirestore, seeded_fake_firestore

ROOT = Path(__file__).resolve().parents[1]


class ReliabilityTest(unittest.TestCase):
    def setUp(self):
        self.client = seeded_fake_firestore()
        database.set_firestore_client_for_testing(self.client)
        self.addCleanup(database.set_firestore_client_for_testing, seeded_fake_firestore())

    def page(self, analysis=True):
        app = AppTest.from_file(str(ROOT / 'src/web_app.py')).run(timeout=30)
        if analysis:
            app.switch_page('pages/shipment_analysis.py').run(timeout=30)
        self.assertFalse(list(app.exception))
        return app

    def test_totals_and_first_order_are_separate(self):
        with patch('src.pages.shipment_analysis.get_openai_api_key', return_value=None):
            app = self.page()
            app.selectbox[0].select('S-106').run(timeout=30)
        text = '\n'.join(row.value for row in app.markdown)
        self.assertIn('53 units uncovered across 3 orders', text)
        self.assertIn('O-209 · 13 units short', text)

    def test_priority_is_per_order_and_boundary_is_strict(self):
        for shorts, expected in [([6, 6], ['analyst_review'] * 2), ([10], ['analyst_review']), ([11], ['same_day_review'])]:
            allocation = [{'order_id': f'O-{i}', 'qty_uncovered': n} for i, n in enumerate(shorts)]
            with patch('src.openai_agent.calculate_order_allocation', return_value=allocation):
                impact = execute_tool('check_shipment_impact', {'shipment_id': 'S-104'})
                self.assertEqual([a['action_id'] for a in impact['allowed_next_steps']], expected)
            # Use actual UI with two six-unit shortages, and verify the banner.
        orders = self.client.collection('orders').documents
        orders['O-201']['qty_needed'] = 6
        orders['O-202']['qty_needed'] = 6
        self.client.collection('inventory').documents['CTRL-01']['available_qty'] = 0
        app = self.page()
        text = '\n'.join(row.value for row in app.markdown)
        self.assertIn('ANALYST REVIEW', text)
        self.assertNotIn('HIGH PRIORITY', text)

    def test_allocation_includes_fully_covered_order(self):
        allocation = execute_tool('check_shipment_impact', {'shipment_id': 'S-104'})['allocation']
        self.assertEqual([(a['order_id'], a['qty_covered'], a['qty_uncovered']) for a in allocation],
                         [('O-201', 20, 0), ('O-202', 10, 15)])

    def test_stale_brief_clears_on_inventory_and_shipment_change(self):
        with patch('src.ui.get_openai_api_key', return_value='fake'), patch('src.ai_explainer.explain_impact_with_openai', return_value={
            'headline': 'Old 15-unit explanation', 'summary': 'Old brief', 'analyst_focus': 'Review', 'limitation': 'Synthetic'}):
            app = self.page()
            next(b for b in app.button if b.label == 'Generate explanation').click().run(timeout=30)
            self.assertTrue(any('Old 15-unit' in row.value for row in app.markdown))
            self.client.collection('inventory').documents['CTRL-01']['available_qty'] = 100
            app.run(timeout=30)
            self.assertEqual(app.metric[0].value, '0')
            self.assertFalse(any('Old 15-unit' in row.value for row in app.markdown))
            app.selectbox[0].select('S-106').run(timeout=30)
            self.assertFalse(any('Old 15-unit' in row.value for row in app.markdown))

    def test_offline_launcher_mode_recovers_database_after_reload(self):
        with patch.dict('os.environ', {"SUPPLYCHAIN_DEMO_MODE": "1"}):
            database.set_firestore_client_for_testing(None)
            app = self.page(False)
            self.assertEqual(app.metric[0].value, '50')
            database.set_firestore_client_for_testing(None)
            app.run(timeout=30)
            self.assertFalse(list(app.exception))
            self.assertEqual(app.metric[0].value, '50')
            self.assertTrue(any('Offline demo' in row.value for row in app.info))

    def test_empty_database_both_entry_points(self):
        database.set_firestore_client_for_testing(FakeFirestore())
        app = self.page(False)
        self.assertTrue(any('Seed' in row.value for row in app.info))
        direct = AppTest.from_file(str(ROOT / 'src/pages/shipment_analysis.py')).run(timeout=30)
        self.assertFalse(list(direct.exception))
        self.assertTrue(any('Seed' in row.value for row in direct.info))

    def test_overview_opens_selected_shipment(self):
        app = self.page(False)
        app.selectbox[0].select('S-106').run(timeout=30)
        next(b for b in app.button if b.label == 'Open shipment analysis').click().run(timeout=30)
        self.assertFalse(list(app.exception))
        self.assertEqual(app.selectbox[0].value, 'S-106')

    def test_public_generation_requires_explicit_server_opt_in(self):
        from src.ui import get_openai_api_key
        with patch.dict('os.environ', {"OPENAI_API_KEY": "fake", "ENABLE_LIVE_AI": "false"}):
            self.assertIsNone(get_openai_api_key())
            app = self.page()
            self.assertFalse(any(b.label == "Generate explanation" for b in app.button))

    def test_ai_failure_keeps_verified_results_visible(self):
        with patch('src.ui.get_openai_api_key', return_value='fake'), patch(
                'src.ai_explainer.explain_impact_with_openai', side_effect=ValueError('bad response')):
            app = self.page()
            next(b for b in app.button if b.label == 'Generate explanation').click().run(timeout=30)
            self.assertFalse(list(app.exception))
            self.assertTrue(any('Explanation unavailable' in e.value for e in app.error))
            self.assertEqual(app.metric[0].value, '1')

    def test_valid_replacement_preserves_other_collections(self):
        self.client.collection('unrelated').documents['keep'] = {'value': 1}
        result = database.seed_firestore(self.client, replace=True)
        self.assertEqual(result['orders'], 248)
        self.assertEqual(self.client.collection('unrelated').documents, {'keep': {'value': 1}})

    def test_invalid_seeds_never_mutate_existing_database(self):
        before = {name: copy.deepcopy(col.documents) for name, col in self.client.collections.items()}
        for failure in ('missing', 'empty', 'duplicate', 'reference', 'date', 'quantity', 'field', 'cost'):
            for replace in (False, True):
                with self.subTest(failure=failure, replace=replace), tempfile.TemporaryDirectory() as tmp:
                    target = Path(tmp)
                    for source in database.DATA_DIR.glob('*.csv'):
                        shutil.copy(source, target / source.name)
                    file = target / 'orders.csv'
                    rows = list(csv.DictReader(file.open()))
                    fields = list(rows[0])
                    if failure == 'missing':
                        file.unlink()
                    elif failure == 'empty':
                        file.write_text(','.join(fields) + '\n')
                    else:
                        if failure == 'duplicate': rows.append(rows[0].copy())
                        if failure == 'reference': rows[0]['customer_id'] = 'missing'
                        if failure == 'date': rows[0]['due_date'] = 'bad-date'
                        if failure == 'quantity': rows[0]['qty_needed'] = '-1'
                        if failure == 'field': rows[0]['order_id'] = ''
                        if failure == 'cost':
                            file = target / 'items.csv'
                            rows = list(csv.DictReader(file.open()))
                            fields = list(rows[0]); rows[0]['unit_cost_usd'] = 'nan'
                        with file.open('w', newline='') as out:
                            writer = csv.DictWriter(out, fields); writer.writeheader(); writer.writerows(rows)
                    with patch.object(database, 'DATA_DIR', target), self.assertRaises((ValueError, FileNotFoundError)):
                        database.seed_firestore(self.client, replace=replace)
                    self.assertEqual(before, {name: col.documents for name, col in self.client.collections.items()})

    def test_structured_response_checks_and_negative_commentary(self):
        for sid in ('S-104', 'S-106', 'S-105'):
            shipment = execute_tool('get_shipment_details', {'shipment_id': sid})
            impact = execute_tool('check_shipment_impact', {'shipment_id': sid})
            brief = verified_fields(shipment, impact)
            brief.update(headline='Verified impact', summary='Review the supplied records.', analyst_focus='Use permitted review actions.', limitation='Synthetic data.')
            self.assertEqual(validate_brief(brief, shipment, impact), brief)
            from types import SimpleNamespace
            from src.ai_explainer import explain_impact_with_openai
            with patch('openai.OpenAI') as client:
                client.return_value.chat.completions.create.return_value = SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(brief)))])
                self.assertEqual(explain_impact_with_openai(shipment, impact, 'Synthetic policy', api_key='fake'), brief)
            if sid != 'S-104': continue
            for key, value in [('orders', []), ('actions', []), ('delay_cause', 'customs'), ('delivery_promise', 'Tomorrow'),
                               ('summary', 'Zero shortage, not 15; promise delivery.'), ('summary', 'Delayed due to customs.'),
                               ('summary', 'O-202 has 0 units uncovered.'), ('summary', 'We guarantee delivery tomorrow.')]:
                bad = dict(brief, **{key: value})
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    validate_brief(bad, shipment, impact)
                self.assertFalse(grade_answer(bad, {'question': 'Explain S-104', 'expected_mode': 'openai_explanation'})['passed'])
