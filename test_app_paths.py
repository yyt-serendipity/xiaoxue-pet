import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app_paths import settings_directory


class AppPathsTests(unittest.TestCase):
    def test_source_keeps_existing_user_settings(self):
        self.assertEqual(settings_directory('project'), Path('project'))

    def test_frozen_settings_live_outside_installed_binaries(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'LOCALAPPDATA': directory}):
                result = settings_directory('read-only-install', frozen=True)
                self.assertEqual(result, Path(directory)/'XiaoxuePet')
                self.assertTrue(result.is_dir())
