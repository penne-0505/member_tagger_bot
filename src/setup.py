import os

from db_handler import DBHandler

# TODO: setup.pyの実装

def fetch_contexts(lang: str) -> tuple[str]:
    if lang == any('ja', 'jp', 'jpn'):
        pass
    elif lang == any('en', 'us', 'uk', 'en-us', 'en-uk'):
        pass
    else:
        pass

def setup():
    # 環境変数の設定(確認)と、awsのテーブル作成を行うCLI
    pass