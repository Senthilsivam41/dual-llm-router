import unittest
from math_utils import add


class TestMathUtils(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(-1, 1), 0)
        self.assertEqual(add(0, 0), 0)
        self.assertEqual(add(-5, -7), -12)
        self.assertEqual(add(1.5, 2.5), 4.0)


if __name__ == "__main__":
    unittest.main()
