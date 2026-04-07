# Ubuntu 24 命令行生产部署教程（Ti / saksk.top）

> 目标：在一台全新的 **Ubuntu 24.04 LTS** 服务器上，通过**纯命令行**把 Ti 部署到 **`https://saksk.top`**。  
> 仓库地址：`https://github.com/Saksk-IT/Ti.git`

## 0. 部署方案说明

本仓库自带一层容器内 Nginx（负责静态文件、上传文件和转发到 Flask / Gunicorn），但 `compose.prod.yml` 默认只开放 **80 端口**。  
为了在 Ubuntu 24 上稳定接入 **HTTPS**，本教程采用下面这套结构：

```text
公网 80/443
  -> 宿主机 Nginx + Certbot（证书与 HTTPS）
  -> 127.0.0.1:8080
  -> Docker Compose 内 nginx
  -> web / worker / postgres / redis / backup
```

这样做的好处：

- HTTPS 终止放在宿主机，证书续期简单；
- Compose 内现有生产结构基本不用改；
- PostgreSQL / Redis 不暴露公网；
- 小程序生产地址 `https://saksk.top/api` 可直接复用。

> 如果你不做 HTTPS，小程序生产环境通常无法正常接入，因此**不建议跳过证书步骤**。

---

## 1. 前置条件

请先确认：

1. 你有一台公网 Ubuntu 24.04 LTS 服务器；
2. 你有 sudo 权限；
3. 域名 `saksk.top` 的 **A 记录**已经指向这台服务器公网 IP；
4. 服务器 80 / 443 端口未被其它程序占用；
5. 你已经准备好域名、服务器和 sudo 权限。

建议先在本地或服务器上确认 DNS 已生效：

```bash
sudo apt update
sudo apt install -y dnsutils

dig +short saksk.top
```

如果这里还查不到你的服务器 IP，先不要继续申请证书。

---

## 2. 安装系统依赖

```bash
sudo apt update
sudo apt install -y \
  ca-certificates \
  curl \
  gnupg \
  openssl \
  git \
  nginx \
  snapd \
  ufw \
  dnsutils

sudo systemctl enable --now nginx
sudo systemctl enable --now snapd
```

可选：如果你希望服务器时间和备份日志使用中国时区：

```bash
sudo timedatectl set-timezone Asia/Shanghai
```

---

## 3. 安装 Docker Engine 和 Compose 插件

以下命令按 Docker 官方 Ubuntu 安装方式整理。

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin

sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
```

---

## 4. 克隆仓库并进入部署目录

下面统一把项目放到 `/opt/ti`：

```bash
export APP_DIR=/opt/ti
export REPO_URL=https://github.com/Saksk-IT/Ti.git

sudo mkdir -p "$APP_DIR"
sudo chown "$USER":"$USER" "$APP_DIR"

git clone "$REPO_URL" "$APP_DIR"
cd "$APP_DIR"
```

---

## 5. 一键部署（推荐）

如果你希望直接完成 Ubuntu 24 生产部署，优先使用仓库自带脚本：

```bash
cd /opt/ti

DOMAIN=saksk.top \
CERTBOT_EMAIL=你的邮箱 \
./scripts/deploy_ubuntu24.sh
```

脚本会自动完成：

- 安装系统依赖、Docker、Nginx、Certbot；
- 生成最小化 `.env.production`；
- 构建镜像并启动生产容器；
- 执行数据库迁移；
- 配置宿主机 Nginx；
- 申请并接入 HTTPS 证书；
- 做基础健康检查。

脚本默认会在 Docker 构建阶段使用阿里云 PyPI 镜像，并增加 pip 超时与重试。  
如果你需要临时改成别的 PyPI 源，也可以覆盖：

```bash
cd /opt/ti

DOMAIN=saksk.top \
CERTBOT_EMAIL=你的邮箱 \
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
./scripts/deploy_ubuntu24.sh
```

如果只是临时内网部署、不申请 HTTPS，可以这样跳过证书：

```bash
cd /opt/ti

DOMAIN=saksk.top \
SKIP_CERTBOT=1 \
./scripts/deploy_ubuntu24.sh
```

> 脚本生成的是**最小化 env**。  
> **邮件 / AI / 短信** 不再要求你提前写进 `.env.production`，部署完成后去后台管理系统配置即可。

部署完成后，请立刻登录后台补齐运行时配置：

- `/admin/settings/mail`
- `/admin/settings/sms`
- `/admin/settings/ai`

如果你想手动执行每一步，请继续看下面的“手动部署流程”。

---

## 6. 手动部署流程：生成生产环境变量文件

### 6.1 先准备本次部署要用到的变量

把下面几行复制到同一个 shell 会话里执行：

```bash
export APP_DOMAIN=saksk.top
export APP_EMAIL=admin@saksk.top
export POSTGRES_DB=ti_db
export POSTGRES_USER=studyuser
export POSTGRES_PASSWORD="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)"
export SECRET_KEY="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)"
```

> `APP_EMAIL` 请改成你自己的真实邮箱，Let’s Encrypt 续期提醒会发到这里。
> 后续如果你换了一个新的 shell 会话，又想继续直接复用文档里的变量写法，请先重新执行：`export APP_DOMAIN=saksk.top`。

### 6.2 创建 `.env.production`

现在推荐只保留**核心启动配置**。  
邮件 / AI / 短信 改为部署完成后在后台管理系统里配置。

```bash
cat > .env.production <<EOF
FLASK_ENV=production
SECRET_KEY=${SECRET_KEY}

POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=${POSTGRES_DB}

PROXY_FIX_ENABLED=true
SESSION_COOKIE_SECURE=true
FORCE_HTTPS=false

WECHAT_APPID=
WECHAT_SECRET=

SENTRY_DSN=
DB_POOL_SIZE=3
DB_MAX_OVERFLOW=5
DB_POOL_RECYCLE=300

BACKUP_TZ=Asia/Shanghai
BACKUP_ANCHOR_TIME=04:00
BACKUP_INTERVAL=43200
BACKUP_CHECK_INTERVAL=60
BACKUP_RETENTION_DAYS=7
EOF
```

建议立刻检查一次：

```bash
sed -n '1,220p' .env.production
```

---

## 7. 创建持久化目录

### 7.1 创建数据目录

```bash
mkdir -p \
  var/postgres \
  var/redis \
  var/uploads \
  var/instance \
  var/logs \
  backups
```

当前主分支的 `compose.prod.yml` 已经内置：

```text
127.0.0.1:8080 -> 容器 nginx:80
```

所以不再需要额外的覆盖文件来改端口。

## 8. 构建镜像、启动应用、执行迁移

### 8.1 构建镜像

```bash
sudo docker build -t saksk-ti:latest -f docker/Dockerfile .
```

### 8.2 启动生产栈

```bash
sudo docker compose \
  --env-file .env.production \
  -f compose.prod.yml \
  up -d
```

### 8.3 执行数据库迁移

```bash
sudo docker compose \
  --env-file .env.production \
  -f compose.prod.yml \
  exec web flask db upgrade
```

### 8.4 查看服务状态

```bash
sudo docker compose \
  --env-file .env.production \
  -f compose.prod.yml \
  ps
```

### 8.5 先做本机侧验证

此时站点还没暴露到公网 HTTPS，但容器栈应该已经能在本机 `127.0.0.1:8080` 正常工作：

```bash
curl -fsS http://127.0.0.1:8080/api/ping | python3 -m json.tool
curl -fsS "http://127.0.0.1:8080/api/ping?deep=1" | python3 -m json.tool
```

预期至少能看到类似：

```json
{
  "code": 0,
  "status": "success"
}
```

如果这一步就失败，先不要继续申请证书，先查日志：

```bash
sudo docker compose \
  --env-file .env.production \
  -f compose.prod.yml \
  logs --tail=200 web
```

---

## 9. 配置宿主机 Nginx，把 `saksk.top` 反向代理到 `127.0.0.1:8080`

创建站点配置：

```bash
sudo tee /etc/nginx/sites-available/ti.conf > /dev/null <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${APP_DOMAIN};

    client_max_body_size 10m;

    location /sse/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        chunked_transfer_encoding off;
    }

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Request-ID \$request_id;
        proxy_connect_timeout 10s;
        proxy_read_timeout 65s;
        proxy_send_timeout 65s;
    }
}
EOF
```

启用配置并重载 Nginx：

```bash
sudo ln -sf /etc/nginx/sites-available/ti.conf /etc/nginx/sites-enabled/ti.conf
sudo nginx -t
sudo systemctl reload nginx
```

此时可以先做一次 **HTTP** 验证：

```bash
curl -I http://${APP_DOMAIN}
curl -fsS http://${APP_DOMAIN}/api/ping | python3 -m json.tool
```

---

## 10. 放通防火墙并签发 HTTPS 证书

### 10.1 UFW 放通 SSH / HTTP / HTTPS

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
sudo ufw status
```

### 10.2 安装 Certbot

```bash
sudo snap install core
sudo snap refresh core
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/bin/certbot
```

### 10.3 申请证书并自动改写 Nginx 为 HTTPS

```bash
sudo certbot --nginx \
  -d ${APP_DOMAIN} \
  --redirect \
  -m ${APP_EMAIL} \
  --agree-tos \
  --no-eff-email
```

如果证书申请成功，再验证一次：

```bash
curl -I https://${APP_DOMAIN}
curl -fsS https://${APP_DOMAIN}/api/ping | python3 -m json.tool
```

再检查自动续期：

```bash
sudo systemctl status snap.certbot.renew.service --no-pager
sudo certbot renew --dry-run
```

---

## 11. 部署完成后的标准验证

建议至少执行下面这些检查：

```bash
# 1) Compose 服务状态
sudo docker compose \
  --env-file .env.production \
  -f compose.prod.yml \
  ps

# 2) 健康检查
curl -fsS https://saksk.top/api/ping | python3 -m json.tool
curl -fsS "https://saksk.top/api/ping?deep=1" | python3 -m json.tool

# 3) 首页可达性
curl -I https://saksk.top

# 4) 宿主机监听端口
sudo ss -tlnp | grep -E ':80|:443|:8080'
```

如果你还要给微信小程序联调，生产 API 地址就是：

```text
https://saksk.top/api
```

如果你需要邮件 / AI / 短信功能，请在验证通过后登录后台继续配置：

```text
/admin/settings/mail
/admin/settings/sms
/admin/settings/ai
```

---

## 12. 日常运维命令

### 12.1 查看服务状态

```bash
cd /opt/ti
sudo docker compose \
  --env-file .env.production \
  -f compose.prod.yml \
  ps
```

### 12.2 查看日志

```bash
cd /opt/ti
sudo docker compose \
  --env-file .env.production \
  -f compose.prod.yml \
  logs -f web

sudo docker compose \
  --env-file .env.production \
  -f compose.prod.yml \
  logs -f nginx

sudo docker compose \
  --env-file .env.production \
  -f compose.prod.yml \
  logs -f backup
```

### 12.3 重启服务

```bash
cd /opt/ti
sudo docker compose \
  --env-file .env.production \
  -f compose.prod.yml \
  restart
```

### 12.4 执行手动备份

```bash
cd /opt/ti
./scripts/backup.sh
ls -lh backups/
```

### 12.5 从备份恢复（危险操作）

```bash
cd /opt/ti
./scripts/restore.sh backup_20260407_040024.tar.gz
```

> 恢复会覆盖当前数据，执行前务必确认备份文件正确。

---

## 13. 后续更新部署

以后更新代码，按下面流程执行即可：

```bash
cd /opt/ti

git pull --ff-only origin "$(git rev-parse --abbrev-ref HEAD)"

sudo docker build -t saksk-ti:latest -f docker/Dockerfile .

sudo docker compose \
  --env-file .env.production \
  -f compose.prod.yml \
  up -d --force-recreate

sudo docker compose \
  --env-file .env.production \
  -f compose.prod.yml \
  exec web flask db upgrade

curl -fsS https://saksk.top/api/ping | python3 -m json.tool
```

可选清理旧镜像：

```bash
sudo docker image prune -f
```

如果脚本部署过一次，后续你也可以继续直接复用：

```bash
cd /opt/ti

DOMAIN=saksk.top \
CERTBOT_EMAIL=你的邮箱 \
./scripts/deploy_ubuntu24.sh
```

---

## 14. 常见故障排查

### 14.1 域名访问不到服务器

```bash
dig +short saksk.top
curl -I http://saksk.top
sudo ufw status
```

排查重点：

- A 记录是否已经指向正确公网 IP；
- 80 / 443 端口是否已放通；
- 云厂商安全组是否已放通 80 / 443。

### 14.2 Certbot 申请证书失败

常见原因：

- DNS 还没生效；
- `saksk.top` 并没有真正访问到这台机器；
- 80 端口被其他程序占用；
- Nginx 配置语法错误。

先执行：

```bash
sudo nginx -t
sudo systemctl status nginx --no-pager
sudo ss -tlnp | grep ':80'
```

### 14.3 应用容器启动失败

```bash
cd /opt/ti
sudo docker compose \
  --env-file .env.production \
  -f compose.prod.yml \
  logs --tail=200 web
```

优先检查：

- `.env.production` 中 `SECRET_KEY` 是否为空；
- PostgreSQL 密码是否写坏；
- 镜像是否成功构建；
- 数据库迁移是否执行。

### 14.4 数据库不健康

```bash
cd /opt/ti
source .env.production
sudo docker compose \
  --env-file .env.production \
  -f compose.prod.yml \
  exec postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

### 14.5 HTTPS 正常但页面加载异常

优先看两处日志：

```bash
sudo journalctl -u nginx -n 100 --no-pager

cd /opt/ti
sudo docker compose \
  --env-file .env.production \
  -f compose.prod.yml \
  logs --tail=200 nginx web
```

### 14.6 为什么 `.env.production` 里没有邮件 / AI / 短信？

这是当前推荐方式：  
这些运行时配置现在**优先从后台系统设置读取**，这样部署时无需把敏感服务配置硬写进 env。

部署完成后到后台填写：

- `/admin/settings/mail`
- `/admin/settings/sms`
- `/admin/settings/ai`

---

## 15. 重要持久化目录

生产数据主要在下面这些目录：

```text
/opt/ti/var/postgres    PostgreSQL 数据
/opt/ti/var/redis       Redis 持久化数据
/opt/ti/var/uploads     上传文件
/opt/ti/var/instance    Flask 运行数据
/opt/ti/var/logs        应用日志
/opt/ti/backups         自动/手动备份文件
```

建议你至少把这些内容纳入异地备份：

- `backups/`
- `.env.production`
- `compose.prod.yml`

---

## 16. 最短路径（推荐执行顺序）

如果你只想要当前版本的推荐部署方式，按下面顺序即可：

```bash
export APP_DIR=/opt/ti
sudo mkdir -p "$APP_DIR" && sudo chown "$USER":"$USER" "$APP_DIR"
git clone https://github.com/Saksk-IT/Ti.git "$APP_DIR"
cd "$APP_DIR"

DOMAIN=saksk.top \
CERTBOT_EMAIL=你的邮箱 \
./scripts/deploy_ubuntu24.sh
```

部署成功后，登录后台补齐这三类运行时配置：

```text
/admin/settings/mail
/admin/settings/sms
/admin/settings/ai
```
