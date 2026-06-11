import os
import sys
from app import create_app

app = create_app()

if __name__ == '__main__':
    # TCP 服务器已在 create_app() 中自动启动
    # 启动 Flask Web 服务（禁用 reloader 避免重复启动 TCP）
    app.run(host='0.0.0.0', port=9102, debug=True, use_reloader=False)
