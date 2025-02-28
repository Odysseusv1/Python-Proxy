import re
from urllib.parse import urlparse, urlunparse
from flask import Flask, request, abort, Response, redirect, render_template
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("app.py")

# Approved hosts for proxying
APPROVED_HOSTS = {"google.com", "www.google.com", "yahoo.com"}

@app.route('/', methods=["GET"])
def index():
    # Return the HTML form for URL input
    return render_template('index.html')

@app.route('/<path:url>', methods=["GET", "POST"])
def root(url):
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
    url_parts = urlparse(f'{request.scheme}://{url}')
    if not url_parts.path:
        parts = urlparse(request.url)
        LOG.warning("Proxy request without a path was sent, redirecting to '/': %s -> %s/", url, url)
        return redirect(urlunparse(parts._replace(path=parts.path + '/')))

    LOG.debug("%s %s with headers: %s", request.method, url, request.headers)
    response = make_request(url, request.method, dict(request.headers), request.form)
    LOG.debug("Got %s response from %s", response.status_code, url)

    return stream_response(response)

def make_request(url, method, headers=None, data=None):
    headers = headers or {}
    url = f'http://{url}'

    if not is_approved(url):
        LOG.warning("URL is not approved: %s", url)
        abort(403)

    referer = request.headers.get('referer')
    if referer:
        proxy_ref = get_proxied_request_info(referer)
        headers["referer"] = f"http://{proxy_ref[0]}/{proxy_ref[1]}"

    LOG.debug("Sending %s %s with headers: %s and data: %s", method, url, headers, data)
    return requests.request(method, url, params=request.args, stream=True, headers=headers, allow_redirects=False, data=data)

def is_approved(url):
    parts = urlparse(url)
    return parts.netloc in APPROVED_HOSTS

def get_proxied_request_info(proxy_url):
    parts = urlparse(proxy_url)
    if not parts.path or not parts.path.startswith('/p/'):
        return None

    matches = re.match(r'^/p/([^/]+)/?(.*)', parts.path)
    proxied_host = matches.group(1)
    proxied_path = matches.group(2) or '/'
    LOG.debug("Referred by proxy host, uri: %s, %s", proxied_host, proxied_path)
    return proxied_host, proxied_path

def stream_response(response):
    headers = dict(response.raw.headers)
    def generate():
        for chunk in response.raw.stream(decode_content=False):
            yield chunk
    out = Response(generate(), headers=headers)
    out.status_code = response.status_code
    return out

if __name__ == '__main__':
    app.run(debug=True)
