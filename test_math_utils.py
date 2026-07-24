import unittest

from math_utils import add


class TestAdd(unittest.TestCase):
    """Unit tests for the add function."""

    def test_add_positive_numbers(self):
        """Test addition of two positive numbers."""
        self.assertEqual(add(2, 3), 5)

    def test_add_negative_numbers(self):
        """Test addition of two negative numbers."""
        self.assertEqual(add(-2, -3), -5)

    def test_add_positive_and_negative(self):
        """Test addition of a positive and a negative number."""
        self.assertEqual(add(5, -3), 2)

    def test_add_with_zero(self):
        """Test addition involving zero."""
        self.assertEqual(add(0, 7), 7)
        self.assertEqual(add(7, 0), 7)
        self.assertEqual(add(0, 0), 0)

    def test_add_floats(self):
        """Test addition of floating point numbers."""
        self.assertAlmostEqual(add(2.5, 3.5), 6.0)

    def test_add_large_numbers(self):
        """Test addition of large numbers."""
        self.assertEqual(add(1000000, 2000000), 3000000)


if __name__ == "__main__":
    unittest.main()
