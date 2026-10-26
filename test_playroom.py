import tempfile
import unittest
from pathlib import Path
from companion import CompanionState
from game_guard import is_game_process


class PlayroomTests(unittest.TestCase):
    def test_exact_game_names(self):
        self.assertTrue(is_game_process('Overwatch.exe'))
        self.assertFalse(is_game_process('Overwatch-notes.exe'))
        self.assertFalse(is_game_process('Codex.exe'))

    def test_game_suppression_does_not_persist_quiet(self):
        with tempfile.TemporaryDirectory() as directory:
            now = [0.]
            state = CompanionState(Path(directory) / 'state.json', lambda: now[0])
            state.configure_reminder(True, 1)
            now[0] = 120
            self.assertEqual(state.tick(suppress_reminders=True), [])
            restored = CompanionState(state.path)
            self.assertFalse(restored.data['quiet'])
            self.assertEqual(state.tick(), ['water'])
