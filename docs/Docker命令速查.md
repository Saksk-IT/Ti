# Docker 命令速查手册

## 目录

- [本地开发环境（PowerShell）](#本地开发环境powershell)
- [服务器生产环境（Bash）](#服务器生产环境bash)
- [通用 Docker 命令](#通用-docker-命令)

---

## 本地开发环境（PowerShell）

### 1. 镜像构建

```powershell
# 进入项目目录
cd C:\Users\Administrator\Desktop\Project\WeChatProjects\Saksk_1_Ti

# === 完整构建（推荐：确保镜像内容最新） ===
# 1. 清理旧镜像和构建缓存
docker rmi saksk-ti:latest 2>$null; $null
docker builder prune -a -f

# 2. 构建镜像（--no-cache 确保完全重新构建）
docker build --no-cache -t saksk-ti:latest -f docker/Dockerfile .

# 3. 可选：打日期标签（便于回滚）
docker tag saksk-ti:latest saksk-ti:$(Get-Date -Format "yyyyMMdd")

# === 快速构建（利用缓存，适合小改动） ===
docker build -t saksk-ti:latest -f docker/Dockerfile .
```

### 2. 开发环境启动

```powershell
# 启动开发环境（前台运行，可看日志）
docker compose -f compose.dev.yml up

# 启动开发环境（后台运行）
docker compose -f compose.dev.yml up -d

# 强制重建容器（配置变更后使用）
docker compose -f compose.dev.yml up -d --force-recreate

# 重新构建镜像并启动
docker compose -f compose.dev.yml up -d --build
```

### 3. 开发环境管理

```powershell
# 查看容器状态
docker compose -f compose.dev.yml ps

# 查看日志（实时跟踪）
docker compose -f compose.dev.yml logs -f

# 查看特定服务日志
docker compose -f compose.dev.yml logs -f web
docker compose -f compose.dev.yml logs -f worker
docker compose -f compose.dev.yml logs -f redis

# 查看最近 100 行日志
docker compose -f compose.dev.yml logs --tail=100

# 停止服务
docker compose -f compose.dev.yml stop

# 停止并删除容器
docker compose -f compose.dev.yml down

# 停止并删除容器 + 数据卷（慎用：会删除 Redis 数据）
docker compose -f compose.dev.yml down -v
```

### 4. 容器内操作

```powershell
# 进入 web 容器 shell
docker compose -f compose.dev.yml exec web sh

# 进入 worker 容器 shell
docker compose -f compose.dev.yml exec worker sh

# 在容器内执行命令
docker compose -f compose.dev.yml exec web flask routes
docker compose -f compose.dev.yml exec web python -c "print('hello')"

# 查看容器内数据库
docker compose -f compose.dev.yml exec web ls -la /data/instance/
```

### 5. 导出镜像

```powershell
# 导出镜像为 tar 文件
docker save saksk-ti:latest -o saksk-ti-latest.tar

# 使用 PowerShell 压缩（生成 .zip）
Compress-Archive -Path saksk-ti-latest.tar -DestinationPath saksk-ti-latest.zip -Force

# 或使用 7-Zip 压缩（需安装 7-Zip）
7z a saksk-ti-latest.tar.gz saksk-ti-latest.tar

# 或在 Git Bash 中使用 gzip
gzip saksk-ti-latest.tar
```

---

## 服务器生产环境（Bash）

### 1. 部署新版本（完整流程）

```bash
cd /opt/saksk-ti

# 1. 解压镜像文件（如果是压缩的）
gunzip saksk-ti-latest.tar.gz
# 或解压 zip
unzip saksk-ti-latest.zip

# 2. 停止现有服务
# docker compose --env-file .env.production -f compose.prod.yml down

# 3. 删除旧镜像（防止缓存）
# docker rmi saksk-ti:latest 2>/dev/null || true

# 4. 加载新镜像
docker load -i saksk-ti-latest.tar

# 5. 启动服务
docker compose --env-file .env.production -f compose.prod.yml up -d --force-recreate

# 6. 验证部署
docker compose --env-file .env.production -f compose.prod.yml ps
curl -sS http://127.0.0.1:8000/api/ping

# 7. 清理 tar 文件（可选）
rm saksk-ti-latest.tar
```

### 2. 服务管理

```bash
cd /opt/saksk-ti

# 查看服务状态
docker compose --env-file .env.production -f compose.prod.yml ps

# 查看日志
docker compose --env-file .env.production -f compose.prod.yml logs -f
docker compose --env-file .env.production -f compose.prod.yml logs -f web
docker compose --env-file .env.production -f compose.prod.yml logs --tail=200

# 重启服务
docker compose --env-file .env.production -f compose.prod.yml restart

# 重启单个服务
docker compose --env-file .env.production -f compose.prod.yml restart web
docker compose --env-file .env.production -f compose.prod.yml restart worker

# 停止服务
docker compose --env-file .env.production -f compose.prod.yml stop

# 启动已停止的服务
docker compose --env-file .env.production -f compose.prod.yml start

# 停止并删除容器
docker compose --env-file .env.production -f compose.prod.yml down
```

### 3. 容器内操作

```bash
# 进入容器 shell
docker compose --env-file .env.production -f compose.prod.yml exec web sh
docker compose --env-file .env.production -f compose.prod.yml exec worker sh

# 查看数据库
docker compose --env-file .env.production -f compose.prod.yml exec web \
  sqlite3 /data/instance/submissions.db "SELECT COUNT(*) FROM users;"

# 查看 Flask 路由
docker compose --env-file .env.production -f compose.prod.yml exec web flask routes
```

### 4. 快捷别名（可选）

将以下内容添加到 `~/.bashrc` 或 `~/.zshrc`：

```bash
# Saksk Docker 快捷命令
alias saksk-ps='docker compose --env-file .env.production -f /opt/saksk-ti/compose.prod.yml ps'
alias saksk-logs='docker compose --env-file .env.production -f /opt/saksk-ti/compose.prod.yml logs -f'
alias saksk-restart='docker compose --env-file .env.production -f /opt/saksk-ti/compose.prod.yml restart'
alias saksk-down='docker compose --env-file .env.production -f /opt/saksk-ti/compose.prod.yml down'
alias saksk-up='docker compose --env-file .env.production -f /opt/saksk-ti/compose.prod.yml up -d'
```

---

## 通用 Docker 命令

### 1. 镜像管理

```bash
# 查看所有镜像
docker images

# 查看特定镜像
docker images | grep saksk

# 删除镜像
docker rmi saksk-ti:latest
docker rmi saksk-ti:20260201

# 删除悬空镜像（无标签的 <none> 镜像）
docker image prune -f

# 删除所有未使用的镜像
docker image prune -a -f
```

### 2. 容器管理

```bash
# 查看运行中的容器
docker ps

# 查看所有容器（包括已停止）
docker ps -a

# 查看容器详情
docker inspect <container_id>

# 查看容器资源使用
docker stats

# 停止容器
docker stop <container_id>

# 删除容器
docker rm <container_id>

# 强制删除运行中的容器
docker rm -f <container_id>
```

### 3. 日志与调试

```bash
# 查看容器日志
docker logs <container_id>
docker logs -f <container_id>           # 实时跟踪
docker logs --tail=100 <container_id>   # 最近 100 行
docker logs --since=1h <container_id>   # 最近 1 小时

# 进入运行中的容器
docker exec -it <container_id> sh
docker exec -it <container_id> bash

# 在容器内执行命令
docker exec <container_id> ls -la /app
```

### 4. 磁盘清理

```bash
# 查看 Docker 磁盘占用
docker system df

# 清理未使用的资源（容器、网络、悬空镜像）
docker system prune -f

# 更彻底的清理（包括未使用的镜像，慎用）
docker system prune -a -f

# 清理构建缓存
docker builder prune -a -f

# 清理未使用的数据卷（慎用：会删除数据）
docker volume prune -f
```

### 5. 网络管理

```bash
# 查看网络
docker network ls

# 查看网络详情
docker network inspect <network_name>

# 清理未使用的网络
docker network prune -f
```

### 6. 数据卷管理

```bash
# 查看数据卷
docker volume ls

# 查看数据卷详情
docker volume inspect <volume_name>

# 删除数据卷
docker volume rm <volume_name>

# 清理未使用的数据卷
docker volume prune -f
```

---

## 常见问题排查

### 容器无法启动

```bash
# 查看容器日志
docker logs <container_id>

# 查看容器退出原因
docker inspect <container_id> --format='{{.State.ExitCode}}'
docker inspect <container_id> --format='{{.State.Error}}'
```

### 端口冲突

```bash
# 查看端口占用（Linux）
netstat -tlnp | grep 8000
lsof -i :8000

# 查看端口占用（Windows PowerShell）
netstat -ano | findstr :8000
```

### 磁盘空间不足

```bash
# 查看磁盘使用
df -h

# 查看 Docker 占用
docker system df

# 清理所有未使用资源
docker system prune -a -f
docker builder prune -a -f
```

### 镜像加载失败

```bash
# 验证 tar 文件完整性
file saksk-ti-latest.tar

# 重新上传（使用 rsync 支持校验）
rsync -avP --checksum saksk-ti-latest.tar.gz user@server:/opt/saksk-ti/
```

---

## 文件上传方式

### SCP（简单直接）

```bash
scp saksk-ti-latest.tar.gz user@server:/opt/saksk-ti/
```

### Rsync（推荐：支持断点续传和校验）

```bash
rsync -avP saksk-ti-latest.tar.gz user@server:/opt/saksk-ti/

# 带校验
rsync -avP --checksum saksk-ti-latest.tar.gz user@server:/opt/saksk-ti/
```

### SFTP/FTP 工具

使用 FileZilla、WinSCP 等工具上传到 `/opt/saksk-ti/` 目录。
