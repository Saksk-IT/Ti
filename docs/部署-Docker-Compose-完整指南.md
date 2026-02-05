# Docker 部署完整指南（本项目：Flask + Gunicorn + Redis + RQ Worker）

> 本文面向“能直接照做上线”的部署流程，默认你使用 **Docker Compose** 部署本项目后端，并可选配 **Nginx + HTTPS** 供小程序生产环境访问。  
> 你可以把本文当作“从 0 到可用”的操作手册。

---

## 1. 架构与端口（先搞清楚你在跑什么）

本项目后端由 3 个服务组成：

- `web`：Flask + Gunicorn（对外提供 Web 页面与 API）
- `worker`：RQ Worker（处理异步队列任务，例如 AI 解析）
- `redis`：队列/缓存/限流共享存储

默认访问形态：

- Web 页面：`https://<域名>/...`
- API：`https://<域名>/api/...`
- 上传文件：`https://<域名>/uploads/...`
- 健康检查：`GET /api/ping`（用于验证网络与反代是否正确）

> 本项目容器内 Gunicorn 监听 `8000`（见 `docker/Dockerfile`），因此后端对外端口围绕 `8000` 做反代即可。

---

## 2. 数据持久化（非常关键）

项目运行数据建议统一落在一个目录里（例如 `/opt/saksk-ti/var`），并映射到容器内的 `/data`：

- SQLite 数据库：`/data/instance/submissions.db`
- 上传文件目录：`/data/uploads/`
- 日志目录：`/data/logs/`

你仓库里 `compose.yml` 已使用：

- `./var:/data`（把仓库同级 `var/` 当作运行数据目录）
- `redis_data:/data`（Redis 持久化卷）

生产建议：

- 服务器使用 `/opt/saksk-ti/var` 作为实际存储目录
- 将仓库放在 `/opt/saksk-ti`，让 `./var` 就等于 `/opt/saksk-ti/var`（最省心）

---

## 3. 服务器准备（通用清单）

### 3.1 目录

```bash
sudo mkdir -p /opt/saksk-ti
sudo mkdir -p /opt/saksk-ti/var/{instance,logs,uploads}
sudo chown -R $USER:$USER /opt/saksk-ti
```

### 3.2 安装 Docker 与 Compose

请按你服务器发行版的官方安装说明安装 Docker 与 Compose 插件，安装完成后确认：

```bash
docker version
docker compose version
```

> 如果你在国内/网络受限环境，建议先配置镜像加速器（见 3.2.1），否则可能在拉取 `redis:7-alpine` 等基础镜像时遇到 `registry-1.docker.io ... i/o timeout`。

#### 3.2.1（可选）配置 Docker 镜像加速器（解决 docker.io 超时）

常见报错长这样：
`failed to resolve reference "docker.io/library/redis:7-alpine" ... dial tcp ...:443: i/o timeout`

推荐优先使用云厂商提供的 Docker Hub 镜像加速器（阿里云 ECS：控制台 → 容器镜像服务 → 镜像工具 → 镜像加速器），把加速器地址写入 Docker 配置即可：

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json >/dev/null <<'JSON'
{
  "registry-mirrors": [
    "https://<你的加速器地址>"
  ]
}
JSON
sudo systemctl daemon-reload
sudo systemctl restart docker

docker info | grep -A10 "Registry Mirrors"
```

验证（能拉下来就说明 OK）：

```bash
docker pull redis:7-alpine
```

另外一种选择是使用第三方镜像仓库/加速服务（例如：毫秒镜像 1ms.run）：

- 镜像地址：`https://docker.1ms.run`
- （推荐）一键全局配置（Linux，来自 1ms.run 首页示例）：
  ```bash
  sudo bash -c "$(curl -sSL https://n3.ink/helper)"
  ```
  > 说明：这是运行第三方脚本/工具的方式，会下载并执行 `1ms-helper`，请自行评估安全性与稳定性；不放心可先 `curl -sSL https://n3.ink/helper` 查看脚本内容。
- 直接使用（临时，不改配置）：
  ```bash
  docker pull docker.1ms.run/redis:7-alpine
  ```
- （可选）登录（VIP 通道）：
  ```bash
  docker login docker.1ms.run
  ```
  > 注意：按 1ms.run 文档说明，单独 `docker login` 仅对带 `docker.1ms.run/` 前缀的拉取生效；若希望 `docker pull redis:7-alpine` 这类“不带前缀”的命令也加速，请使用其“一键全局配置/一键登录”的方式。

### 3.3 防火墙（只开 80/443）

如果你用 UFW：

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

> 不建议对公网开放 `8000`。正确做法是：`8000` 仅绑定本机回环地址 `127.0.0.1`，公网只经由 Nginx 的 `443` 访问。

---

## 4. 放置项目代码（两种方式）

### 方式 A：git（如果你允许使用）
```bash
cd /opt/saksk-ti
git clone <你的仓库地址> .
```

### 方式 B：上传压缩包/目录（不使用 git）
- 将项目文件上传并解压到 `/opt/saksk-ti`
- 建议按下面清单准备上传内容（**这是“后端 Docker 部署”维度的清单**）

#### 必须上传（后端能跑起来的最小集合）

- `compose.yml`
- `docker/Dockerfile`
- `requirements.txt`
- `run.py`
- `app/`（包含所有后端代码与 `templates/`）
- `static/`（Web 静态资源）
- `.dockerignore`（强烈建议上传：能显著减少构建上下文，避免把 `var/`、`miniprogram-1/` 等打进镜像）

#### 可选上传（不影响后端运行，但建议保留在同目录便于维护）

- `docs/`（部署/说明文档）
- `miniprogram-1/`（小程序工程：**不需要部署到服务器**，但你想统一管理也可上传备份）
- `docker/` 下除 `Dockerfile` 外如有新增脚本，也一并上传

#### 可选上传（迁移你本地已有数据：想“延续现有用户/题库/记录”才需要）

> 如果你希望服务器上线后“数据从零开始”，这一段全部可以不上传，只需在服务器创建空目录即可。

- `var/instance/submissions.db`（核心数据库）
- `var/uploads/`（所有上传的图片/头像/音视频等）
- `var/instance/question_import_template.xlsx`（导入模板，可选）
- `var/backup/`（历史备份，可选）

#### 不要上传（或不要放进镜像/仓库）

- `.env` / `.env.*`（包含密钥：生产请用服务器上的 `.env.production`）
- `.venv/`、`__pycache__/`、`.git/`（不需要）
- 根目录的 `instance/`、`logs/`、`uploads/`（你本机是 Junction 指向 `var/`；服务器直接用 `/opt/saksk-ti/var/*` 即可）

#### 推荐的打包方式（本地一次性生成上传包）

在本地项目根目录执行（示例）：
```bash
tar -czf saksk-ti.tar.gz \
  compose.yml docker/Dockerfile requirements.txt run.py .dockerignore \
  app static docs miniprogram-1
```

如果你要迁移数据，再额外把 `var/instance/submissions.db` 与 `var/uploads/` 单独打包上传（避免误把数据打进镜像构建上下文）。

---

## 5. 生产环境“正确姿势”：用覆盖文件剥离密钥 + 收紧端口

### 5.1 为什么要做这一步？

你的仓库 `compose.yml` 里包含固定值/密钥（例如 `SECRET_KEY: change-me`）。生产环境如果直接用它：

- 有**密钥泄露**风险（尤其是微信/第三方 key）
- 容易**误用默认密钥**导致会话安全问题
- 端口 `8000` 可能直接暴露公网

因此推荐：**仓库文件不动**，在服务器新增两份“不入库”的文件来覆盖它：

1) `/opt/saksk-ti/.env.production`：只放真实密钥与生产参数  
2) `/opt/saksk-ti/compose.prod.yml`：只放生产差异（端口收紧、覆盖固定值、restart 策略等）

### 5.2 创建 `/opt/saksk-ti/.env.production`

文件内容（复制后只需替换标注项）：

```bash
# /opt/saksk-ti/.env.production
FLASK_ENV=production

# 必须：用于 session/jwt/签名等（请替换为强随机）
SECRET_KEY=BOTCI44xaEomGdflIqX53OOycd8ng3x300-C-HJJADQ

# 微信小程序（必填：从微信公众平台获取）
WECHAT_APPID=wxfc4c270f007773ab
WECHAT_SECRET=714b6315c5e27cb2689c3c1d5bd54e2d

# 如启用 AI 解析（可选，不用可留空）
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_API_KEY=sk-9305b010e9be495b8407611f14394fd5

# Nginx 反代场景建议开启（获取真实 https/host/ip）
PROXY_FIX_ENABLED=true

# HTTPS 部署建议开启（让 session cookie 只在 https 下发送）
SESSION_COOKIE_SECURE=true
```

生成 `SECRET_KEY` 的命令：
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 5.3 创建 `/opt/saksk-ti/compose.prod.yml`

作用：覆盖仓库 `compose.yml` 的固定值，并把端口只绑定到本机。

```yaml
# /opt/saksk-ti/compose.prod.yml
services:
  web:
    restart: unless-stopped
    # 注意：多文件 compose 合并时，ports 列表默认是“追加”而不是“替换”。
    # 由于仓库的 compose.yml 里 web 已包含 `ports: ["8000:8000"]`，
    # 这里必须用 !override 强制覆盖，否则会同时发布两个 8000 端口并报错：
    # `failed to bind host port 127.0.0.1:8000/tcp: address already in use`
    ports: !override
      - "127.0.0.1:8000:8000"
    environment:
      # 覆盖仓库里的固定值（用 .env.production 注入）
      SECRET_KEY: ${SECRET_KEY}
      WECHAT_APPID: ${WECHAT_APPID}
      WECHAT_SECRET: ${WECHAT_SECRET}
      DASHSCOPE_BASE_URL: ${DASHSCOPE_BASE_URL}
      DASHSCOPE_API_KEY: ${DASHSCOPE_API_KEY}
      PROXY_FIX_ENABLED: ${PROXY_FIX_ENABLED}
      SESSION_COOKIE_SECURE: ${SESSION_COOKIE_SECURE}

  worker:
    restart: unless-stopped
    environment:
      SECRET_KEY: ${SECRET_KEY}
      WECHAT_APPID: ${WECHAT_APPID}
      WECHAT_SECRET: ${WECHAT_SECRET}
      DASHSCOPE_BASE_URL: ${DASHSCOPE_BASE_URL}
      DASHSCOPE_API_KEY: ${DASHSCOPE_API_KEY}
      PROXY_FIX_ENABLED: ${PROXY_FIX_ENABLED}
      SESSION_COOKIE_SECURE: ${SESSION_COOKIE_SECURE}

  redis:
    restart: unless-stopped
```

> 为什么这里要写 `${SECRET_KEY}`？  
> 因为启动时我们用 `docker compose --env-file .env.production ...`，Compose 会读取 `.env.production` 里的值，把 `${SECRET_KEY}` 替换成真实密钥，再传给容器。  
> 同时由于这个文件不进仓库，就不会把密钥写死在代码库里。

---

## 6. 启动与验证（Docker 侧）

### 6.1 构建并启动

```bash
cd /opt/saksk-ti
docker compose --env-file .env.production -f compose.yml -f compose.prod.yml up -d --build
docker compose --env-file .env.production -f compose.yml -f compose.prod.yml ps
```

### 6.2 先做“本机连通”验证（不依赖 Nginx）

```bash
curl -sS http://127.0.0.1:8000/api/ping
```

期望输出类似：
```json
{"status":"success","data":{"pong":true}}
```

### 6.3 查看日志

```bash
docker compose --env-file .env.production -f compose.yml -f compose.prod.yml logs -f web
docker compose --env-file .env.production -f compose.yml -f compose.prod.yml logs -f worker
```

---

## 7. Nginx + HTTPS（小程序生产环境必须）

微信小程序生产环境要求 HTTPS 域名且需配置“服务器域名/业务域名（web-view）”。  
因此推荐 Nginx 终止 TLS，并反代到 `127.0.0.1:8000`。

### 7.1 安装 Nginx 与证书工具（示例：Ubuntu）

```bash
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

> 注意：如果你在证书还没签发前就把 `ssl_certificate /etc/letsencrypt/live/<域名>/fullchain.pem` 写进 Nginx 配置并启用，
> `nginx -t` 会因为证书文件不存在而失败，进而导致 `certbot --nginx` 也无法运行（你会看到 `cannot load certificate ... No such file or directory`）。
> 推荐先按下面的 “7.1.1 webroot 方式” 把证书签出来，签发成功后再用 7.2 的 HTTPS 站点配置。

#### 7.1.1（推荐）webroot 方式签发证书（不依赖 Nginx 插件改配置）

1) 先准备 ACME webroot 目录：
```bash
sudo mkdir -p /var/www/certbot
```

2) 临时只启用 80 站点（用于 Let’s Encrypt 校验；证书签发成功后再切换到 7.2 配置）：
```nginx
# /etc/nginx/sites-available/saksk.top.conf
server {
    listen 80;
    server_name saksk.top;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 200 "ok";
    }
}
```

启用并启动 Nginx：
```bash
sudo ln -sf /etc/nginx/sites-available/saksk.top.conf /etc/nginx/sites-enabled/saksk.top.conf
sudo nginx -t
sudo systemctl enable --now nginx
```

3) 签发证书（以 `saksk.top` 为例）：
```bash
sudo certbot certonly --webroot -w /var/www/certbot -d saksk.top
```

如果报错 `unauthorized` / 404（CA 访问 `http://<域名>/.well-known/acme-challenge/...` 返回 404），按顺序排查：

1) 先确认 80 端口到底是谁在监听（常见是装了宝塔/面板后自带 Nginx/OpenResty，占用 80/443，导致 `systemctl nginx` 启动失败）：
```bash
sudo ss -ltnp | egrep ':80|:443'
sudo systemctl status nginx --no-pager -l
```

2) 验证 “challenge 文件是否真的能被当前站点访问到”（必须返回 `ok`）：
```bash
sudo mkdir -p /var/www/certbot/.well-known/acme-challenge
echo ok | sudo tee /var/www/certbot/.well-known/acme-challenge/_ping >/dev/null
curl -sS -H 'Host: saksk.top' http://127.0.0.1/.well-known/acme-challenge/_ping
```

3) 确认公网 DNS 解析到本机公网 IP，且安全组/防火墙放行 80：
```bash
nslookup saksk.top
```

> 如果签发失败，优先检查：域名 DNS 是否指向本机公网 IP、以及云安全组/防火墙是否放行 80/443。

#### 7.1.2（可选）使用 Nginx 插件自动配置

如果你希望 Certbot 直接改写 Nginx 配置，也可以用：
```bash
sudo certbot --nginx -d saksk.top
```

### 7.2 推荐的站点配置（示例：`saksk.top`）

文件：`/etc/nginx/sites-available/saksk.top.conf`

> 仅在证书已签发后使用（确保 `/etc/letsencrypt/live/saksk.top/fullchain.pem` 与 `privkey.pem` 已存在），否则 `nginx -t` 会失败。

```nginx
server {
    listen 80;
    server_name saksk.top;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name saksk.top;

    ssl_certificate     /etc/letsencrypt/live/saksk.top/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/saksk.top/privkey.pem;

    # 防止上传触发 413（后端允许 16MB，这里给到 20MB）
    client_max_body_size 20m;

    # uploads 建议 Nginx 直出
    location /uploads/ {
        alias /opt/saksk-ti/var/uploads/;
        add_header Cache-Control "public, max-age=604800";
        try_files $uri =404;
    }

    # static 可选直出（项目有 /static）
    location /static/ {
        alias /opt/saksk-ti/static/;
        add_header Cache-Control "public, max-age=604800";
        try_files $uri =404;
    }

    # Web 页面 + /api 全部反代到后端
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;

        proxy_buffering off;
        proxy_read_timeout 300;
    }
}
```

启用与重载：
```bash
sudo ln -sf /etc/nginx/sites-available/saksk.top.conf /etc/nginx/sites-enabled/saksk.top.conf
sudo nginx -t
sudo systemctl reload nginx
```

> 如果 `nginx -t` 报：`open() "/etc/nginx/sites-enabled/default" failed`  
> 说明你的 `/etc/nginx/nginx.conf` 在 `include /etc/nginx/sites-enabled/default;`（但该文件不存在）。  
> 处理方式二选一：  
> 1) 把该 include 改成 `include /etc/nginx/sites-enabled/*;`（推荐）  
> 2) 重新创建默认站点软链：`sudo ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default`
>  
> 如果提示：`nginx.service is not active, cannot reload.`  
> 说明 Nginx 还没启动过（或启动失败），请用：`sudo systemctl enable --now nginx` 或 `sudo systemctl restart nginx`

> 如果访问域名仍显示 `Welcome to nginx!`（默认页），或 reload 时看到：`conflicting server name "saksk.top" on 0.0.0.0:80/443, ignored`，按顺序排查：
> 1) 先看当前启用了哪些站点（通常需要禁用默认站点）：`sudo ls -l /etc/nginx/sites-enabled`  
>    - 如存在 `default` 且你不需要它：`sudo rm -f /etc/nginx/sites-enabled/default`
> 2) 确认是否有重复的 `server_name saksk.top`（来自别的配置文件，或同一配置被重复 include）：
>    - `sudo grep -RIn --include='*.conf' "server_name\\s\\+.*saksk\\.top" /etc/nginx`
>    - `sudo nginx -T 2>&1 | grep -n "/etc/nginx/sites-available/saksk.top.conf"`（如果同一路径出现多次，说明被重复加载）
> 3) 不走 DNS，直接验证命中 Host（可快速判断 Nginx 是否选中了正确的 server 块）：
>    - `curl -I -H "Host: saksk.top" http://127.0.0.1/`（期望 `301` 跳转到 https）  
>    - `curl -kI -H "Host: saksk.top" https://127.0.0.1/api/ping`（期望 `200`）
> 4) 最后再 `sudo nginx -t && sudo systemctl reload nginx`

最终验证（公网）：
```bash
curl -sS https://saksk.top/api/ping
```

---

## 8. 小程序侧配置（同域名 / 不灰度）

### 8.1 小程序生产 API 地址

文件：`miniprogram-1/miniprogram/utils/config.ts`

将：
```ts
const PROD_API_BASE_URL = 'https://your-actual-domain.com/api';
```
改为：
```ts
const PROD_API_BASE_URL = 'https://saksk.top/api';
```

> 你选择“不灰度”，因此体验版/正式版都连同一个生产域名即可。

### 8.2 微信公众平台后台域名白名单

微信公众平台 -> 小程序 -> 开发 -> 开发管理 -> 开发设置：

1) **服务器域名**
- request 合法域名：`https://saksk.top`
- uploadFile 合法域名：`https://saksk.top`
- downloadFile 合法域名：`https://saksk.top`

2) **业务域名（web-view）**
- `https://saksk.top`

---

## 9. 运维常用命令（上线后你最常用的）

### 9.1 更新代码并重建

（git 场景）
```bash
cd /opt/saksk-ti
git pull
docker compose --env-file .env.production -f compose.yml -f compose.prod.yml up -d --build
```

### 9.2 重启/停止

```bash
cd /opt/saksk-ti
docker compose --env-file .env.production -f compose.yml -f compose.prod.yml restart web worker
docker compose --env-file .env.production -f compose.yml -f compose.prod.yml down
```

### 9.3 查看资源与磁盘

```bash
docker stats
docker system df
du -sh /opt/saksk-ti/var
```

---

## 10. 备份与恢复（SQLite + uploads）

### 10.1 推荐备份内容

- `/opt/saksk-ti/var/instance/submissions.db`（核心数据）
- `/opt/saksk-ti/var/uploads/`（图片/头像/音视频等）

### 10.2 手动备份（示例）

```bash
sudo tar -czf /opt/saksk-ti/backup-$(date +%F).tar.gz -C /opt/saksk-ti var/instance var/uploads
```

> SQLite 在 WAL 模式下备份建议尽量在低峰执行；需要更严格一致性可临时停服务再打包：`docker compose ... down` -> 备份 -> `up -d`。

---

## 11. 常见故障排查（按概率排序）

### 11.1 502/504（Nginx 反代失败）

按顺序：
1) `curl http://127.0.0.1:8000/api/ping` 是否通  
2) `docker compose ... ps` 查看 `web` 是否在跑  
3) `docker compose ... logs -f web` 看 Gunicorn 是否启动失败  
4) `nginx -t` 与 `systemctl status nginx` 看反代是否生效

### 11.2 413（上传太大）

- Nginx 配 `client_max_body_size`（本文第 7.2 节已包含）
- 后端限制为 16MB（如需更大再单独调整）

### 11.3 小程序提示域名不合法 / web-view 打不开

- 检查微信后台是否已配置：
  - 服务器域名：request/upload/download
  - 业务域名：web-view
- 必须 HTTPS 且证书链完整

### 11.4 拉取镜像失败（docker.io 超时 / i/o timeout）

典型报错：
- `failed to resolve reference "docker.io/library/redis:7-alpine" ... dial tcp ...:443: i/o timeout`

排查/解决：
1) 先确认服务器能出网：`curl -I https://registry-1.docker.io/v2/`（返回 `401 Unauthorized` 也算正常）  
2) 国内/网络受限：按 3.2.1 配置镜像加速器，然后 `docker pull redis:7-alpine`  
3) 仍失败：检查 DNS/代理/iptables/运营商出网策略；必要时为 Docker 配置系统代理

### 11.5 启动失败：`127.0.0.1:8000` 端口被占用（address already in use）

典型报错：
- `failed to bind host port 127.0.0.1:8000/tcp: address already in use`

常见原因有两类：
1) **ports 合并导致重复发布**：`compose.yml` 已有 `8000:8000`，`compose.prod.yml` 又加 `127.0.0.1:8000:8000`（未使用 `!override`）  
2) **宿主机端口确实被占用**：有其他进程/容器已占用 8000

解决思路：先排除“重复发布”，再排查真正的端口占用；或直接把本机映射端口换成别的（例如 8001）。

0) 先检查是否“重复发布”（推荐）：

```bash
cd /opt/saksk-ti
docker compose --env-file .env.production -f compose.yml -f compose.prod.yml config | sed -n '/^[[:space:]]*web:/,/^[[:space:]]*worker:/p' | grep -n 'published: "8000"'
```

如果看到两条 `published: "8000"`，请按本文 5.3 把 `compose.prod.yml` 的 `ports` 改为 `ports: !override` 后再启动。

1) 先找出是谁占用了 8000：

```bash
sudo ss -ltnp | grep ':8000'
```

2) 如果是某个 Docker 容器占用：

```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}' | grep '8000->'
```

> 说明：只有出现类似 `127.0.0.1:8000->8000/tcp` 才代表占用了宿主机 8000 端口；单独的 `8000/tcp` 通常只是镜像 `EXPOSE 8000` 的展示，不占用宿主机端口。

停止对应容器后再重启本项目（示例）：

```bash
cd /opt/saksk-ti
docker compose --env-file .env.production -f compose.yml -f compose.prod.yml down
docker compose --env-file .env.production -f compose.yml -f compose.prod.yml up -d --build
```

3) 如果你不方便释放 8000：把 `compose.prod.yml` 里的端口映射改成 `127.0.0.1:8001:8000`，并把 Nginx upstream（或本机 `curl`）同步改到 `8001`。

### 11.6 访问 `saksk.top` 显示 “Welcome to nginx!” / 未命中项目

现象：浏览器打开 `https://saksk.top` 显示 Nginx 默认欢迎页，项目页面未展示。

按顺序排查：
1) 先确认后端本机通：`curl -sS http://127.0.0.1:8000/api/ping`
2) 看当前启用了哪些站点（通常需要禁用默认站点）：`sudo ls -l /etc/nginx/sites-enabled`
   - 如存在 `default` 且你不需要它：`sudo rm -f /etc/nginx/sites-enabled/default`
3) 如果 reload 时报 `conflicting server name ... ignored`，说明存在重复的 `server_name saksk.top`（来自别的配置文件，或同一配置被重复 include）：
   - `sudo grep -RIn --include='*.conf' "server_name\\s\\+.*saksk\\.top" /etc/nginx`
   - `sudo nginx -T 2>&1 | grep -n "/etc/nginx/sites-available/saksk.top.conf"`（同一路径出现多次=重复加载）
4) 不走 DNS 直接验证命中 Host（可快速定位 Nginx 是否选中了正确的 server 块）：
   - `curl -I -H "Host: saksk.top" http://127.0.0.1/`
   - `curl -kI -H "Host: saksk.top" https://127.0.0.1/api/ping`
5) 修好后：`sudo nginx -t && sudo systemctl reload nginx`

---

## 12. 安全提醒（务必做）

- 如果仓库/历史里出现过微信密钥、第三方 key：请立即去对应平台**重置/轮换**。
- 对公网只开放 `80/443`，不要让 `8000` 暴露。
- `SECRET_KEY` 必须是强随机且只存在服务器环境里。
