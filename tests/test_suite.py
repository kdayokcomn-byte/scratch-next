"""
tests/test_suite.py
===================
scratch-next 全モジュールの動作確認・自動検証スイート (`pytest` または `python -m unittest` で実行)
"""

import os
import unittest
import tempfile
import scratch_next as sn


class TestScratchNextFullSuite(unittest.TestCase):
    def test_unicode_encoding_and_json_pack(self):
        msg = "こんにちはScratch🚀123!"
        encoded = sn.Encoding.encode(msg)
        self.assertTrue(encoded.isdigit())
        self.assertEqual(sn.Encoding.decode(encoded), msg)

        payload = {"hp": 100, "name": "勇者", "items": ["剣", "盾"]}
        j_enc = sn.Encoding.encode_json(payload)
        self.assertEqual(sn.Encoding.decode_json(j_enc), payload)

    def test_cloud_multiplexer_and_sandbox(self):
        sandbox = sn.VirtualCloudSandbox(project_id=123456)
        packed = sn.CloudVariableMultiplexer.pack({"x": 120, "y": 45, "score": 9999})
        sandbox.set_var("player1", packed, user="griffpatch")
        raw = sandbox.get_var("player1")
        unpacked = sn.CloudVariableMultiplexer.unpack(raw, ["x", "y", "score"])
        self.assertEqual(unpacked, {"x": 120, "y": 45, "score": 9999})

    def test_security_and_anticheat(self):
        signer = sn.CloudPacketSigner("super_secret_key")
        signed = signer.sign("123456789")
        ok, payload = signer.verify(signed)
        self.assertTrue(ok)
        self.assertEqual(payload, "123456789")

        guard = sn.AntiCheatGuard(min_val=0, max_val=1000, max_ops_per_sec=5)
        self.assertTrue(guard.check("alice", 500))
        with self.assertRaises(sn.SecurityViolationError):
            guard.check("alice", 99999)

        vault = sn.TokenVault.encrypt("my_session_token", "pass123")
        self.assertEqual(sn.TokenVault.decrypt(vault, "pass123"), "my_session_token")

    def test_project_ast_toolkit(self):
        sample_json = {
            "targets": [
                {"isStage": True, "name": "Stage", "variables": {"v1": ["score", 0]}, "blocks": {}},
                {
                    "isStage": False,
                    "name": "Cat",
                    "variables": {},
                    "blocks": {
                        "b1": {"opcode": "event_whenflagclicked", "topLevel": True, "next": "b2"},
                        "b2": {"opcode": "motion_movesteps", "topLevel": False, "next": None},
                        "dead": {"opcode": "looks_say", "topLevel": True, "next": None},
                    },
                },
            ]
        }
        ast_tool = sn.ProjectJSONToolkit(sample_json)
        self.assertEqual(len(ast_tool.find_orphan_blocks()), 1)
        self.assertEqual(ast_tool.rename_variable("score", "high_score"), 1)
        self.assertIn("class Sprite_Cat:", ast_tool.to_pseudo_python())

    def test_game_server_and_sqlite_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = sn.SQLiteCloudStorage(os.path.join(tmp, "test.db"))
            lb = sn.GlobalLeaderboard(db)
            lb.submit("season1", "PlayerA", 1500)
            lb.submit("season1", "PlayerB", 3200)
            top = lb.get_top("season1", limit=2)
            self.assertEqual(top[0], ("playerb", 3200.0))

            eco = sn.VirtualEconomyLedger(db)
            eco.grant("PlayerA", 500)
            self.assertTrue(eco.transfer("PlayerA", "PlayerB", 200))
            self.assertEqual(eco.balance("PlayerA"), 300)
            self.assertEqual(eco.balance("PlayerB"), 200)


if __name__ == "__main__":
    unittest.main()
