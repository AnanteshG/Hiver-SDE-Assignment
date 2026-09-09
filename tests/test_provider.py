import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch
from hiver_support.provider import Provider


class ProviderTests(unittest.TestCase):
    def test_real_transport_and_cache_without_paid_calls(self):
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                calls.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers()
                self.wfile.write(json.dumps({'model':'test-local','choices':[{'message':{'content':'{"ok":true}'}}],
                                            'usage':{'total_tokens':7}}).encode())
            def log_message(self,*args): pass
        server=HTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as cache, patch.dict(os.environ,{'LLM_API_KEY':''}):
                provider=Provider(model='test-local',base_url=f'http://127.0.0.1:{server.server_port}',cache_dir=cache)
                first=provider.complete('Return JSON.',{'message':'test fixture'})
                second=provider.complete('Return JSON.',{'message':'test fixture'})
                self.assertEqual(first['output'],{'ok':True})
                self.assertTrue(second['cache_hit'])
                self.assertEqual(len(calls),1)
        finally:
            server.shutdown(); server.server_close(); thread.join()
