import unittest

from bridge.robobike_utils import get_command_index
from bridge.robobike_utils import get_command_name
from bridge.robobike_utils import get_status_index
from bridge.robobike_utils import get_status_name


class TestRobobikeUtils(unittest.TestCase):
    def test_command_name_and_index_round_trip(self) -> None:
        command_index = get_command_index("bt_Str_S")

        self.assertEqual(command_index, 7)
        self.assertEqual(get_command_name(command_index), "bt_Str_S")

    def test_status_name_and_index_round_trip(self) -> None:
        status_index = get_status_index("OK")

        self.assertEqual(get_status_name(status_index), "OK")

    def test_invalid_command_index_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_command_name(0)

    def test_invalid_status_index_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_status_name(-1)
