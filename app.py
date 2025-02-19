import requests
from flask import Flask, request, Response, send_from_directory

app = Flask(__name__)

@app.route('/')
def index():
    return send_from_directory('', 'index.html')

@app.route('/proxy', methods=['GET'])
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return Response("URL parameter is required", status=400)

    # Ensure the URL starts with http:// or https://
    if not target_url.startswith(('http://', 'https://')):
        return Response("Invalid URL. Please include http:// or https://", status=400)

    try:
        # Set headers to mimic a browser request
        headers = {
            'User -Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        # Make the request to the target URL
        response = requests.get(target_url, headers=headers)
        response.raise_for_status()  # Raises an error for bad responses

        return Response(response.content, status=response.status_code, headers=dict(response.headers))
    except requests.exceptions.HTTPError as http_err:
        return Response(f"HTTP error occurred: {http_err}", status=response.status_code)
    except requests.exceptions.RequestException as req_err:
        return Response(f"Request error occurred: {req_err}", status=500)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
