import requests
from flask import Flask, request, jsonify
app =  Flask(__name__)

@app.route('/proxy', methods=['GET'])

def proxy():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing url parameter'})
    try:
        response = requests.get(url)
        return (response.content, response.status_code, response.headers.items())
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500
if __name__ == '__main__':
    app.run(port=5000)
