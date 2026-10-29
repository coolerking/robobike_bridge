"""Tests for interrupted HTTP response bodies without network access."""

from http.client import IncompleteRead
from io import BytesIO
import unittest
from unittest.mock import MagicMock, patch

from bridge.robobike_bridge import RobobikeBridge


class TestIncompleteResponse(unittest.TestCase):
    """Verify interrupted responses are logged and handled by each API."""

    def setUp(self):
        self.bridge = RobobikeBridge('localhost')

    def interrupted_response(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.side_effect = IncompleteRead(b'a,1000', 100)
        return response

    def test_reads_return_error_dictionaries(self):
        for method in ('send_command', 'get_status', 'get_telemetry'):
            with self.subTest(method=method):
                with patch(
                    'bridge.robobike_bridge.urlopen',
                    return_value=self.interrupted_response(),
                ) as request:
                    with self.assertLogs(
                        'bridge.robobike_bridge', level='ERROR'
                    ) as logs:
                        result = getattr(self.bridge, method)()
                self.assertEqual(
                    result,
                    {
                        'status': 'error',
                        'error': 'IncompleteRead(6 bytes read, 100 more expected)',
                    },
                )
                self.assertIn('IncompleteRead', '\n'.join(logs.output))
                request.assert_called_once()

    def test_clear_buffer_logs_and_reraises(self):
        with patch(
            'bridge.robobike_bridge.urlopen',
            return_value=self.interrupted_response(),
        ):
            with self.assertLogs('bridge.robobike_bridge', level='ERROR'):
                with self.assertRaises(IncompleteRead):
                    self.bridge.send_clear_buffer()

    def test_clear_buffer_accepts_ok(self):
        for body in (b'OK', b'OK\r\n'):
            with self.subTest(body=body):
                with patch(
                    'bridge.robobike_bridge.urlopen', return_value=BytesIO(body)
                ) as request:
                    self.assertIsNone(self.bridge.send_clear_buffer())
                request.assert_called_once()

    def test_clear_buffer_rejects_unexpected_responses(self):
        for body in (b'0', b'', b'ERROR', b'ok'):
            with self.subTest(body=body):
                with patch(
                    'bridge.robobike_bridge.urlopen', return_value=BytesIO(body)
                ):
                    with self.assertRaisesRegex(
                        ValueError, 'Unexpected clear_buffer response'
                    ):
                        self.bridge.send_clear_buffer()

    def test_unexpected_clear_response_preserves_telemetry_history(self):
        sample = dict(a='a', time=950, drv=2.0)
        self.bridge._telemetry_history = [sample]
        self.bridge._latest_telemetry_time = 950
        for body in (b'0', b'', b'ERROR', b'ok'):
            with self.subTest(body=body):
                with patch(
                    'bridge.robobike_bridge.urlopen',
                    return_value=BytesIO(body),
                ) as request:
                    with self.assertRaisesRegex(
                        ValueError, 'Unexpected clear_buffer response'
                    ):
                        self.bridge.send_clear_buffer()
                request.assert_called_once()
                self.assertEqual(self.bridge._telemetry_history, [sample])
                self.assertEqual(self.bridge._latest_telemetry_time, 950)

    def test_interrupted_clear_reraises_without_updating_history(self):
        sample = dict(a='a', time=950, drv=2.0)
        self.bridge._telemetry_history = [sample]
        self.bridge._latest_telemetry_time = 950
        with patch(
            'bridge.robobike_bridge.urlopen',
            return_value=self.interrupted_response(),
        ) as request:
            with self.assertLogs('bridge.robobike_bridge', level='ERROR'):
                with self.assertRaises(IncompleteRead):
                    self.bridge.send_clear_buffer()
        request.assert_called_once()
        self.assertEqual(self.bridge._telemetry_history, [sample])
        self.assertEqual(self.bridge._latest_telemetry_time, 950)

    def test_connection_reset_returns_error_dictionaries(self):
        for method in ('send_command', 'get_status', 'get_telemetry'):
            with self.subTest(method=method):
                response = MagicMock()
                response.__enter__.return_value = response
                error = ConnectionResetError(10054, 'Connection reset by peer')
                response.read.side_effect = error
                with patch('bridge.robobike_bridge.urlopen', return_value=response):
                    with self.assertLogs('bridge.robobike_bridge', level='ERROR'):
                        result = getattr(self.bridge, method)()
                self.assertEqual(result, {'status': 'error', 'error': str(error)})

    def test_invalid_utf8_returns_error_dictionaries(self):
        for method in ('send_command', 'get_status', 'get_telemetry'):
            with self.subTest(method=method):
                with patch(
                    'bridge.robobike_bridge.urlopen', return_value=BytesIO(b'\xff')
                ) as request:
                    with self.assertLogs('bridge.robobike_bridge', level='ERROR'):
                        result = getattr(self.bridge, method)()
                self.assertEqual(result['status'], 'error')
                self.assertIn('utf-8', result['error'])
                request.assert_called_once()

    def test_clear_response_failures_log_and_reraise(self):
        for error in (
            ConnectionResetError(10054, 'Connection reset by peer'),
            UnicodeDecodeError('utf-8', b'\xff', 0, 1, 'invalid start byte'),
        ):
            with self.subTest(error=type(error).__name__):
                response = MagicMock()
                response.__enter__.return_value = response
                response.read.side_effect = error
                with patch('bridge.robobike_bridge.urlopen', return_value=response):
                    with self.assertLogs('bridge.robobike_bridge', level='ERROR'):
                        with self.assertRaises(type(error)):
                            self.bridge.send_clear_buffer()

    def test_clear_response_failures_preserve_telemetry_history(self):
        for failure in ('reset', 'invalid_utf8'):
            with self.subTest(failure=failure):
                sample = dict(a='a', time=950, drv=2.0)
                self.bridge._telemetry_history = [sample]
                self.bridge._latest_telemetry_time = 950
                response = MagicMock()
                response.__enter__.return_value = response
                if failure == 'reset':
                    response.read.side_effect = ConnectionResetError(
                        10054, 'Connection reset by peer'
                    )
                else:
                    response.read.return_value = b'\xff'
                with patch(
                    'bridge.robobike_bridge.urlopen',
                    return_value=response,
                ) as request:
                    with self.assertLogs('bridge.robobike_bridge', level='ERROR'):
                        expected_error = (
                            ConnectionResetError if failure == 'reset'
                            else UnicodeDecodeError
                        )
                        with self.assertRaises(expected_error):
                            self.bridge.send_clear_buffer()
                request.assert_called_once()
                self.assertEqual(self.bridge._telemetry_history, [sample])
                self.assertEqual(self.bridge._latest_telemetry_time, 950)
