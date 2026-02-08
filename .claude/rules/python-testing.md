# Python 测试

> 扩展自 [common/testing.md](通用测试规则)，针对本项目 Flask/Python 技术栈。

## 框架

使用 **pytest** 作为测试框架。

## 覆盖率

```bash
pytest --cov=app --cov-report=term-missing
```

## 测试组织

使用 `pytest.mark` 进行测试分类：

```python
import pytest

@pytest.mark.unit
def test_calculate_total():
    ...

@pytest.mark.integration
def test_database_connection():
    ...
```

## Flask 测试模式

```python
import pytest
from app import create_app

@pytest.fixture
def app():
    app = create_app(testing=True)
    yield app

@pytest.fixture
def client(app):
    return app.test_client()
```

## 参考

参见 skill：`python-testing` 获取详细的 pytest 模式和 fixtures。
