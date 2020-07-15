import socket
import os
import argparse
import mimetypes
from urllib.parse import unquote_plus
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from myrequest import MyRequest
from myresponse import MyResponse

OK = 200
FORBIDDEN = 403
NOT_FOUND = 404
METHOD_NOT_ALLOWED = 405
INTERNAL_SERVER_ERROR = 500


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
            executor = ThreadPoolExecutor(max_workers=self._number_workers)
            print(f"Server {self._server_name} started at {self._host}:{self._port}")
            while True:
                conn, _ = serv_sock.accept()
                conn.settimeout(10)
                try:
                    executor.submit(self.serve_client, conn)
                except Exception as e:
                    print('Client serving failed', e)
        finally:
            serv_sock.close()

    def serve_client(self, conn: socket):
        """Обработка запроса"""
        try:
            buff = self.read_request(conn)
            req = self.parse_request(buff)
            resp = self.handle_request(req)
            self.send_response(conn, resp)
        except ConnectionResetError:
            conn = None
        except Exception as e:
            self.send_error(conn, e)
        if conn:
            conn.close()

    def read_request(self, conn: socket) -> str:
        """Читаем запрос из сокета"""
        buff = ''
        while '\n\n' not in buff:
            data = conn.recv(1024)
            if data is None:
                raise ConnectionResetError
            buff += str(data, encoding='iso-8859-1').replace('\r\n', '\n')
        return buff

    def parse_request(self, buff: str) -> MyRequest:
        """Парсинг запроса"""
        buff = buff.split('\n')
        request_line = buff[0].split()
        if len(request_line) != 3:
            raise Exception('Request has nonstandard format')
        method, target, ver = request_line
        headers_dict = {h.split(':', 1)[0]: h.split(':', 1)[1] for h in buff[1:] if ':' in h}
        target, args = self.parse_target(target)
        return MyRequest(method, target, ver, headers_dict, args)

    def parse_target(self, target: str) -> tuple:
        """Дополнительная обратока target из запроса. Вычищаем путь, читаем аргументы"""
        target = unquote_plus(target)
        args = None
        if '?' in target:
            target, string_args = target.split('?', 1)
            args = {arg.split('=')[0]: arg.split('=')[1] for arg in string_args.split('&')}
        return target, args

    def handle_request(self, req: MyRequest) -> MyResponse:
        """Основной маршрутизатор запросов"""
        if req.method == 'HEAD':
            return self.handle_head_method(req.target)
        elif req.method == 'GET':
            return self.handle_get_method(req.target)
        return MyResponse(METHOD_NOT_ALLOWED, 'Method not allowed')

    def create_headers(self, **kwargs) -> dict:
        """Конструируем headers для ответа"""
        headers = {
            'Date': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'Server': self._server_name,
        }
        for key, value in kwargs.items():
            head_paramm = key.replace('_', '-')
            headers[head_paramm] = value
        return headers

    def handle_head_method(self, target: str) -> MyResponse:
        """Обработка HEAD запросов"""
        file_path = os.path.abspath(self._doc_root + target)
        if os.path.exists(file_path):
            _, file_extension = os.path.splitext(file_path)
            headers = self.create_headers(
                Last_modified=datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%a, %d %b %Y %H:%M:%S GMT'),
                Content_Type=file_extension,
                Content_Length=os.path.getsize(file_path)
            )
            resp = MyResponse(OK, 'Document_follows', headers)
        else:
            headers = self.create_headers()
            resp = MyResponse(NOT_FOUND, "Document doesn't exist", headers)
        return resp

    def handle_get_method(self, target: str) -> MyResponse:
        """Обработка GET запросов"""
        path = os.path.abspath(self._doc_root + target)
        if os.path.isdir(path):
            file_path = os.path.join(path, 'index.html')
        else:
            file_path = path
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                body = f.read()
            headers = self.create_headers(
                Content_Type=self.define_content_type(file_path),
                Content_Length=os.path.getsize(file_path),
                Connection='Connection: close'
            )
            resp = MyResponse(OK, "GET", headers, body)
        else:
            headers = self.create_headers(Connection='Connection: close')
            resp = MyResponse(NOT_FOUND, "File not found", headers)
        return resp

    def define_content_type(self, file_path: str) -> str:
        """Метод по определению Content-Type передаваемого файла"""
        _, file_extension = os.path.splitext(file_path)
        return mimetypes.types_map[file_extension]

    def send_response(self, conn: socket, resp: MyResponse):
        """Отправка сообщения"""
        status_line = f'HTTP/1.1 {resp.status} {resp.reason}\r\n'
        data = status_line.encode('iso-8859-1')
        if resp.headers:
            for key, value in resp.headers.items():
                header_line = f'{key}: {value}\r\n'
                data += header_line.encode('iso-8859-1')
        data += b'\r\n'
        if resp.body:
            data += resp.body
        conn.sendall(data)

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
    parser.add_argument('-w', default=1024)
    parser.add_argument('-r', default="http-test-suite-master")
    console_data = parser.parse_args()
    try:
        number_workers = int(console_data.w)
    except:
        number_workers = 1024
    return number_workers, console_data.r


if __name__ == "__main__":
    host = 'localhost'
    port = 8000
    server_name = 'OtusHomeTask'
    number_workers, document_root = parse_args()
    serv = MyHTTPServer(host, port, server_name, number_workers, document_root)
    serv.serve_forever()
