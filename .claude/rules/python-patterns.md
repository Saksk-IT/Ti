# Python 模式

> 扩展自 [common/patterns.md](通用模式规则)，针对本项目 Flask/Python 技术栈。

## Protocol（鸭子类型）

```python
from typing import Protocol

class Repository(Protocol):
    def find_by_id(self, id: str) -> dict | None: ...
    def save(self, entity: dict) -> dict: ...
```

## Dataclasses 作为 DTO

```python
from dataclasses import dataclass

@dataclass
class CreateUserRequest:
    name: str
    email: str
    age: int | None = None
```

## 上下文管理器与生成器

- 使用上下文管理器（`with` 语句）进行资源管理
- 使用生成器进行惰性求值和内存高效迭代

## Flask 蓝图模式

```python
from flask import Blueprint

bp = Blueprint('module_name', __name__, url_prefix='/api/module')

@bp.route('/items', methods=['GET'])
def list_items():
    ...
```

## 参考

参见 skill：`python-patterns` 获取完整模式，包括装饰器、并发和包组织。
