import unittest

class SimpleTestCase(unittest.TestCase):
    """Simple test case that always passes"""
    
    def test_simple(self):
        """A simple test that always passes"""
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
