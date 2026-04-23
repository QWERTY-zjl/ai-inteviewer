from flask import Flask

app = Flask(__name__)

@app.route('/api/test')
def test():
    return {'message': 'Hello, World!'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10006, debug=True, threaded=True)