# 在同一服务器部署第二个项目（Memos）到 sakms.top（Docker Compose + Nginx + HTTPS）

> 适用场景：你已经按 `docs/部署-Docker-Compose-完整指南.md` 成功部署了 `saksk.top`（Flask 项目），现在希望在**同一台服务器**再部署一个项目 **Memos**，并用域名 **`sakms.top`** 访问。  
> 核心思路：两个应用都只对本机开放端口（`127.0.0.1:*`），由 **同一个 Nginx** 用 **不同域名** 分流到不同上游端口。

---

## 0. 你将得到什么

- `saksk.top` -> 反代到 `http://127.0.0.1:8000`（你已完成）
- `sakms.top` -> 反代到 `http://127.0.0.1:5230`（本文新增）
- 两个项目共享：同一个 Nginx（80/443）、同一个 Certbot（Let’s Encrypt）

> 端口选择说明：Memos 默认端口是 `5230`；你的 Flask 项目容器内是 `8000`。两者不冲突。

---

## 0.1（重要）如果 `sakms.top` 因“未备案/未接入”被拦截，怎么先用起来？

如果你在浏览器访问 `http://sakms.top` / `https://sakms.top` 看到类似“域名暂时无法访问 / 备案需要时间”的提示（常见于**国内大陆服务器**），那么：

- **`sakms.top` 在备案完成前无法对公网提供 HTTP/HTTPS 服务**（也会导致 `certbot --nginx -d sakms.top` 失败），这是平台/监管要求，无法靠改 Nginx 绕过。

此时推荐的“能立刻使用”方案是：

### 方案 A（推荐，立刻可用 + HTTPS）：先用已可访问/已备案域名的子域名

你已经有可正常访问的站点（例如 `saksk.top`），通常它的子域名也可用。做法：

1) 新建子域名：例如 `memos.saksk.top`（或 `sakms.saksk.top`）指向同一台服务器 IP  
2) 把本文所有 `sakms.top` **临时替换为** `memos.saksk.top` 完成部署与签证书  
3) 等 `sakms.top` 备案通过后，再把 Nginx 配置与证书切换到 `sakms.top`

> 优点：最省事、最稳定、也最符合国内合规要求。

### 方案 B（临时可用但不推荐）：直接用公网 IP 访问

例如 `http://<你的公网IP>:5230`。  
缺点：需要对公网开放端口、没有域名/HTTPS、也不利于长期维护与安全；仅建议你短期自用测试。

### 方案 C（为备案完成后提前准备）：用 DNS-01 先把证书签出来（可选）

如果你希望备案一通过就立刻切换到 `https://sakms.top`，可以在备案期间先用 **DNS-01** 签发证书（不依赖 80 端口可访问）。  
这需要你能添加 DNS TXT 记录（阿里云/腾讯云/Cloudflare 等均可）。证书签出来后先放着，备案通过再启用即可。

---

## 1. 部署前检查清单（务必确认）

### 1.1 DNS 与端口

1) `sakms.top` 的 DNS **A 记录**已指向你服务器公网 IP  
2) 服务器安全组/防火墙已放行：
- `80/tcp`（签发证书 + http 跳转）
- `443/tcp`（https 访问）

### 1.2 服务器已有软件（你大概率已经有）

```bash
docker version
docker compose version
nginx -v
certbot --version
```

### 1.3 不要对公网暴露应用端口

- `8000`（saksk-ti）仅绑定 `127.0.0.1:8000`
- `5230`（memos）仅绑定 `127.0.0.1:5230`

公网访问统一走 `https://<域名>` -> Nginx -> 本机回环端口。

---

## 2. 部署 Memos（推荐：直接用官方 Docker 镜像）

> Memos 官方推荐 Docker 部署：`neosmemo/memos:stable`。  
> 你仓库里虽然有 `memos/` 源码目录，但**部署并不需要它**；除非你要自定义/二次开发（见文末“附录：从源码构建”）。

### 2.1 创建目录（数据持久化）

建议把第二个项目放到独立目录，避免和 `/opt/saksk-ti` 混在一起：

```bash
sudo mkdir -p /opt/sakms/var
sudo chown -R $USER:$USER /opt/sakms
```

> `/opt/sakms/var` 会保存 memos 的数据库与附件等数据；以后备份只要备份这个目录即可。

### 2.2 创建 compose 文件

创建文件：`/opt/sakms/compose.yml`

```yaml
services:
  memos:
    image: neosmemo/memos:stable
    container_name: sakms-memos
    restart: unless-stopped
    ports:
      - "127.0.0.1:5230:5230"
    volumes:
      - ./var:/var/opt/memos
    environment:
      - TZ=Asia/Shanghai
```

### 2.3 启动 memos 并做“本机连通”验证

```bash
cd /opt/sakms
docker compose up -d
docker compose ps
docker compose logs -n 200 --no-log-prefix memos

# 本机直连（不依赖 Nginx）
curl -I http://127.0.0.1:5230/
```

如果 `curl` 无法连接：
- 先看 `docker compose ps` 是否 healthy/running
- 再看日志 `docker compose logs -n 200 memos`
- 最后检查端口是否被占用：`sudo ss -lntp | grep 5230`

---

## 3. Nginx：为 sakms.top 配置反代（HTTP + HTTPS）

> 证书签发方式你可以二选一：  
> - **A) webroot**：更可控，且与你在 `saksk.top` 教程里用的方式一致（`certbot certonly --webroot ...`）。  
> - **B) Nginx 插件**：更省事，直接 `sudo certbot --nginx -d sakms.top`，Certbot 会自动改写 Nginx 配置并安装证书。

### 3.1（仅 webroot 方式需要）准备 webroot 目录

```bash
sudo mkdir -p /var/www/certbot
```

做一个快速自检文件（可选）：
```bash
sudo mkdir -p /var/www/certbot/.well-known/acme-challenge
echo ok | sudo tee /var/www/certbot/.well-known/acme-challenge/_ping >/dev/null
```

### 3.2 先写 HTTP 站点（两种方式二选一）

创建文件：`/etc/nginx/sites-available/sakms.top.conf`

#### A) webroot 方式（用于签证书 + 自动跳转 https）

```nginx
server {
    listen 80;
    server_name sakms.top;

    # Let’s Encrypt HTTP-01 challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # 其它路径全部跳转 https
    location / {
        return 301 https://$host$request_uri;
    }
}
```

启用并重载：
```bash
sudo ln -sf /etc/nginx/sites-available/sakms.top.conf /etc/nginx/sites-enabled/sakms.top.conf
sudo nginx -t
sudo systemctl reload nginx
```

不走 DNS 的命中验证（推荐，能快速确认 Nginx 是否选中正确 server 块）：
```bash
curl -I -H "Host: sakms.top" http://127.0.0.1/.well-known/acme-challenge/_ping
```
期望：`200` 且返回 `ok`。

#### B) Nginx 插件方式（先只配纯 HTTP 反代；不要预先写 301 跳转/ssl_certificate）

> 说明：`certbot --nginx` 会自动把 HTTPS(443) 配好，并可选自动把 HTTP(80) 重定向到 HTTPS。  
> 因此这里建议你先把 **HTTP 的反代**写好即可（后续 Certbot 会把它“复制/迁移”到 HTTPS server 块中）。

把 `sakms.top.conf` 改为下面这样（如果你已经写了 A 的内容，直接整段替换即可）：

```nginx
server {
    listen 80;
    server_name sakms.top;

    # 视你的使用场景调整（上传附件/图片时避免 413）
    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:5230;
        proxy_http_version 1.1;

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_buffering off;
        proxy_read_timeout 300;
    }
}
```

启用并重载（同上）：
```bash
sudo ln -sf /etc/nginx/sites-available/sakms.top.conf /etc/nginx/sites-enabled/sakms.top.conf
sudo nginx -t
sudo systemctl reload nginx

# 本机命中验证（不走 DNS）
curl -I -H "Host: sakms.top" http://127.0.0.1/
```

---

## 4. 申请 sakms.top 的 HTTPS 证书（Let’s Encrypt）

### 4.1 webroot 方式（手动签发；不改 Nginx 配置）

```bash
sudo certbot certonly --webroot -w /var/www/certbot -d sakms.top
```

签发成功后，你应当能看到：
- `/etc/letsencrypt/live/sakms.top/fullchain.pem`
- `/etc/letsencrypt/live/sakms.top/privkey.pem`

### 4.2 Nginx 插件方式（自动签发 + 自动写入 HTTPS 配置）

> 前提：`sudo nginx -t` 必须通过，且 Nginx 正在运行。  
> ⚠️ 如果你曾手动写过 `ssl_certificate /etc/letsencrypt/live/sakms.top/...` 但证书还没签出来，务必先删掉那段，否则 `nginx -t` 会失败，导致插件无法工作。

安装插件（示例：Ubuntu/Debian）：
```bash
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx
```

执行自动签发与配置（Certbot 会交互式询问是否把 http 自动重定向到 https，建议选“Redirect”）：
```bash
sudo certbot --nginx -d sakms.top
```

签发成功后，你应当能看到：
- `/etc/letsencrypt/live/sakms.top/fullchain.pem`
- `/etc/letsencrypt/live/sakms.top/privkey.pem`

---

## 5. 启用 HTTPS 站点并反代到 memos（5230）

> webroot 方式：需要你手动补齐 443 server 块（本节）。  
> Nginx 插件方式：Certbot 会自动写入 443 配置；你通常可以**直接跳到第 6 节验证**（如果发现 443 没有反代到 `127.0.0.1:5230`，再回到这里手动调整）。

### 5.1 webroot 方式：手动追加 443 server 块

> 注意：只有在证书已签发后再写 `ssl_certificate ...`，否则 `nginx -t` 会因为证书文件不存在而失败。

把以下内容追加到 `/etc/nginx/sites-available/sakms.top.conf`（保留第 3.2 的 80 段不动）：

```nginx
server {
    listen 443 ssl http2;
    server_name sakms.top;

    ssl_certificate     /etc/letsencrypt/live/sakms.top/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sakms.top/privkey.pem;

    # 视你的使用场景调整（上传附件/图片时避免 413）
    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:5230;
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

重载：
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 5.2 Nginx 插件方式：确认 443 是否已正确反代（可选）

检查 `sakms.top` 的最终生效配置（只读查看）：
```bash
sudo nginx -T 2>/dev/null | grep -n \"server_name sakms.top\" -n
```

你应该能在 `listen 443 ssl` 的 server 块里看到 `proxy_pass http://127.0.0.1:5230;`（或等价配置）。

---

## 6. 最终验证（按顺序，能省大量时间）

### 6.1 本机验证（不走 DNS）

```bash
# http -> https 跳转
curl -I -H "Host: sakms.top" http://127.0.0.1/

# https 反代到 memos
curl -kI -H "Host: sakms.top" https://127.0.0.1/
```

### 6.2 公网验证

```bash
curl -I https://sakms.top/
```

浏览器打开 `https://sakms.top`，首次进入按页面提示创建账号/初始化即可。

---

## 7. 常用运维命令（建议收藏）

### 7.1 查看状态/日志

```bash
cd /opt/sakms
docker compose ps
docker compose logs -f --tail=200 memos
```

### 7.2 更新 memos（拉新镜像并滚动重建）

```bash
cd /opt/sakms
docker compose pull
docker compose up -d
docker image prune -f
```

### 7.3 备份与迁移

- 备份目录：`/opt/sakms/var`
- 一般做法：定时打包/rsync 到对象存储或另一台机器

示例：
```bash
sudo tar -czf /opt/sakms/backup_sakms_var_$(date +%F).tar.gz -C /opt/sakms var
```

### 7.4 证书自动续期（通常系统已自带定时任务）

手动检查：
```bash
sudo certbot renew --dry-run
```

---

## 8. 常见问题排查

### 8.1 访问 `https://sakms.top` 看到 “Welcome to nginx!”

通常是**命中了默认站点**或存在重复 `server_name`：

```bash
sudo ls -l /etc/nginx/sites-enabled
sudo grep -RIn --include='*.conf' \"server_name\\s\\+.*sakms\\.top\" /etc/nginx
```

### 8.2 `502/504`（反代失败）

先按顺序检查：

1) memos 是否在跑：
```bash
cd /opt/sakms && docker compose ps
```
2) 本机端口是否通：
```bash
curl -I http://127.0.0.1:5230/
```
3) Nginx 是否写错端口（应为 `127.0.0.1:5230`）：
```bash
sudo nginx -T | grep -n \"sakms.top\" -n
```

### 8.3 certbot `unauthorized` / 404

说明 CA 访问 `http://sakms.top/.well-known/acme-challenge/...` 没打到这台 Nginx：

- DNS 解析是否正确（A 记录）
- 80 端口是否被面板/其它 Nginx/OpenResty 占用
- 安全组/防火墙是否放行 80

---

## 附录：如果你必须用本仓库 `memos/` 源码构建（可选）

> 仅在你需要二开/打补丁时使用。生产最省心仍是 `neosmemo/memos:stable`。

### A.1 构建前端静态资源

```bash
cd /opt/sakms/memos/web

# 若服务器未安装 pnpm，可用 corepack（Node 16+）
corepack enable
pnpm -v

pnpm install
pnpm release
```

> `pnpm release` 会把产物输出到：`memos/server/router/frontend/dist`（已在 `web/package.json` 定义）。

### A.2 构建 Docker 镜像并运行

```bash
cd /opt/sakms/memos
docker build -f scripts/Dockerfile -t sakms-memos:local .
```

然后把 `/opt/sakms/compose.yml` 的镜像改为：

```yaml
image: sakms-memos:local
```

重建：
```bash
cd /opt/sakms
docker compose up -d --build
```
