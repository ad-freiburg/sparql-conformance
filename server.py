from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import shutil

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def setResponse(self, code, contentType):
        self.send_response(code)
        self.send_header("Content-type", contentType)
        self.end_headers()

    def do_GET(self):
        print(self.path)
        if self.path == "/www/RESULTS.json":
            self.setResponse(200, "application/json")
            with open(self.path[1:], 'rb') as file:
                shutil.copyfileobj(file, self.wfile)
            return
        elif self.path.startswith('/compare='):
            self.setResponse(200, "application/json")
            dict1, dict2 = self.path.split('=')[1].split('+')
            with open("www/RESULTS.json", 'r') as file:
                data = json.load(file)
            result = compare(data[dict1], data[dict2])
            self.wfile.write(json.dumps(result).encode("utf-8"))
            return
        elif self.path == '/www/index.html':
            self.setResponse(200, "text/html")
        elif self.path == '/www/index.css':
            self.setResponse(200, "text/css")
        elif self.path == '/www/index.js' or self.path == '/www/jquery-3.7.1.min.js':
            self.setResponse(200, "application/javascript")
        else:
            self.setResponse(404, "text/html")
            self.wfile.write("404 Not Found".encode("utf-8"))
            return
        with open(self.path[1:], 'rb') as file:
                self.wfile.write(file.read())

def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=8000):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on port {port}...")
    httpd.serve_forever()

def compare(dict1, dict2):
    result = {}
    for testName in dict2:
        for key in dict2[testName]:
            if dict1[testName][key] != dict2[testName][key]:
                if testName not in result:
                    result[testName] = dict1[testName]
                result[testName][key + "-diff"] = dict2[testName][key]
    return result

if __name__ == "__main__":
    run()