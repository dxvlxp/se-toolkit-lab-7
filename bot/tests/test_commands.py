import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from handlers import CommandContext, route_text

class HandlerSmokeTests(unittest.TestCase):
    def test_all_cli_commands_return_text(self):
        for command in ('/start','/help','/health','/labs','/scores lab-04'):
            self.assertTrue(route_text(command, CommandContext()))
    def test_unimplemented_backend_is_not_reported_healthy(self):
        self.assertIn('pending integration', route_text('/health', CommandContext()))

if __name__ == '__main__':
    unittest.main()
