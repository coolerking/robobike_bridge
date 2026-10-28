"""Tests for status response parsing without network access."""

from io import BytesIO
import unittest
from unittest.mock import patch

from bridge.constants import ROBOBIKE_STATUS_CSV_INDEXES
from bridge.constants import ROBOBIKE_STATUS_CSV_INDEXES_FLOAT
from bridge.robobike_bridge import RobobikeBridge


class TestStatusParsing(unittest.TestCase):
    """Verify numeric types and explicit errors for malformed status values."""

    def setUp(self):
        self.bridge = RobobikeBridge('localhost')
        self.fields = [
            'b', '1', '2', 'OK', '0', '10', '0.03', '12.0', '0.03',
            '20', '40', '0.011', '0', '0.0', '30', '0.75', '0',
        ]

    def read_status(self, method):
        response = BytesIO(','.join(self.fields).encode('utf-8'))
        with patch(
            'bridge.robobike_bridge.urlopen', return_value=response
        ) as request:
            result = getattr(self.bridge, method)()
        request.assert_called_once()
        return result

    def test_valid_numeric_fields_keep_their_types(self):
        for method in ('send_command', 'get_status'):
            with self.subTest(method=method):
                result = self.read_status(method)
                self.assertNotIn('status', result)
                self.assertIsInstance(result['mot_spd'], int)
                self.assertEqual(result['mot_spd'], 10)
                self.assertIsInstance(result['gain_str'], float)
                self.assertEqual(result['gain_str'], 0.03)
                self.assertEqual(result['OK'], 'OK')

    def test_invalid_numeric_fields_return_and_log_errors(self):
        for method in ('send_command', 'get_status'):
            for field in ('mot_spd', 'gain_str'):
                with self.subTest(method=method, field=field):
                    position = ROBOBIKE_STATUS_CSV_INDEXES.index(field)
                    original = self.fields[position]
                    self.fields[position] = 'invalid'
                    try:
                        with self.assertLogs(
                            'bridge.robobike_bridge', level='ERROR'
                        ) as logs:
                            result = self.read_status(method)
                        self.assertEqual(set(result), {'status', 'error'})
                        self.assertEqual(result['status'], 'error')
                        self.assertIn(field, result['error'])
                        self.assertIn("'invalid'", result['error'])
                        self.assertIn(field, '\n'.join(logs.output))
                        self.assertIn("'invalid'", '\n'.join(logs.output))
                    finally:
                        self.fields[position] = original

    def test_non_finite_float_fields_return_and_log_errors(self):
        for method in ('send_command', 'get_status'):
            for field in ROBOBIKE_STATUS_CSV_INDEXES_FLOAT:
                for value in ('nan', 'inf', '-inf', '1e309'):
                    with self.subTest(method=method, field=field, value=value):
                        position = ROBOBIKE_STATUS_CSV_INDEXES.index(field)
                        original = self.fields[position]
                        self.fields[position] = value
                        try:
                            with self.assertLogs(
                                'bridge.robobike_bridge', level='ERROR'
                            ) as logs:
                                result = self.read_status(method)
                            self.assertEqual(set(result), {'status', 'error'})
                            self.assertEqual(result['status'], 'error')
                            self.assertIn(field, result['error'])
                            self.assertIn(repr(value), result['error'])
                            self.assertIn(field, '\n'.join(logs.output))
                            self.assertIn(repr(value), '\n'.join(logs.output))
                        finally:
                            self.fields[position] = original
