import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from tcp_server import run_tcp_server
from services.tcp_handler import TcpConnectionHandler

application = create_app()

# 启动TCP服务器后台线程
run_tcp_server(application, TcpConnectionHandler)

if __name__ == '__main__':
    application.run()
