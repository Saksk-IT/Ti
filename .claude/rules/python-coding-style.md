# Python 编码风格

> 扩展自 [common/coding-style.md](通用编码风格规则)，针对本项目 Flask/Python 技术栈。

## 标准

- 遵循 **PEP 8** 规范
- 所有函数签名使用**类型注解**

## 不可变性

优先使用不可变数据结构：

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class User:
    name: str
    email: str

from typing import NamedTuple

class Point(NamedTuple):
    x: float
    y: float
```

## 格式化工具

- **ruff** 用于代码格式化和 lint
- **isort** 用于 import 排序

## 参考

参见 skill：`python-patterns` 获取完整的 Python 惯用模式。
