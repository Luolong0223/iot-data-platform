# 宝塔面板部署指南（Windows Server 2019）

本文档详细介绍如何在 Windows Server 2019 上使用宝塔面板部署 IoT 数据可视化平台。

## 目录

- [环境准备](#环境准备)
- [宝塔面板安装](#宝塔面板安装)
- [部署步骤](#部署步骤)
- [环境变量配置](#环境变量配置)
- [故障排查](#故障排查)
- [备份与维护](#备份与维护)

---

## 环境准备

### 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows Server 2019（标准版/数据中心版） |
| 内存 | 最低 4GB，推荐 8GB 及以上 |
| 磁盘 | 最低 20GB 可用空间 |
| 网络 | 固定内网/公网 IP，可访问互联网 |

### 软件依赖

| 软件 | 版本 | 说明 |
|------|------|------|
| Python | 3.9+ | 宝塔面板中安装 |
| MySQL | 5.7+ 或 8.0 | 生产环境数据库，宝塔中安装 |
| Nginx | 1.20+ | 反向代理，宝塔中安装 |
| 宝塔面板 | 最新版 | Windows 版宝塔 |

> **注意**：本项目在开发环境使用 SQLite，生产环境强烈建议切换为 MySQL 以获得更好的并发性能与数据可靠性。

---

## 宝塔面板安装

### 1. 下载并安装宝塔 Windows 版

访问宝塔官网下载 Windows 版安装包，或在服务器浏览器中访问：

```
https://www.bt.cn/new/download.html
```

下载后双击安装，安装过程中记住面板地址、用户名和密码。

### 2. 登录宝塔面板

安装完成后，在浏览器中访问：

```
http://服务器IP:8888
```

使用安装时提供的账号密码登录，首次登录会提示绑定宝塔账号，按提示完成即可。

---

## 部署步骤

### a. 安装 Python 环境

1. 登录宝塔面板，点击左侧菜单 **"软件商店"**
2. 在搜索框中输入 **"Python"**，找到 **"Python 项目管理器"** 或 **"Python 3.9"**
3. 点击 **安装**，等待安装完成
4. 安装完成后，打开服务器命令行（宝塔终端或远程桌面），确认 Python 版本：

```cmd
python --version
```

应显示 `Python 3.9.x` 或更高版本。

### b. 创建网站并上传代码

1. 在宝塔面板中，点击左侧 **"网站"**，然后点击 **"添加站点"**
2. 填写站点信息：
   - **域名**：填写你的域名，如 `iot.example.com`，或直接使用服务器 IP
   - **根目录**：设置为 `C:/wwwroot/iot-data-platform`
   - **PHP 版本**：选择 **纯静态**
   - 点击 **提交**

3. 上传项目代码：
   - 点击站点根目录进入文件管理器
   - 点击 **上传**，将本地项目压缩包（`iot-data-platform.zip`）上传
   - 上传完成后右键解压，确保目录结构如下：

```
C:/wwwroot/iot-data-platform/
├── app.py
├── tcp_server.py
├── config.py
├── requirements.txt
├── run.py
├── wsgi.py
├── models/
├── routes/
├── services/
├── static/
├── templates/
└── docs/
```

### c. 安装依赖

1. 在宝塔面板中打开 **终端**，或远程桌面连接到服务器
2. 进入项目目录：

```cmd
cd C:\wwwroot\iot-data-platform
```

3. 创建虚拟环境（推荐）：

```cmd
python -m venv venv
venv\Scripts\activate
```

4. 安装项目依赖：

```cmd
pip install -r requirements.txt
```

安装完成后，确认所有包安装成功：

```cmd
pip list
```

### d. 初始化数据库

#### 方式一：使用 MySQL（推荐生产环境）

1. 在宝塔面板中，点击 **"数据库"** → **"添加数据库"**
2. 填写数据库信息：
   - **数据库名**：`iot_platform`
   - **用户名**：`iot_user`
   - **密码**：设置强密码，如 `YourStrongP@ssw0rd`
   - **权限**：本地服务器

3. 修改项目配置文件，使用 MySQL：

编辑 `config.py` 中的数据库连接，或在服务器环境变量中设置：

```cmd
set DATABASE_URL=mysql+pymysql://iot_user:YourStrongP@ssw0rd@localhost:3306/iot_platform
```

> 注意：使用 MySQL 时需要额外安装 PyMySQL：`pip install pymysql`

4. 初始化数据表：

```cmd
cd C:\wwwroot\iot-data-platform
venv\Scripts\activate
python -c "from app import app; from models.database import db; app.app_context().push(); db.create_all()"
```

#### 方式二：使用 SQLite（简单测试）

如果不使用 MySQL，SQLite 无需额外配置，直接运行初始化命令即可：

```cmd
cd C:\wwwroot\iot-data-platform
venv\Scripts\activate
python -c "from app import app; from models.database import db; app.app_context().push(); db.create_all()"
```

数据库文件将生成在项目目录下的 `database.db`。

### e. 配置 Gunicorn

1. 确认 Gunicorn 已安装（在 `requirements.txt` 中已包含）

2. 创建 Gunicorn 启动脚本 `start_gunicorn.bat`，放在项目根目录：

```bat
@echo off
cd C:\wwwroot\iot-data-platform
venv\Scripts\activate
gunicorn -w 4 -b 127.0.0.1:5000 --timeout 120 --access-logfile logs/access.log --error-logfile logs/error.log wsgi:app
```

3. 创建日志目录：

```cmd
mkdir C:\wwwroot\iot-data-platform\logs
```

4. 手动测试启动 Gunicorn：

```cmd
cd C:\wwwroot\iot-data-platform
start_gunicorn.bat
```

看到类似以下输出表示启动成功：

```
[2024-01-01 12:00:00 +0800] [1234] [INFO] Starting gunicorn 21.2.0
[2024-01-01 12:00:00 +0800] [1234] [INFO] Listening at: http://127.0.0.1:5000 (1234)
```

按 `Ctrl+C` 停止测试运行。

### f. 配置 Nginx 反向代理

1. 在宝塔面板中，点击 **"网站"**，找到刚才创建的站点，点击 **"设置"**
2. 点击 **"配置文件"**，在 `server` 块中添加反向代理配置：

```nginx
location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}

location /static/ {
    alias C:/wwwroot/iot-data-platform/static/;
    expires 30d;
}
```

3. 如果启用了 HTTPS，在 `server` 块中（443 端口）同样添加上述配置，并确保证书已正确配置。

4. 点击 **保存**，然后点击 **"服务"** → **"重载配置"**

5. 测试访问：`http://你的域名或IP/`，应能看到登录页面。

### g. 配置 Supervisor 守护 TCP 服务器

宝塔 Windows 版不自带 Supervisor，但可以通过 **"计划任务"** 或 **Windows 服务** 实现守护进程。

#### 方案一：使用宝塔计划任务（推荐）

1. 创建 TCP 启动脚本 `start_tcp.bat`：

```bat
@echo off
cd C:\wwwroot\iot-data-platform
venv\Scripts\activate
python tcp_server.py
```

2. 在宝塔面板中，点击 **"计划任务"**
3. 点击 **"添加计划任务"**：
   - **任务类型**：选择 **"运行Shell脚本"**
   - **任务名称**：`iot_tcp_server`
   - **执行周期**：选择 **"每分钟"**
   - **脚本内容**：

```bat
tasklist | findstr "python.exe" | findstr "tcp_server" >nul
if errorlevel 1 (
    start /min C:\wwwroot\iot-data-platform\start_tcp.bat
)
```

4. 点击 **添加任务**

5. 手动首次启动 TCP 服务器：

```cmd
start C:\wwwroot\iot-data-platform\start_tcp.bat
```

#### 方案二：使用 NSSM 创建 Windows 服务（更稳定）

1. 下载 NSSM（Non-Sucking Service Manager）：

```cmd
cd C:\tools
curl -L -o nssm.zip https://nssm.cc/release/nssm-2.24.zip
```

2. 解压后，将 `nssm.exe` 放入系统 PATH，如 `C:\Windows\System32`

3. 创建 TCP 服务：

```cmd
nssm install IoTTcpServer
```

在弹出的窗口中配置：
- **Path**：`C:\wwwroot\iot-data-platform\venv\Scripts\python.exe`
- **Startup directory**：`C:\wwwroot\iot-data-platform`
- **Arguments**：`tcp_server.py`

4. 启动服务：

```cmd
nssm start IoTTcpServer
```

5. 设置开机自启：

```cmd
sc config IoTTcpServer start= auto
```

同样为 Gunicorn 创建服务：

```cmd
nssm install IoTWebServer
```

配置：
- **Path**：`C:\wwwroot\iot-data-platform\venv\Scripts\gunicorn.exe`
- **Startup directory**：`C:\wwwroot\iot-data-platform`
- **Arguments**：`-w 4 -b 127.0.0.1:5000 --timeout 120 wsgi:app`

```cmd
nssm start IoTWebServer
sc config IoTWebServer start= auto
```

### h. 防火墙设置

#### Windows 防火墙配置

1. 打开 **Windows Defender 防火墙** → **高级设置**
2. 点击 **"入站规则"** → **"新建规则"**
3. 为以下端口添加允许规则：

| 端口 | 用途 | 规则名称 |
|------|------|----------|
| 80 | HTTP 访问 | IoT_HTTP |
| 443 | HTTPS 访问 | IoT_HTTPS |
| 5000 | Gunicorn（本地，可不开放） | IoT_Gunicorn |
| 9000-9100 | TCP 数据接收端口范围 | IoT_TCP_Data |

4. 以开放 9000-9100 为例，新建规则步骤：
   - **规则类型**：端口
   - **协议和端口**：TCP，特定本地端口 `9000-9100`
   - **操作**：允许连接
   - **配置文件**：域、专用、公用（根据网络环境选择）
   - **名称**：`IoT_TCP_Data`
   - **描述**：`IoT 平台 TCP 数据接收端口`

#### 宝塔面板防火墙

1. 在宝塔面板左侧点击 **"安全"**
2. 在 **"系统防火墙"** 中，点击 **"添加规则"**
3. 放行以下端口：
   - 端口 `80`，协议 TCP，备注 `HTTP`
   - 端口 `443`，协议 TCP，备注 `HTTPS`
   - 端口 `9000-9100`，协议 TCP，备注 `TCP数据端口`

#### 云服务器安全组（如适用）

如果使用阿里云、腾讯云等云服务器，还需要在控制台的安全组中放行上述端口。

---

## 环境变量配置

生产环境建议通过环境变量或 `.env` 文件配置敏感信息，避免硬编码在代码中。

### 必需的环境变量

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `SECRET_KEY` | Flask 密钥，用于会话加密 | `your-random-secret-key-32chars` |
| `DATABASE_URL` | 数据库连接字符串 | `mysql+pymysql://iot_user:pass@localhost/iot_platform` |
| `TCP_HOST` | TCP 服务器监听地址 | `0.0.0.0` |
| `TCP_BASE_PORT` | TCP 起始端口 | `9000` |
| `ADMIN_USERNAME` | 默认管理员用户名 | `admin` |
| `ADMIN_PASSWORD` | 默认管理员密码 | `YourSecureAdminPass` |

### 在 Windows 中设置环境变量

#### 方式一：系统环境变量（推荐）

1. 右键 **"此电脑"** → **"属性"** → **"高级系统设置"**
2. 点击 **"环境变量"**
3. 在 **"系统变量"** 中点击 **"新建"**，添加上述变量
4. 重启服务器或相关服务使配置生效

#### 方式二：宝塔终端临时设置

```cmd
set SECRET_KEY=your-random-secret-key-32chars
set DATABASE_URL=mysql+pymysql://iot_user:YourStrongP@ssw0rd@localhost:3306/iot_platform
set TCP_HOST=0.0.0.0
set TCP_BASE_PORT=9000
set ADMIN_USERNAME=admin
set ADMIN_PASSWORD=YourSecureAdminPass
```

> **注意**：`set` 命令仅在当前终端会话有效，重启后失效。生产环境请使用系统环境变量或 NSSM 服务环境变量配置。

#### 方式三：NSSM 服务环境变量

如果使用 NSSM 部署，可以在安装服务时配置环境变量：

```cmd
nssm edit IoTTcpServer
nssm edit IoTWebServer
```

在 **Environment** 选项卡中添加键值对。

---

## 故障排查

### 问题一：Gunicorn 无法启动

**现象**：访问网站提示 502 Bad Gateway。

**排查步骤**：

1. 检查 Gunicorn 是否运行：

```cmd
tasklist | findstr gunicorn
```

2. 查看错误日志：

```cmd
type C:\wwwroot\iot-data-platform\logs\error.log
```

3. 常见原因与解决：
   - **端口被占用**：修改 `start_gunicorn.bat` 中的端口，并同步修改 Nginx 配置
   - **依赖缺失**：重新运行 `pip install -r requirements.txt`
   - **权限不足**：确保运行用户对项目目录有读写权限

### 问题二：TCP 服务器无法接收数据

**现象**：设备发送数据后，平台没有显示新数据。

**排查步骤**：

1. 检查 TCP 服务器进程是否存在：

```cmd
tasklist | findstr python
```

2. 检查端口监听状态：

```cmd
netstat -an | findstr 9000
```

3. 检查 Windows 防火墙是否放行对应端口
4. 检查宝塔安全设置是否放行端口
5. 查看 TCP 日志（如有配置）确认是否收到连接

### 问题三：数据库连接失败

**现象**：页面报错 `OperationalError` 或 `Can't connect to MySQL server`。

**排查步骤**：

1. 确认 MySQL 服务已启动（宝塔 **"数据库"** 页面查看）
2. 确认数据库用户名、密码、数据库名正确
3. 确认 `DATABASE_URL` 环境变量已正确设置
4. 测试连接：

```cmd
mysql -u iot_user -p -h localhost
```

### 问题四：静态文件 404

**现象**：页面样式丢失，CSS/JS 文件无法加载。

**解决**：

1. 检查 Nginx 配置中 `location /static/` 的路径是否正确指向项目 `static` 目录
2. 检查 Windows 路径分隔符，确保使用 `/` 或正确转义的 `\`
3. 确认 `static` 目录及文件存在且 IIS 未占用 80 端口

### 问题五：Nginx 启动失败

**现象**：宝塔中 Nginx 显示停止状态，无法启动。

**排查步骤**：

1. 检查 80/443 端口是否被占用：

```cmd
netstat -ano | findstr :80
```

2. 如果被 IIS 占用，停止 IIS 服务：

```cmd
iisreset /stop
sc config W3SVC start= disabled
```

3. 重新启动 Nginx

---

## 备份与维护

### 数据库备份

#### MySQL 备份

1. 宝塔面板自动备份：
   - 点击 **"数据库"** → 找到 `iot_platform` → **"备份"**
   - 设置自动备份周期（建议每天）

2. 手动命令行备份：

```cmd
mysqldump -u iot_user -p iot_platform > C:\backups\iot_platform_%date:~0,4%%date:~5,2%%date:~8,2%.sql
```

#### SQLite 备份

直接复制数据库文件：

```cmd
copy C:\wwwroot\iot-data-platform\database.db C:\backups\database_%date:~0,4%%date:~5,2%%date:~8,2%.db
```

### 项目代码备份

```cmd
cd C:\wwwroot
zip -r C:\backups\iot-data-platform_%date:~0,4%%date:~5,2%%date:~8,2%.zip iot-data-platform -x "iot-data-platform/venv/*" "iot-data-platform/__pycache__/*"
```

### 日志清理

定期清理日志文件避免磁盘占满：

```cmd
forfiles /p C:\wwwroot\iot-data-platform\logs /s /m *.log /d -30 /c "cmd /c del @path"
```

### 服务重启维护

```cmd
:: 重启 Web 服务
nssm restart IoTWebServer

:: 重启 TCP 服务
nssm restart IoTTcpServer

:: 重载 Nginx（宝塔面板中操作或命令行）
nginx -s reload
```

### 定期检查清单

- [ ] 每周检查磁盘空间使用率
- [ ] 每周检查数据库备份是否成功
- [ ] 每月更新系统补丁与宝塔面板版本
- [ ] 每月检查并清理过期日志
- [ ] 每季度更换管理员密码
- [ ] 每季度检查防火墙规则

---

## 附录：一键部署脚本参考

以下脚本供参考，可根据实际环境调整：

```bat
@echo off
chcp 65001 >nul
echo ===== IoT 平台部署脚本 =====

cd C:\wwwroot\iot-data-platform

:: 激活虚拟环境
call venv\Scripts\activate

:: 安装/更新依赖
pip install -r requirements.txt

:: 初始化数据库
python -c "from app import app; from models.database import db; app.app_context().push(); db.create_all()"

:: 启动服务
echo 正在启动 Web 服务...
start /min start_gunicorn.bat

echo 正在启动 TCP 服务...
start /min start_tcp.bat

echo ===== 部署完成 =====
pause
```

---

如有其他问题，请参考项目 [README.md](../README.md) 或 [API 文档](api.md)。
