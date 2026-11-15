import gzip
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verify_kernel import embedded_config, verify


class ArtifactVerificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fragment = self.root / 'required.config'
        self.fragment.write_text('CONFIG_KSU=y\nCONFIG_PID_NS=y\n# CONFIG_LTO_CLANG_FULL is not set\n')
        self.config = 'CONFIG_KSU=y\nCONFIG_PID_NS=y\nCONFIG_LTO_CLANG_FULL=n\nCONFIG_EXTRA=y\n'

    def image(self, text):
        return b'kernel literal IKCFG_ST text\0' + b'IKCFG_ST' + gzip.compress(text.encode()) + b'IKCFG_ED'

    def test_image_and_package_require_actual_embedded_features(self):
        image = self.root / 'Image'
        image.write_bytes(self.image(self.config))
        verify(image, 'image', [self.fragment])
        package = self.root / 'kernel.zip'
        with zipfile.ZipFile(package, 'w') as archive:
            archive.writestr('Image.gz', gzip.compress(image.read_bytes()))
        verify(package, 'zip', [self.fragment])
        image.write_bytes(self.image(self.config.replace('CONFIG_KSU=y', '# CONFIG_KSU is not set')))
        with self.assertRaisesRegex(ValueError, 'CONFIG_KSU'):
            verify(image, 'image', [self.fragment])

    def test_stale_image_cannot_borrow_a_good_external_config(self):
        reference = self.root / '.config'
        reference.write_text(self.config)
        image = self.root / 'Image'
        image.write_bytes(self.image(self.config.replace('CONFIG_EXTRA=y', 'CONFIG_EXTRA=m')))
        with self.assertRaisesRegex(ValueError, 'differs from build .config'):
            verify(image, 'image', [self.fragment], reference)

    def test_ambiguous_or_truncated_embedded_config_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'found 2'):
            embedded_config(self.image(self.config) * 2)
        with self.assertRaisesRegex(ValueError, 'found 0'):
            embedded_config(self.image(self.config)[:-10])

    def test_package_with_two_possible_kernels_is_rejected(self):
        package = self.root / 'ambiguous.zip'
        with zipfile.ZipFile(package, 'w') as archive:
            archive.writestr('Image', self.image(self.config))
            archive.writestr('Image.gz', gzip.compress(self.image(self.config)))
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            verify(package, 'zip', [self.fragment])

    def test_missing_builtin_or_module_setting_is_rejected(self):
        config = self.root / '.config'
        config.write_text('CONFIG_KSU=y\nCONFIG_PID_NS=m\n')
        with self.assertRaisesRegex(ValueError, 'CONFIG_PID_NS'):
            verify(config, 'config', [self.fragment])


if __name__ == '__main__':
    unittest.main()
