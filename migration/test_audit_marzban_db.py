import os
import sqlite3
import tempfile
import unittest
from audit_marzban_db import audit

class MigrationAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "marzban.db")
        c = sqlite3.connect(self.path)
        c.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, proxies TEXT, sub_token TEXT, status TEXT)")
        c.execute("CREATE TABLE inbounds (id INTEGER PRIMARY KEY, tag TEXT, protocol TEXT, port INTEGER)")
        c.execute("INSERT INTO users(username, proxies, sub_token, status) VALUES ('PRIVATE_USER', '{}', 'PRIVATE_TOKEN', 'active')")
        c.execute("INSERT INTO inbounds(tag, protocol, port) VALUES ('vless', 'vless', 443)")
        c.commit()
        c.close()
    def tearDown(self):
        self.tmp.cleanup()
    def test_audit_is_read_only_and_reports_counts_not_secrets(self):
        report = audit(self.path)
        rendered = str(report)
        self.assertTrue(report["read_only"])
        self.assertTrue(report["migration_readiness"]["ready_for_mapping_review"])
        self.assertEqual(report["users"]["total"], 1)
        self.assertNotIn("PRIVATE_USER", rendered)
        self.assertNotIn("PRIVATE_TOKEN", rendered)
    def test_missing_subscription_identity_blocks_mapping_review(self):
        c = sqlite3.connect(self.path)
        c.execute("ALTER TABLE users RENAME TO old_users")
        c.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, proxies TEXT)")
        c.commit()
        c.close()
        report = audit(self.path)
        self.assertFalse(report["migration_readiness"]["ready_for_mapping_review"])
        self.assertIn("subscription_identity_column_not_found", report["migration_readiness"]["blockers"])

if __name__ == "__main__":
    unittest.main()
