"""Tests for telemetry averaging across successive buffer reads."""

from io import BytesIO
import unittest
from unittest.mock import patch

from bridge.robobike_bridge import RobobikeBridge


class TestTelemetryWindow(unittest.TestCase):
    """Verify history retention, eviction, and robot clock resets."""

    def setUp(self):
        self.bridge = RobobikeBridge('localhost')

    def read_samples(self, samples):
        rows = [
            ','.join(['a', str(timestamp)] + [str(value)] * 11)
            for timestamp, value in samples
        ]
        responses = [BytesIO('\n'.join(rows).encode('utf-8'))]
        if rows:
            responses.append(BytesIO(b'0'))
        with patch(
            'bridge.robobike_bridge.urlopen', side_effect=responses
        ) as request:
            result = self.bridge.get_telemetry()
        self.assertEqual(request.call_count, 2 if rows else 1)
        return result

    def test_averages_across_reads(self):
        self.read_samples([(1000, 0), (1050, 0)])
        result = self.read_samples([(1075, 10), (1100, 10)])
        self.assertEqual(result['drv'], 5.0)
        self.assertEqual(result['time'], 1100)
        self.assertEqual(result['a'], 'a')

    def test_includes_boundary_and_discards_older_samples(self):
        self.read_samples([(999, 100), (1000, 2), (1050, 4)])
        result = self.read_samples([(1100, 6)])
        self.assertEqual(result['drv'], 4.0)
        self.assertEqual(
            [sample['time'] for sample in self.bridge._telemetry_history],
            [1000, 1050, 1100],
        )

    def test_gap_longer_than_window_discards_history(self):
        self.read_samples([(1000, 0)])
        result = self.read_samples([(1101, 10)])
        self.assertEqual(result['drv'], 10.0)
        self.assertEqual(len(self.bridge._telemetry_history), 1)

    def test_empty_read_does_not_republish_history(self):
        self.read_samples([(1000, 0)])
        self.assertIsNone(self.read_samples([]))
        result = self.read_samples([(1050, 10)])
        self.assertEqual(result['drv'], 5.0)

    def test_clock_reset_discards_previous_history(self):
        self.read_samples([(1000, 100)])
        with self.assertLogs('bridge.robobike_bridge', level='WARNING'):
            result = self.read_samples([(950, 10)])
        self.assertEqual(result['drv'], 10.0)
        self.assertEqual(result['time'], 950)
        self.assertEqual(len(self.bridge._telemetry_history), 1)

    def test_non_finite_values_return_errors_without_updating_history(self):
        self.read_samples([(1000, 2)])
        history = self.bridge._telemetry_history.copy()
        for value in ('nan', 'inf', '-inf', '1e309'):
            with self.subTest(value=value):
                with self.assertLogs(
                    'bridge.robobike_bridge', level='ERROR'
                ) as logs:
                    result = self.read_samples([(1050, value)])
                self.assertEqual(result['status'], 'error')
                self.assertIn('drv', result['error'])
                self.assertIn('row 1', result['error'])
                self.assertIn(repr(value), result['error'])
                self.assertIn(repr(value), '\n'.join(logs.output))
                self.assertEqual(self.bridge._telemetry_history, history)
                self.assertEqual(self.bridge._latest_telemetry_time, 1000)
        result = self.read_samples([(1050, 4)])
        self.assertEqual(result['drv'], 3.0)

    def test_non_finite_average_returns_error_without_updating_history(self):
        self.read_samples([(1000, 1e308)])
        history = self.bridge._telemetry_history.copy()
        with self.assertLogs('bridge.robobike_bridge', level='ERROR') as logs:
            result = self.read_samples([(1050, 1e308)])
        self.assertEqual(result['status'], 'error')
        self.assertIn('Non-finite telemetry average for drv', result['error'])
        self.assertIn('drv', '\n'.join(logs.output))
        self.assertEqual(self.bridge._telemetry_history, history)
        self.assertEqual(self.bridge._latest_telemetry_time, 1000)
