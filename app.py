import re
from urllib.parse import urlparse, urlunparse
from flask import Flask, request, abort, Response, redirect
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("app.py")

# Approved hosts for proxying
APPROVED_HOSTS = {"google.com", "www.google.com", "yahoo.com"}

@app.route('/', methods=["GET"])
def index():
    # Return a simple HTML form for URL input
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>URL Proxy</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/4.5.2/css/bootstrap.min.css">
    </head>
    <body>
        <div class="container mt-5">
            <h1 class="text-center">URL Proxy Service</h1>
            <form action="/<path:url>" method="POST" class="mt-4">
                <div class="form-group">
                    <label for="url">Enter URL to Proxy:</label>
                    <input type="text" class="form-control" id="url" name="url" placeholder="e.g., google.com/search?q=example" required>
                </div>
                <button type="submit" class="btn btn-primary btn-block">Proxy URL</button>
            </form>
        </div>
        <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.9.2/dist/umd/popper.min.js"></script>
        <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
    </body>
    </html>
    '''

@app.route('/<path:url>', methods=["GET", "POST"])
def root(url):
    # Handles requests to the root path and redirects to the proxy path
    referer = request.headers.get('referer')
    if not referer:
        return Response("Relative URL sent without a proxying request referral. Please specify a valid proxy host (/p/url)", 400)

    proxy_ref = get_proxied_request_info(referer)
    host = proxy_ref[0]
    redirect_url = f"/p/{host}/{url}"
    if request.query_string:
        redirect_url += f"?{request.query_string.decode('utf-8')}"

    LOG.debug("Redirecting relative path to one under proxy: %s", redirect_url)
    return redirect(redirect_url)

@app.route('/p/<path:url>', methods=["GET", "POST"])
def proxy(url):
    # Fetches the specified URL and streams it to the client
    url_parts = urlparse(f'{request.scheme}://{url}')
    
    # Redirect if the URL has no path
    if not url_parts.path:
        parts = urlparse(request.url)
        LOG.warning("Proxy request without a path was sent, redirecting to '/': %s -> %s/", url, url)
        return redirect(urlunparse(parts._replace(path=parts.path + '/')))

    LOG.debug("%s %s with headers: %s", request.method, url, request.headers)
    response = make_request(url, request.method, dict(request.headers), request.form)
    LOG.debug("Got %s response from %s", response.status_code, url)

    # Stream the response back to the client
    return stream_response(response)

def make_request(url, method, headers=None, data=None):
    # Makes a request to the specified URL and returns the response
    headers = headers or {}
    url = f'http://{url}'

    # Ensure the URL is approved
    if not is_approved(url):
        LOG.warning("URL is not approved: %s", url)
        abort(403)

    # Pass original Referer for subsequent resource requests
    referer = request.headers.get('referer')
    if referer:
        proxy_ref = get_proxied_request_info(referer)
        headers["referer"] = f"http://{proxy_ref[0]}/{proxy_ref[1]}"

    LOG.debug("Sending %s %s with headers: %s and data: %s", method, url, headers, data)
    return requests.request(method, url, params=request.args, stream=True, headers=headers, allow_redirects=False, data=data)

def is_approved(url):
    # Checks if the given URL is allowed to be fetched
    parts = urlparse(url)
    return parts.netloc in APPROVED_HOSTS

def get_proxied_request_info(proxy_url):
    # Extracts information about the target proxied URL from the proxy request
    parts = urlparse(proxy_url)
    if not parts.path or not parts.path.startswith('/p/'):
        return None

    matches = re.match(r'^/p/([^/]+)/?(.*)', parts.path)
    proxied_host = matches.group(1)
    proxied_path = matches.group(2) or '/'
    LOG.debug("Referred by proxy host, uri: %s, %s", proxied_host, proxied_path)
    return proxied_host, proxied_path

def stream_response(response):
    # Streams the response content back to the client
    headers = dict(response.raw.headers)
    def generate():
        for chunk in response.raw.stream(decode_content=False):
            yield chunk
    out = Response(generate(), headers=headers)
    out.status_code = response.status_code
    return out

if __name__ == '__main__':
    app.run(debug=True)
