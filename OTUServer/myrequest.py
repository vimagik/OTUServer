class MyRequest:
    def __init__(self, method, target, ver, headers, args):
        self.method = method
        self.target = target
        self.ver = ver
        self.headers = headers
        self.args = args
