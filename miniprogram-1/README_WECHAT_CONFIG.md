# 微信小程序配置说明

## 配置步骤

### 1. 后台系统设置配置

推荐在管理后台配置微信小程序参数：

1. 登录管理后台
2. 进入「系统设置」→「微信小程序配置」
3. 填写 AppID、AppSecret，并按需调整扫码登录小程序码版本与路径校验
4. 保存后约 15 秒内生效

后台配置会优先于环境变量，Web 扫码登录和小程序微信登录共用同一套配置。

### 2. 环境变量兜底配置

如果后台暂未配置，应用会继续读取 Docker 环境变量：

```
WECHAT_APPID=你的AppID
WECHAT_SECRET=你的AppSecret
WECHAT_MINICODE_ENV_VERSION=
WECHAT_MINICODE_CHECK_PATH=auto
```

### 3. 验证配置

后台保存后无需重启；环境变量变更后需要重启 Docker 服务才能加载。

### 4. 重启应用

如果修改的是环境变量，需要重启应用：

```bash
docker compose --env-file .env -f compose.dev.yml restart web worker
```

### 5. 测试微信登录

配置完成后，小程序的微信登录功能应该可以正常工作了。

## 安全提示

⚠️ **重要：** `.env` 文件包含敏感信息（AppSecret），请确保：

1. **不要将 `.env` 文件提交到 Git 仓库**
   - 已在 `.gitignore` 中添加 `.env`（如果存在）
   - 使用 `.env.example` 作为模板（不包含真实密钥）

2. **生产环境配置**
   - 推荐在后台系统设置中配置，环境变量作为兜底
   - 如使用环境变量，可以通过服务器环境变量或容器配置来设置

3. **定期更换 Secret**
   - 如果密钥泄露，立即在微信公众平台重置 AppSecret
   - 更新配置后重启应用

## 获取 AppID 和 AppSecret

如果需要修改配置：

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)
2. 进入「开发」→「开发管理」→「开发设置」
3. 查看「AppID(小程序ID)」和「AppSecret(小程序密钥)」
4. 如果 Secret 未设置，点击「重置」生成新的 Secret

## 故障排查

如果微信登录仍然失败，请检查：

1. **配置是否正确加载**
   - 优先检查管理后台「系统设置」→「微信小程序配置」
   - 后台为空时再检查 Docker 环境变量 `WECHAT_APPID` 和 `WECHAT_SECRET`

2. **AppID 和 Secret 是否正确**
   - 确认没有多余的空格或换行
   - 确认 Secret 是完整的（32位字符）

3. **网络连接**
   - 确保服务器能够访问 `https://api.weixin.qq.com`
   - 检查防火墙设置

4. **日志信息**
   - 查看应用日志（`logs/app.log`）
   - 查看微信 API 返回的错误信息
