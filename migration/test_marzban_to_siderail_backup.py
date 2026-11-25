import importlib.util, pathlib, unittest
P=pathlib.Path(__file__).with_name("marzban_to_siderail_backup.py")
spec=importlib.util.spec_from_file_location("converter",P)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class ConvertTests(unittest.TestCase):
    def setUp(self):
        self.src={"format":"pompnet-marzban-export-v1","users":[{
            "id":7,"username":"alice","status":"active","expire":0,"data_limit":1000,
            "used_traffic":125,"ip_limit":3,"proxies":{"vless":{"id":"11111111-1111-4111-8111-111111111111"}},
            "inbounds":{"vless":["vless-ws"]},"token":"sub-token-123","created_at":1700000000
        }]}
        self.map={"vless-ws":{"id":1,"tag":"VLESS-WS","protocol":"vless","transport":"ws","port":20000,"path":"/vless"}}
    def test_preserves_identity_and_quota(self):
        out=m.convert(self.src,self.map)
        u=out["users"][0]
        self.assertEqual(u["uuid"],"11111111-1111-4111-8111-111111111111")
        self.assertEqual(u["sub_token"],"sub-token-123")
        self.assertEqual(u["down"],125)
        self.assertEqual(u["ip_limit"],3)
        self.assertEqual(out["user_inbounds"],[{"user_id":7,"inbound_id":1}])
    def test_parses_iso_datetime_export(self):
        self.assertEqual(m.epoch_ms("2024-01-01T00:00:00+00:00"),1704067200000)
    def test_rejects_unsupported_transport(self):
        bad={"vless-ws":dict(self.map["vless-ws"],transport="grpc")}
        with self.assertRaisesRegex(ValueError,"unsupported_inbound_mapping"):
            m.convert(self.src,bad)
    def test_rejects_missing_inbound_mapping(self):
        with self.assertRaisesRegex(ValueError,"inbound_map_required"):
            m.convert(self.src,{})
    def test_rejects_ambiguous_protocol_credentials(self):
        self.src["users"][0]["proxies"]["vmess"]={"id":"different"}
        with self.assertRaisesRegex(ValueError,"protocol_credentials_differ"):
            m.convert(self.src,self.map)
    def test_rejects_duplicate_subscription_tokens(self):
        self.src["users"].append(dict(self.src["users"][0],id=8,username="bob"))
        with self.assertRaisesRegex(ValueError,"duplicate_subscription_token"):
            m.convert(self.src,self.map)

if __name__=="__main__": unittest.main()
