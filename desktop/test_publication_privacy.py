import unittest
from pathlib import Path
from prepare_publication import ROOT, included, private_file


class PublicationPrivacyTests(unittest.TestCase):
    def test_private_progress_connection_and_keys_are_never_selected(self):
        for name in ('nas-sync-config-v1.json','nas-sync-state-v1.json','nas-credentials-v1.enc',
                     'device-'+'a'*32+'.json','python-progress-v1.json','progress-v3-real.json',
                     'memory-v1.json','debug.keystore','release.p12','settings-v1.json'):
            self.assertTrue(private_file(name),name)
            self.assertFalse(included(ROOT/'desktop'/name),name)

    def test_public_code_and_generic_guide_remain_publishable(self):
        for name in ('nas_sync.py','nas_sync_ui.py','test_nas_sync.py'):
            self.assertTrue(included(ROOT/'desktop'/name),name)

    def test_build_staging_is_excluded(self):
        for path in ('desktop/.port-tools/config.json','android/app/build/assets/private.json',
                     'desktop/nas-sync-backup/python-progress-v1.json','desktop/dist-windows/private.json'):
            self.assertFalse(included(ROOT/path),path)


if __name__=='__main__':unittest.main()
