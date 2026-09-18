import unittest
from guest.offline_repositories import platform_manifest_for


class GuestArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.index = {'manifests': [
            {'digest': 'sha256:x86', 'platform': {'os': 'linux', 'architecture': 'amd64'}},
            {'digest': 'sha256:arm', 'platform': {'os': 'linux', 'architecture': 'arm64', 'variant': 'v8'}},
            {'digest': 'sha256:attestation', 'platform': {'os': 'unknown', 'architecture': 'unknown'}},
        ]}

    def test_both_guests_choose_their_own_real_layers(self):
        self.assertEqual('sha256:x86', platform_manifest_for(self.index, 'amd64')['digest'])
        self.assertEqual('sha256:arm', platform_manifest_for(self.index, 'arm64')['digest'])

    def test_missing_architecture_never_falls_back_to_amd64(self):
        self.index['manifests'].pop(1)
        with self.assertRaises(ValueError):
            platform_manifest_for(self.index, 'arm64')

    def test_ambiguous_and_unsupported_platforms_rejected(self):
        self.index['manifests'].append(self.index['manifests'][1])
        for arch in ('arm64', 'armhf'):
            with self.assertRaises(ValueError):
                platform_manifest_for(self.index, arch)
