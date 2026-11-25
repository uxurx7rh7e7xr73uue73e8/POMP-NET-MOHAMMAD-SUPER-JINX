import base64, hashlib, hmac, json, os, unittest
from unittest.mock import patch
import pompnet_3xui_bridge as bridge
import tempfile
from pathlib import Path

class BridgeTests(unittest.TestCase):
    def test_adapter_token_roundtrip_and_tamper_rejected(self):
        with patch.object(bridge, "SECRET", "test-secret"):
            token=bridge.token_make("owner")
            self.assertEqual(bridge.token_check("Bearer "+token),"owner")
            with self.assertRaises(bridge.BridgeError):
                bridge.token_check("Bearer "+token+"x")
    def test_legacy_subscription_mapping_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(bridge, 'SUB_MAP_DB', str(Path(tmp) / 'map.sqlite3')):
                db=bridge.map_db()
                db.execute('INSERT INTO legacy_sub_map VALUES(?,?,?,?)', ('oldtoken123','newsub123','alice',1))
                db.commit(); db.close()
                self.assertEqual(bridge.lookup_sub_id('oldtoken123'), 'newsub123')
                self.assertIsNone(bridge.lookup_sub_id('unknown-token'))

    def test_new_client_subscription_mapping_is_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(bridge, "SUB_MAP_DB", str(Path(tmp) / "map.sqlite3")):
                token = bridge.register_subscription("alice", "xui-sub-id-123")
                self.assertGreaterEqual(len(token), 32)
                self.assertEqual(bridge.lookup_sub_id(token), "xui-sub-id-123")

    def test_missing_3xui_sub_id_fails_closed(self):
        with self.assertRaises(bridge.BridgeError):
            bridge.register_subscription("alice", "")


    def test_inbound_index_uses_branded_remark_and_legacy_alias(self):
        rows=[{"id":7,"remark":"POMP NET MOHAMMAD - VLESS WS","protocol":"vless","port":2053,"enable":True}]
        with patch.object(bridge, "request", return_value=rows):
            index=bridge.inbound_index()
        self.assertEqual(index["POMP NET MOHAMMAD - VLESS WS"]["id"],7)
        self.assertEqual(index["VLESS WS"]["id"],7)

    def test_api_token_does_not_bypass_owner_login(self):
        with patch.object(bridge, "API_TOKEN", "upstream-token"), patch.object(bridge, "USER", "owner"), patch.object(bridge, "PASSWORD", "correct"):
            with self.assertRaises(bridge.BridgeError):
                bridge.login_xui("attacker", "wrong")

    def test_normalize_traffic_and_expiry(self):
        client={"email":"alice","enable":True,"totalGB":1000,"expiryTime":1700000000000,
                "inboundIds":[4],"traffic":{"up":10,"down":20}}
        inbound={"vless":{"id":4,"protocol":"vless","tag":"VLESS WS"}}
        out=bridge.normalize(client,inbound)
        self.assertEqual(out["used_traffic"],30)
        self.assertEqual(out["inbounds"],{"vless":["VLESS WS"]})
        self.assertEqual(out["data_limit"],1000)
        self.assertEqual(out["expire"],1700000000)
if __name__ == "__main__": unittest.main()
