import ctypes
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Frame(ctypes.Structure):
    _fields_ = [("token", ctypes.c_uint32), ("value", ctypes.c_int)]


class HubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hub = ctypes.CDLL(str(ROOT / "build/libhub.so"))
        cls.hub.hub_encode.argtypes = [ctypes.c_int]
        cls.hub.hub_encode.restype = Frame
        cls.hub.hub_update_period.argtypes = [ctypes.c_int]

    def test_initialize(self):
        self.assertEqual(self.hub.hub_initialize(), 0)

    def test_deploy_command(self):
        result = subprocess.run(
            [str(ROOT / "build/hub"), "dispatch", "deploy"],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(result.stdout, "0\n")

    def test_frame_value(self):
        self.assertEqual(self.hub.hub_encode(42).value, 42)

    def test_period_configuration(self):
        self.assertEqual(self.hub.hub_update_period(12), 12)

    def test_filter_configuration(self):
        self.hub.hub_configure_filters(2)
        self.assertEqual(self.hub.hub_initialize(), 0)


if __name__ == "__main__":
    unittest.main()
