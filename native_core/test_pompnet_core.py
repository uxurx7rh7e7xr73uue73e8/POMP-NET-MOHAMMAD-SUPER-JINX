import json, os, sqlite3, tempfile, unittest
from unittest.mock import patch
import pompnet_core as core

class NativeCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        core.DB=os.path.join(self.tmp.name,"state.db")
        core.CONFIG=os.path.join(self.tmp.name,"xray.json")
        core.PUBLIC_HOST="vpn.example.test"
        core.TOKEN="test-token"
        core.init()
    def tearDown(self): self.tmp.cleanup()
    def test_initial_inbound_is_persisted(self):
        with core.db() as c:
            row=c.execute("SELECT * FROM inbounds").fetchone()
        self.assertEqual(row["tag"],"POMP-NET-VLESS-WS")
        self.assertEqual(row["port"],2001)
    def test_config_uses_persisted_clients_and_brand_label(self):
        with core.db() as c:
            c.execute("INSERT INTO clients VALUES(?,?,?,?,1,0,0,?)",
                      ("client-1","POMP-NET-VLESS-WS","محمد","11111111-1111-4111-8111-111111111111",1))
            c.commit()
        core.build_config()
        cfg=json.load(open(core.CONFIG,encoding="utf-8"))
        self.assertEqual(cfg["inbounds"][0]["settings"]["clients"][0]["email"],"محمد")
        row={"uuid":"11111111-1111-4111-8111-111111111111","name":"محمد"}
        ib={"path":"/pompnet/ws"}
        self.assertIn("POMP%20NET%20MOHAMMAD",core.link(row,ib))
    def test_config_validation_fails_closed(self):
        core.build_config()
        with patch.object(core.os.path,"isfile",return_value=True), patch.object(core.subprocess,"run",return_value=type("R",(),{"returncode":1,"stderr":"bad config","stdout":""})()):
            with self.assertRaisesRegex(RuntimeError,"xray_config_rejected"): core.validate()

if __name__=="__main__": unittest.main()
