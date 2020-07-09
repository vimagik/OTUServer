import socket
import os
import threading
import argparse
from urllib.parse import unquote_plus
from datetime import datetime

from myrequest import MyRequest
from myresponse import MyResponse

OK = 200
FORBIDDEN = 403
NOT_FOUND = 404
METHOD_NOT_ALLOWED = 405
INTERNAL_SERVER_ERROR = 500
MIME = {
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'text/javascript',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.swf': 'application/x-shockwave-flash',
}


class MyHTTPServer:
    def __init__(self, host: str, port: int, server_name: str, number_workers: int, doc_root: str):
        self._host = host
        self._port = port
        self._server_name = server_name
        self._number_workers = number_workers
        self._doc_root = doc_root

    def serve_forever(self):
        """Основная работа с сокетами. Обработка запроса через threading"""
        serv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, proto=0)
        try:
            serv_sock.bind((self._host, self._port))
            serv_sock.listen(self._number_workers)
            print(f"Server {self._server_name} started at {self._host}:{self._port}")
            while True:
                conn, _ = serv_sock.accept()
                try:
                    client_handler = threading.Thread(
                        target=self.serve_client,
                        args=(conn,),

                    )
                    client_handler.start()
                except Exception as e:
                    print('Client serving failed', e)
        finally:
            serv_sock.close()

    def serve_client(self, conn: socket):
        """Обработка запроса"""
        try:
            req = self.parse_request(conn)
            resp = self.handle_request(req)
            self.send_response(conn, resp)
        except ConnectionResetError:
            conn = None
        except Exception as e:
            self.send_error(conn, e)
        if conn:
            conn.close()

    def parse_request(self, conn: socket) -> MyRequest:
        """Парсинг шапки запроса"""
        method, target, ver = self.parse_request_line(conn)
        target, args = self.parse_target(target)
        headers = self.parse_headers(conn)
        return MyRequest(method, target, ver, headers, args)

    def parse_request_line(self, conn: socket) -> tuple:
        """Парсинг первой строки запроса"""
        buff = ''
        while '\r\n' not in buff:
            byte = conn.recv(1)
            buff += str(byte, encoding='iso-8859-1')
        words = buff.split()
        if len(words) != 3:
            raise Exception('Request has nonstandard format')
        method, target, ver = words
        return method, target, ver

    def parse_target(self, target: str) -> tuple:
        """Дополнительная обратока target из запроса. Вычищаем путь, читаем аргументы"""
        target = unquote_plus(target)
        args = None
        if '?' in target:
            target, string_args = target.split('?', 1)
            args = {arg.split('=')[0]: arg.split('=')[1] for arg in string_args.split('&')}
        return target, args

    def parse_headers(self, conn: socket) -> dict:
        """Парсинг headers из запроса"""
        headers = []
        while True:
            line = ''
            while '\r\n' not in line:
                byte = conn.recv(1)
                line += str(byte, encoding='iso-8859-1')
            if line in ('\r\n', '\n', ''):
                break
            headers.append(line)
        headers_dict = {h.split(':', 1)[0]: h.split(':', 1)[1] for h in headers}
        return headers_dict

    def handle_request(self, req: MyRequest) -> MyResponse:
        """Основной маршрутизатор запросов"""
        if req.method == 'HEAD':
            return self.handle_head_method(req.target)
        elif req.method == 'GET':
            return self.handle_get_method(req.target)
        return MyResponse(METHOD_NOT_ALLOWED, 'Method not allowed')

    def handle_head_method(self, target: str) -> MyResponse:
        """Обработка HEAD запросов"""
        file_path = self._doc_root + target
        if os.path.exists(file_path):
            _, file_extension = os.path.splitext(file_path)
            headers = {
                'Date': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                'Server': self._server_name,
                'Last-modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%a, %d %b %Y %H:%M:%S GMT'),
                'Content-Type': file_extension,
                'Content-Length': os.path.getsize(file_path),
            }
            return MyResponse(OK, 'Document_follows', headers)
        else:
            headers = {
                'Date': datetime.now().strftime('%a, %d %b %Y %H:%M:%S %Z'),
                'Server': self._server_name,
            }
        return MyResponse(NOT_FOUND, "Document doesn't exist", headers)

    def handle_get_method(self, target: str) -> MyResponse:
        """Обработка GET запросов"""
        path = self._doc_root + target
        if os.path.isdir(path):
            file_path = os.path.join(path, 'index.html')
        else:
            file_path = path
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                body = f.read()
            headers = {
                'Date': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                'Server': self._server_name,
                'Content-Type': self.define_content_type(file_path),
                'Content-Length': os.path.getsize(file_path),
                'Connection': 'Connection: close'
            }
            return MyResponse(OK, "GET", headers, body)
        else:
            headers = {
                'Date': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                'Server': self._server_name,
                'Connection': 'Connection: close'
            }
            return MyResponse(NOT_FOUND, "File not found", headers)

    def define_content_type(self, file_path: str) -> str:
        """Метод по определению Content-Type передаваемого файла"""
        _, file_extension = os.path.splitext(file_path)
        return MIME.get(file_extension)

    def send_response(self, conn: socket, resp: MyResponse):
        """Отправка сообщения"""
        wfile = conn.makefile('wb')
        status_line = f'HTTP/1.1 {resp.status} {resp.reason}\r\n'
        wfile.write(status_line.encode('iso-8859-1'))
        if resp.headers:
            for key, value in resp.headers.items():
                header_line = f'{key}: {value}\r\n'
                wfile.write(header_line.encode('iso-8859-1'))
        wfile.write(b'\r\n')
        if resp.body:
            wfile.write(resp.body)
        wfile.flush()
        wfile.close()

    def send_error(self, conn: socket, error: Exception):
        """Отправка сообщений об ошибках"""
        reason = bytes(str(error), encoding='iso-8859-1')
        body = b'Internal Server Error'
        resp = MyResponse(
            INTERNAL_SERVER_ERROR,
            reason,
            {'Content-Length': len(body)},
            body
        )
        self.send_response(conn, resp)


def parse_args() -> tuple:
    """Парсинг аргументов, переданных в командной строке"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', default=8)
    parser.add_argument('-r', default="http-test-suite-master")
    console_data = parser.parse_args()
    try:
        number_workers = int(console_data.w)
    except:
        number_workers = 8
    return number_workers, console_data.r


if __name__ == "__main__":
    host = 'localhost'
    port = 8000
    server_name = 'OtusHomeTask'
    number_workers, document_root = parse_args()
    serv = MyHTTPServer(host, port, server_name, number_workers, document_root)
    serv.serve_forever()
