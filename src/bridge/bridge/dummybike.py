#!/usr/bin/env python3
"""
ファイル名：dummybike.py

Robobike 実機がない場合に使用する、ダミーROBOBIKEモジュール

使い方：
    python3 dummybike.py
"""

from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer

class DummyBikeHandler(BaseHTTPRequestHandler):
    """
    ダミーROBOBIKEサーバのリクエストハンドラクラス
    """
    def do_GET(self):
        """
        GETメッセージを処理し、固定のCSVデータを返す
        """
        # URLをパスとクエリ（?以降の部分）に分解
        parsed_url = urlparse(self.path)
        
        # エンドポイントが '/command' かどうかをチェック
        if parsed_url.path == '/command':
            # クエリパラメータを辞書形式に変換
            query_params = parse_qs(parsed_url.query)
            
            # ステータスコード200 (OK) を設定
            self.send_response(200)
                
            # レスポンスのヘッダーを設定（CSVデータであることを指定）
            self.send_header('Content-type', 'text/csv; charset=utf-8')
            self.end_headers()
            
            # 返却する固定のCSVデータ
            csv_data = "b,1042,6,OK,0,20,0.030,12.000,0.030,20,40,0.011,1,0.000,30,0.750,0"
                
            # データをバイト列に変換して送信
            self.wfile.write(csv_data.encode('utf-8'))
            print(f"[DummyBikeHandler] query_params: {query_params}")
            return
        
        # 条件に一致しないアクセス（別のURLなど）の場合は 404 Not Found を返す
        self.send_response(404)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write("Not Found".encode('utf-8'))

def run_dummy_bike():
    port = 8080
    server_address = ('', port)
    
    # サーバーのインスタンスを作成
    httpd = HTTPServer(server_address, DummyBikeHandler)
    print(f"テスト用ダミーサーバを起動しました。ポート番号: {port}")
    print(f"テストURL: http://localhost:{port}/command?..")
    
    try:
        print("Ctrl+Cで停止できます。")
        # サーバーを実行（Ctrl+Cで停止するまで動き続ける）
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバを停止します。")
        httpd.server_close()

if __name__ == "__main__":
    run_dummy_bike()


