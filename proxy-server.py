import ssl
import socket
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import json

class ProxyHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle HTTP requests from the frontend."""
        if self.path.startswith('/proxy'):
            url = self.path.split('?url=')[1]
            if url:
                # Decode URL and forward the request
                decoded_url = urlparse(url)
                try:
                    # Forward the request to the target server
                    response = requests.get(decoded_url.geturl(), verify=False)
                    self.send_response(response.status_code)
                    for header, value in response.headers.items():
                        if header.lower() != 'content-encoding':
                            self.send_header(header, value)
                    self.end_headers()
                    self.wfile.write(response.content)
                except Exception as e:
                    self.send_error(500, 'Internal Server Error', str(e))
            else:
                self.send_error(400, 'Bad Request', 'No URL provided')
        else:
            self.send_error(404, 'Not Found')

def run_https_proxy():
    """Run the HTTPS Proxy server."""
    server_address = ('', 443)
    httpd = HTTPServer(server_address, ProxyHTTPRequestHandler)

    # Wrap the server in SSL
    httpd.socket = ssl.wrap_socket(httpd.socket, keyfile="server.key", certfile="server.crt", server_side=True)

    print('Starting HTTPS proxy on port 443...')
    httpd.serve_forever()

if __name__ == "__main__":
    run_https_proxy()
