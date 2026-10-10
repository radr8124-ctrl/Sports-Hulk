#!/usr/bin/env python3
"""Offline tests: protected, no-echo Groq Free account setup."""
import importlib.util
import stat
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("groq_key_setup",ROOT/"scripts"/"zenith_groq_secure_setup.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TestSecureGroqSetup(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.destination=Path(t.name)/".env.groq_shadow"
        self.fake_key="gsk_FAKE_OFFLINE_UNIT_TEST_NOT_REAL_Abc123456"

    def test_free_unbilled_confirmation_creates_mode_600_once(self):
        module.install_credential(self.destination,self.fake_key,"FREE",
            when=datetime(2026,10,10,12,0,tzinfo=timezone.utc))
        self.assertEqual(stat.S_IMODE(self.destination.stat().st_mode),0o600)
        result=self.destination.read_text()
        self.assertIn("GROQ_API_KEY="+self.fake_key,result)
        self.assertIn("ZENITH_GROQ_ACCOUNT_TIER=FREE_UNBILLED",result)
        self.assertIn("ZENITH_GROQ_ACCOUNT_NO_PAYMENT_METHOD=1",result)
        self.assertIn("ZENITH_GROQ_ACCOUNT_USER_CONFIRMED=1",result)
        self.assertIn("ZENITH_GROQ_ACCOUNT_CHECKED_AT=2026-10-10T12:00:00Z",result)
        self.assertNotIn("POSTHOG",result)
        self.assertNotIn("PAID",result.replace("FREE_UNBILLED",""))

    def test_rejects_nonfree_account_confirmation(self):
        for value in ["","yes","Developer","PAID","Free",None]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError,"free_plan_confirmation"):
                    module.install_credential(self.destination,self.fake_key,value)
        self.assertFalse(self.destination.exists())

    def test_rejects_wrong_key_shapes_and_whitespace(self):
        for key in ["","sk-test","gsk_ab","gsk_abc defghijklmno","gsk_abc\nDEF", "X"*300]:
            with self.subTest(key=key[:20]):
                with self.assertRaisesRegex(ValueError,"invalid_groq_key"):
                    module.install_credential(self.destination,key,"FREE")
        self.assertFalse(self.destination.exists())

    def test_never_overwrites_existing_key_or_file(self):
        module.install_credential(self.destination,self.fake_key,"FREE")
        before=self.destination.read_bytes()
        with self.assertRaises(FileExistsError):
            module.install_credential(self.destination,
                "gsk_ANOTHER_FAKE_CREDENTIAL_ABCDEFGH","FREE")
        self.assertEqual(self.destination.read_bytes(),before)

    def test_rejects_symlink_target(self):
        original=self.destination.parent/"original.secret"
        original.write_text("unchanged")
        self.destination.symlink_to(original)
        with self.assertRaises((FileExistsError, OSError)):
            module.install_credential(self.destination,self.fake_key,"FREE")
        self.assertEqual(original.read_text(),"unchanged")

    def test_requires_tty_and_does_not_echo_secret(self):
        with self.assertRaisesRegex(RuntimeError,"interactive_terminal_required"):
            module.prompt_and_install(path=self.destination,
                is_tty=False,
                ask_plan=lambda _: "FREE",
                read_secret=lambda _: self.fake_key)
        self.assertFalse(self.destination.exists())

if __name__=="__main__":
    unittest.main()
