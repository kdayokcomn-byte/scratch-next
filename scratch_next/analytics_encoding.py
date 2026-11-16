"""
scratch_next.analytics_encoding
===============================
F091-F100: バイラル予測・相互フォロー抽出・HTMLレポート・日本語/絵文字対応クラウドエンコーダ
"""

import re
import math
import json
import datetime
from typing import Any, Dict, List, Optional, Union


class AnalyticsToolkit:
    """F091/F092/F093: バイラル予測・相互フォロー分析・HTMLレポート出力"""
    @staticmethod
    def project_viral_metrics(stats: Dict[str, int]) -> Dict[str, float]:
        views = max(1, stats.get("views", 1))
        loves = stats.get("loves", 0)
        favs = stats.get("favorites", 0)
        remixes = stats.get("remixes", 0)
        love_rate = loves / views * 100
        fav_rate = favs / views * 100
        viral_score = round(min(100.0, love_rate * 4.0 + fav_rate * 5.0 + math.log10(views) * 10.0), 2)
        return {
            "love_rate": round(love_rate, 2),
            "fav_rate": round(fav_rate, 2),
            "remix_rate": round(remixes / views * 100, 2),
            "viral_score": viral_score,
        }

    @staticmethod
    def find_mutual_follows(followers: List[str], following: List[str]) -> Dict[str, List[str]]:
        f_set = {x.lower() for x in followers}
        g_set = {x.lower() for x in following}
        return {
            "mutual": sorted(f_set & g_set),
            "fans_only": sorted(f_set - g_set),
            "not_following_back": sorted(g_set - f_set),
        }

    @staticmethod
    def export_html_report(title: str, metrics: Dict[str, Any], output_path: str = "scratch_report.html") -> str:
        rows = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in metrics.items())
        html = f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:sans-serif;background:#0f172a;color:#f8fafc;padding:2rem}}
table{{border-collapse:collapse;width:100%;max-width:640px;background:#1e293b;border-radius:8px;overflow:hidden}}
th,td{{padding:12px 16px;border-bottom:1px solid #334155;text-align:left}}th{{color:#38bdf8}}</style>
</head><body><h1>📊 {title}</h1><table>{rows}</table></body></html>"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return output_path


class Encoding:
    """F094: Unicode(日本語・絵文字)対応10進エンコーダ / F095: JSON直接パック / F096: 2DマップRLE圧縮"""
    _CHARS = (
        " abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789!@#$%^&*()-_=+[]{}|;:',.<>/?`~\"\n"
    )

    @classmethod
    def encode(cls, text: str) -> str:
        out = []
        for ch in str(text):
            idx = cls._CHARS.find(ch)
            if idx != -1:
                out.append(f"{idx + 1:02d}")
            else:
                hex_str = ch.encode("utf-8").hex()
                encoded_hex = "".join(f"{int(h, 16) + 10:02d}" for h in hex_str)
                out.append(f"99{len(encoded_hex):02d}{encoded_hex}")
        return "".join(out)

    @classmethod
    def decode(cls, digits: Union[str, int]) -> str:
        s = str(digits)
        res = []
        i, n = 0, len(s)
        while i + 1 < n:
            code = int(s[i : i + 2])
            i += 2
            if code == 0:
                break
            if code == 99 and i + 1 < n:
                blen = int(s[i : i + 2])
                i += 2
                hchars = []
                for _ in range(blen // 2):
                    if i + 1 >= n:
                        break
                    hchars.append(f"{int(s[i : i + 2]) - 10:x}")
                    i += 2
                try:
                    res.append(bytes.fromhex("".join(hchars)).decode("utf-8"))
                except Exception:
                    res.append("?")
            elif 1 <= code <= len(cls._CHARS):
                res.append(cls._CHARS[code - 1])
        return "".join(res)

    @classmethod
    def encode_json(cls, data: Any) -> str:
        return cls.encode(json.dumps(data, separators=(",", ":"), ensure_ascii=False))

    @classmethod
    def decode_json(cls, digits: Union[str, int]) -> Any:
        return json.loads(cls.decode(digits))

    @classmethod
    def encode_rle_grid(cls, grid: List[List[int]]) -> str:
        flat = [c for row in grid for c in row]
        if not flat:
            return ""
        out, cur, cnt = [], flat[0], 1
        for v in flat[1:]:
            if v == cur and cnt < 99:
                cnt += 1
            else:
                out.append(f"{cnt:02d}{cur:02d}")
                cur, cnt = v, 1
        out.append(f"{cnt:02d}{cur:02d}")
        return "".join(out)


class ScratchUtilities:
    """F097-F100: HEX→ペン色変換 / 2000年経過日数 / URLパーサー / ユーザー名検証"""
    @staticmethod
    def hex_to_scratch_hue(hex_color: str) -> int:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0
        mx, mn = max(r, g, b), min(r, g, b)
        df = mx - mn
        if df == 0:
            hue = 0.0
        elif mx == r:
            hue = (60 * ((g - b) / df) + 360) % 360
        elif mx == g:
            hue = (60 * ((b - r) / df) + 120) % 360
        else:
            hue = (60 * ((r - g) / df) + 240) % 360
        return round(hue / 360.0 * 100)

    @staticmethod
    def days_since_2000() -> float:
        epoch_2000 = datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        return (now - epoch_2000).total_seconds() / 86400.0

    @staticmethod
    def parse_scratch_url(url: str) -> Dict[str, Optional[str]]:
        m_proj = re.search(r"scratch\.mit\.edu/projects/(\d+)", url)
        if m_proj:
            return {"type": "project", "id": m_proj.group(1)}
        m_stud = re.search(r"scratch\.mit\.edu/studios/(\d+)", url)
        if m_stud:
            return {"type": "studio", "id": m_stud.group(1)}
        m_user = re.search(r"scratch\.mit\.edu/users/([a-zA-Z0-9_-]+)", url)
        if m_user:
            return {"type": "user", "id": m_user.group(1)}
        return {"type": None, "id": None}

    @staticmethod
    def is_valid_username(username: str) -> bool:
        return bool(re.fullmatch(r"[a-zA-Z0-9_-]{3,20}", username))
