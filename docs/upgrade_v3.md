# IoT 数据平台 v3.0 升级指南

## ⚠️ 升级前必读

本次升级包含数据库结构变更，请务必**先备份数据库**！

### 备份方法（宝塔面板）

1. 登录宝塔面板
2. 进入【数据库】菜单
3. 找到对应的数据库，点击【备份】
4. 或使用 phpMyAdmin 导出数据库

---

## 升级步骤

### 方法一：宝塔面板 Python 项目管理器

#### 1. 安装新依赖

在宝塔面板中：
1. 进入【网站】→ 找到你的 Python 项目 → 点击【设置】
2. 找到【模块】或【依赖管理】
3. 点击【安装模块】，依次安装以下依赖：

```
Flask-Limiter==3.5.0
psutil==5.9.7
openpyxl==3.1.2
```

或者在项目目录下执行：
```bash
cd /www/wwwroot/你的项目目录
pip install -r requirements.txt
```

#### 2. 拉取最新代码

```bash
cd /www/wwwroot/你的项目目录
git pull origin main
```

#### 3. 执行数据库升级

```bash
cd /www/wwwroot/你的项目目录
python upgrade_v3.py
```

#### 4. 重启项目

在宝塔面板中：
1. 进入【网站】→ 找到你的 Python 项目 → 点击【设置】
2. 点击【重启】

---

### 方法二：命令行手动升级

```bash
# 1. 进入项目目录
cd /www/wwwroot/你的项目目录

# 2. 备份数据库
cp data.sqlite data.sqlite.bak
# 或者如果是 MySQL
mysqldump -u用户名 -p数据库名 > backup.sql

# 3. 拉取最新代码
git pull origin main

# 4. 安装新依赖
pip install -r requirements.txt

# 5. 执行数据库升级
python upgrade_v3.py

# 6. 重启服务
# 方法1: 使用 supervisorctl
supervisorctl restart 你的项目名

# 方法2: 使用 gunicorn
pkill gunicorn
gunicorn -c gunicorn.conf.py wsgi:app
```

---

## 新增依赖说明

| 依赖 | 版本 | 用途 |
|------|------|------|
| Flask-Limiter | 3.5.0 | API 限流保护 |
| psutil | 5.9.7 | 系统监控和健康检查 |
| openpyxl | 3.1.2 | Excel 数据导出 |

---

## 数据库变更说明

### 新增数据表

1. **device_group** - 设备分组表
2. **login_log** - 登录日志表
3. **system_config** - 系统配置表

### Device 表新增字段

1. **is_online** - 设备在线状态
2. **last_seen_at** - 最后在线时间

### 新增索引

为提升查询性能，添加了以下索引：
- device(user_id), device(is_online)
- slave_channel(device_id)
- data_point(channel_id), data_point(timestamp)
- alarm_record(user_id), alarm_record(is_read)
- tcp_log(user_id)
- login_log(user_id), login_log(created_at)

---

## 常见问题排查

### 1. 模块找不到错误

**错误信息**: `ModuleNotFoundError: No module named 'xxx'`

**解决方法**:
```bash
pip install xxx
# 或
pip install -r requirements.txt
```

### 2. 数据库迁移错误

**错误信息**: `no such table: device_group`

**解决方法**:
```bash
python upgrade_v3.py
```

### 3. 权限错误

**错误信息**: `Permission denied`

**解决方法**:
```bash
# 给予写入权限
chmod -R 755 /www/wwwroot/你的项目目录
chown -R www:www /www/wwwroot/你的项目目录
```

### 4. 端口冲突

**错误信息**: `Address already in use`

**解决方法**:
```bash
# 查看端口占用
netstat -tunlp | grep 5000
# 杀掉占用进程
kill -9 进程ID
```

### 5. Gunicorn 启动失败

**解决方法**:
检查 gunicorn.conf.py 配置文件：
```python
bind = "0.0.0.0:5000"
workers = 2
timeout = 120
```

---

## 验证升级成功

### 1. 检查健康状态

访问: `http://你的域名/api/health`

应该返回:
```json
{
  "status": "healthy",
  "timestamp": "2024-xx-xxTxx:xx:xx",
  "service": "iot-data-platform"
}
```

### 2. 检查新功能

- 设备分组: `/api/groups`
- 数据导出: `/api/export/data/csv`
- 系统指标: `/api/health/metrics`

### 3. 检查登录日志

登录后在管理后台查看登录日志记录。

---

## 回滚方法

如果升级后出现问题，可以回滚：

```bash
# 1. 恢复数据库
cp data.sqlite.bak data.sqlite
# 或 MySQL
mysql -u用户名 -p数据库名 < backup.sql

# 2. 回滚代码
git reset --hard HEAD~1

# 3. 重启服务
supervisorctl restart 你的项目名
```

---

## 联系支持

如有问题，请在 GitHub 提交 Issue:
https://github.com/Luolong0223/iot-data-platform/issues
