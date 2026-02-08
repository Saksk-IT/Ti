# Python 安全

> 扩展自 [common/security.md](通用安全规则)，针对本项目 Flask/Python 技术栈。

## 密钥管理

```python
import os
from dotenv import load_dotenv

load_dotenv()

secret_key = os.environ["SECRET_KEY"]  # 缺失时抛出 KeyError
```

## 安全扫描

- 使用 **bandit** 进行静态安全分析：
  ```bash
  bandit -r app/
  ```

## Flask 安全要点

- 所有表单启用 CSRF 保护
- 使用 `@login_required` 保护需要认证的路由
- SQL 查询必须使用参数化查询（SQLAlchemy ORM 或 `text()` 绑定参数）
- 用户输入必须在系统边界处校验
- 错误消息不得泄露敏感信息（堆栈跟踪、数据库结构等）

## 参考

参见 skill：`security-review` 获取完整的安全审查清单。
