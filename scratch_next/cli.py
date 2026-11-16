"""
scratch_next.cli
================
ターミナルから直接操作できる scratch-next CLI
"""

import json
import argparse
from . import __version__, get_user, get_project, Encoding, AnalyticsToolkit, ScratchUtilities


def main() -> None:
    parser = argparse.ArgumentParser(prog="scratch-next", description=f"scratch-next v{__version__} CLI")
    sub = parser.add_subparsers(dest="cmd")

    p_u = sub.add_parser("user", help="ユーザー情報取得")
    p_u.add_argument("username")

    p_p = sub.add_parser("project", help="プロジェクト統計＆バイラルスコア診断")
    p_p.add_argument("project_id", type=int)

    p_e = sub.add_parser("encode", help="日本語・絵文字対応クラウド数値エンコード")
    p_e.add_argument("text")

    p_d = sub.add_parser("decode", help="クラウド数値デコード")
    p_d.add_argument("digits")

    p_url = sub.add_parser("parse-url", help="Scratch URL解析")
    p_url.add_argument("url")

    args = parser.parse_args()
    if args.cmd == "user":
        u = get_user(args.username)
        u.update()
        print(json.dumps({"username": u.username, "id": u.id, "scratchteam": u.scratchteam, "bio": u.about_me}, ensure_ascii=False, indent=2))
    elif args.cmd == "project":
        p = get_project(args.project_id)
        p.update()
        print(json.dumps({"id": p.id, "title": p.title, "author": p.author, "stats": p.stats, "viral": AnalyticsToolkit.project_viral_metrics(p.stats)}, ensure_ascii=False, indent=2))
    elif args.cmd == "encode":
        print(Encoding.encode(args.text))
    elif args.cmd == "decode":
        print(Encoding.decode(args.digits))
    elif args.cmd == "parse-url":
        print(json.dumps(ScratchUtilities.parse_scratch_url(args.url), ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
