# Multica WeChat Verification Code Monitor

监控 Multica 平台的验证码日志，并将目标邮箱的验证码转发到微信。

## 项目简介

本项目是一个轻量级的 Docker 容器监控服务，用于：
- 实时监控 Multica 后端容器的日志输出
- 检测指定邮箱的验证码日志
- 通过 Webhook 将验证码推送到微信

## 架构设计

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Multica        │     │  Monitor         │     │  Webhook        │
│  Backend        │────▶│  Container       │────▶│  Server         │
│  (Docker)       │     │  (本项目)         │     │  (微信推送)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        日志流              正则匹配验证码          HMAC签名验证
```

### 工作流程

1. 容器启动后，通过 `docker logs --follow` 实时监控 Multica 后端日志
2. 使用正则表达式匹配特定邮箱的验证码日志
3. 提取验证码后，通过 HMAC-SHA256 签名的 Webhook 发送到微信推送服务
4. 本地记录已发送的验证码，避免重复推送

## 文件说明

| 文件 | 说明 |
|------|------|
| `main.py` | 主程序，实现日志监控和 Webhook 调用 |
| `Dockerfile` | Docker 镜像构建文件 |
| `docker-compose.yml` | Docker Compose 部署配置 |
| `requirements.txt` | Python 依赖 |

## 快速部署

### 前置条件

- Docker 和 Docker Compose
- 已运行的 Multica 后端容器
- 微信推送 Webhook 服务

### 配置

编辑 `main.py` 中的配置项：

```python
# 配置 - 根据您的环境修改这些值
CONTAINER_NAME = "multica-backend-1"           # Multica 后端容器名称
TARGET_EMAIL = "YOUR_EMAIL@example.com"        # 目标邮箱
WEBHOOK_URL = "http://YOUR_HOST:8644/webhooks/verification-monitor"  # Webhook 地址
WEBHOOK_SECRET = "your-webhook-secret-here"    # Webhook 签名密钥
```

### 部署步骤

```bash
# 1. 克隆项目
git clone https://github.com/xinxinak47cq/multica-auth-weixin.git
cd multica-auth-weixin

# 2. 修改配置
vim main.py  # 修改上述配置项

# 3. 构建并启动
docker-compose up -d

# 4. 查看日志
docker-compose logs -f
```

## Webhook 签名验证

发送的请求包含 HMAC-SHA256 签名，用于验证请求来源：

```python
# 签名计算
sig = "sha256=" + hmac.new(
    WEBHOOK_SECRET.encode(),
    payload_str.encode(),
    hashlib.sha256
).hexdigest()

# 请求头
headers = {
    "Content-Type": "application/json",
    "X-Hub-Signature-256": sig,  # 签名
    "X-GitHub-Event": "verification",
}
```

### 请求格式

```json
{
  "code": "123456",
  "email": "user@example.com",
  "message": "multica verification code: 123456"
}
```

## 日志格式

监控的日志格式：

```
[DEV] Verification code for user@example.com: 123456
```

## 注意事项

1. 容器使用 `network_mode: host` 以访问本地 Docker 服务
2. 挂载 `/run/docker.sock` 用于读取容器日志
3. 已发送的验证码记录在容器的 `/tmp/sent_codes.json` 文件中
4. 重启容器会清空已发送记录

## 许可证

MIT License
