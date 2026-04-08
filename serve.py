import http.server
import webbrowser

PORT = 8000

handler = http.server.SimpleHTTPRequestHandler
print(f"Serving at http://localhost:{PORT}/frontend/")
webbrowser.open(f"http://localhost:{PORT}/frontend/")
with http.server.HTTPServer(("", PORT), handler) as httpd:
    httpd.serve_forever()
