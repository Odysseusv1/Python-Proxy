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

    try:
        response = requests.get(target_url, proxies={"http": "http://your_proxy:port", "https": "http://your_proxy:port"})
        return Response(response.content, status=response.status_code, headers=dict(response.headers))
    except requests.exceptions.RequestException as e:
        return Response(f"An error occurred: {str(e)}", status=500)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
