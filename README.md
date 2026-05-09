# Multica WeChat Verification Code Monitor

监控 Multica 平台的验证码日志，并将目标邮箱的验证码转发到微信。

## 项目简介

本项目是一个轻量级的 Docker 容器监控服务，用于：
- 监控 Multica 后端容器的日志输出
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

1. 容器启动后，定期轮询 Multica 后端容器的日志输出
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
| `.env.example` | 环境变量配置模板 |
| `.env` | 环境变量配置文件（不提交到 Git） |

## 快速部署

### 前置条件

- Docker 和 Docker Compose
- 已运行的 Multica 后端容器
- 微信推送 Webhook 服务

### 配置

所有配置通过 `.env` 文件管理，无需修改代码：

```bash
# 1. 克隆项目
git clone https://github.com/xinxinak47cq/multica-auth-weixin.git
cd multica-auth-weixin

# 2. 复制配置模板并编辑
cp .env.example .env
vim .env
```

`.env` 文件配置项说明：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CONTAINER_NAME` | Multica 后端容器名称 | `multica-backend-1` |
| `TARGET_EMAIL` | 目标邮箱地址 | （必填） |
| `WEBHOOK_URL` | Webhook 推送地址 | （必填） |
| `WEBHOOK_SECRET` | Webhook 签名密钥 | （必填） |
| `SENT_FILE` | 已发送验证码记录文件 | `/tmp/sent_codes.json` |
| `POLL_INTERVAL` | 日志轮询间隔（秒） | `10` |

### 部署步骤

```bash
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
3. `.env` 文件包含敏感信息，已被 `.gitignore` 排除，不会提交到 Git
4. 已发送的验证码记录在容器的 `/tmp/sent_codes.json` 文件中
5. 重启容器会清空已发送记录

## 许可证

MIT License
