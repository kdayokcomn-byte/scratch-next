"""
scratch_next.ast_tools
======================
F031-F045: project.json AST構造解析・デッドコード検出・変数一括リネーム・疑似Python変換
"""

import re
import hashlib
from typing import Any, Dict, List, Union


class ProjectJSONToolkit:
    def __init__(self, project_json: Dict[str, Any]):
        self.data = project_json

    def inspect_summary(self) -> Dict[str, Any]:
        """F031 & F035: プロジェクト構造診断＆重さスコア算出"""
        targets = self.data.get("targets", [])
        total_blocks = sum(len(t.get("blocks", {})) for t in targets)
        costumes = sum(len(t.get("costumes", [])) for t in targets)
        sounds = sum(len(t.get("sounds", [])) for t in targets)
        cloud_vars = []
        for t in targets:
            for _, v in t.get("variables", {}).items():
                if len(v) >= 3 and v[2] is True:
                    cloud_vars.append(v[0])
        heaviness = total_blocks + costumes * 5 + sounds * 10
        return {
            "sprites": max(0, len(targets) - 1),
            "total_blocks": total_blocks,
            "total_costumes": costumes,
            "total_sounds": sounds,
            "cloud_variables": cloud_vars,
            "extensions": self.data.get("extensions", []),
            "heaviness_score": heaviness,
        }

    def find_orphan_blocks(self) -> List[Dict[str, str]]:
        """F033: イベントハットに未接続の孤立ブロック（死にコード）を抽出"""
        orphans = []
        for t in self.data.get("targets", []):
            sname = t.get("name", "Unknown")
            for bid, b in t.get("blocks", {}).items():
                if isinstance(b, dict) and b.get("topLevel"):
                    op = str(b.get("opcode", ""))
                    if not op.startswith("event_") and not op.startswith("procedures_definition"):
                        orphans.append({"sprite": sname, "block_id": bid, "opcode": op})
        return orphans

    def rename_variable(self, old_name: str, new_name: str) -> int:
        """F034: プロジェクト内の変数定義・参照を一括リネーム"""
        count = 0
        for t in self.data.get("targets", []):
            for vid, v in t.get("variables", {}).items():
                if v[0] == old_name:
                    v[0] = new_name
                    count += 1
            for _, b in t.get("blocks", {}).items():
                if isinstance(b, dict) and "VARIABLE" in b.get("fields", {}):
                    if b["fields"]["VARIABLE"][0] == old_name:
                        b["fields"]["VARIABLE"][0] = new_name
                        count += 1
        return count

    def inject_cloud_variable(self, var_name: str, initial_value: Union[int, str] = 0) -> str:
        """F036: ステージにクラウド変数定義を直接注入"""
        full_name = var_name if var_name.startswith("☁ ") else f"☁ {var_name}"
        var_id = f"sn_cloud_{hashlib.md5(full_name.encode()).hexdigest()[:12]}"
        for t in self.data.get("targets", []):
            if t.get("isStage"):
                t.setdefault("variables", {})[var_id] = [full_name, initial_value, True]
                break
        return var_id

    def to_pseudo_python(self) -> str:
        """F038: スプライトのブロックスクリプトを疑似Pythonコードへトランスパイル"""
        lines = ["# Transpiled by scratch-next ProjectJSONToolkit"]
        for t in self.data.get("targets", []):
            lines.append(f"\nclass Sprite_{re.sub(r'[^a-zA-Z0-9_]', '_', t.get('name', 'Sprite'))}:")
            blocks = t.get("blocks", {})
            hats = [b for b in blocks.values() if isinstance(b, dict) and b.get("topLevel")]
            if not hats:
                lines.append("    pass")
            for idx, h in enumerate(hats):
                lines.append(f"    def script_{idx}_{h.get('opcode', 'hat')}(self):")
                curr_id = h.get("next")
                steps = 0
                while curr_id and curr_id in blocks and steps < 50:
                    blk = blocks[curr_id]
                    lines.append(f"        self.exec('{blk.get('opcode')}')")
                    curr_id = blk.get("next")
                    steps += 1
        return "\n".join(lines)
