#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X API 初回認証セットアップスクリプト
=====================================
このスクリプトを1度だけ実行して、OAuth 1.0a のアクセストークンを取得します。
取得したトークンを config.yaml の access_token / access_token_secret に設定してください。

使い方:
    python3 auth_setup.py
"""

import yaml
import tweepy
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "config.yaml"


def main():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    api_conf = config["api"]
    consumer_key = api_conf["client_id"]
    consumer_secret = api_conf["client_secret"]

    if consumer_key == "YOUR_CLIENT_ID":
        print("エラー: config.yaml の client_id と client_secret を先に設定してください。")
        return

    # OAuth 1.0a ハンドラー
    auth = tweepy.OAuth1UserHandler(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        callback="oob"  # PIN ベース認証
    )

    try:
        auth_url = auth.get_authorization_url()
        print("=" * 60)
        print("以下のURLをブラウザで開いて、Xにログインしてください:")
        print(f"\n  {auth_url}\n")
        print("認証後に表示される PIN コードを入力してください:")
        pin = input("PIN: ").strip()

        auth.get_access_token(pin)

        print("\n" + "=" * 60)
        print("認証成功！以下のトークンを config.yaml に設定してください:")
        print(f"\n  access_token:        {auth.access_token}")
        print(f"  access_token_secret: {auth.access_token_secret}")
        print("\nconfig.yaml の該当箇所を更新したら、auto_like.py を実行できます。")
        print("=" * 60)

    except tweepy.TweepyException as e:
        print(f"認証エラー: {e}")


if __name__ == "__main__":
    main()
