"""Publication gates exercise evidence integrity, inventory, and source drift."""
import shutil
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from check_site import check

ROOT = Path(__file__).resolve().parent


class PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = Path(os.environ['RUNNER_TEMP']) if 'RUNNER_TEMP' in os.environ else ROOT / '.ai-work' / 'runs' / 'test-site'
        cls.work.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.work)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'dist', self.root / 'dist')
        shutil.copytree(ROOT / 'security', self.root / 'security')

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_snapshot_validates_in_isolation(self):
        check(self.root)

    def test_changed_evidence_is_rejected(self):
        path = self.root / 'dist/evidence/confirmation-results.csv'
        path.write_bytes(path.read_bytes().replace(b'baseline', b'tampered', 1))
        with self.assertRaisesRegex(ValueError, 'file changed'):
            check(self.root)

    def test_extra_file_is_rejected(self):
        (self.root / 'dist/unreviewed.txt').write_text('extra')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            check(self.root)

    def test_symlink_is_rejected(self):
        (self.root / 'dist/linked').symlink_to('index.html')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            check(self.root)

    def test_source_drift_is_rejected(self):
        for name in ('study_manifest.json', 'results.csv', 'benchmark_results.csv', 'games.csv'):
            shutil.copy2(ROOT / name, self.root / name)
        (self.root / 'results.csv').write_text('changed source')
        with self.assertRaisesRegex(ValueError, 'Bundled/source mismatch'):
            check(self.root)

    def test_optimized_python_fails_closed(self):
        result = subprocess.run([sys.executable, '-O', '-B', str(ROOT / 'check_site.py'), '--root', str(self.root)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('non-optimized Python', result.stderr)


if __name__ == '__main__':
    unittest.main()
