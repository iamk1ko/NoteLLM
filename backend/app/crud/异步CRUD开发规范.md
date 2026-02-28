# 异步 CRUD 规范

本项目所有请求与消费者流程统一使用 SQLAlchemy `AsyncSession`。
只允许使用异步 CRUD 方法，同步 CRUD 视为遗留写法，不再使用。

## 规则

- 方法参数必须接收 `db: AsyncSession`。
- 查询统一使用 `await db.execute(...)` / `await db.scalars(...)` / `await db.scalar(...)`。
- 提交必须使用 `await db.commit()`，刷新使用 `await db.refresh(obj)`。
- 禁止调用同步 Session API（例如 `db.query(...)`，或没有 `await` 的 `db.commit()`）。

## 命名约定

- 异步方法必须以 `_async` 结尾。
- 方法命名与现有 CRUD 保持一致（仅增加 `_async` 后缀）。

## 示例

### 创建

```python
@staticmethod
async def create_user_async(db: AsyncSession, user: User) -> User:
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
```

### 查询（单条）

```python
@staticmethod
async def get_user_by_id_async(db: AsyncSession, user_id: int) -> User | None:
    return await db.get(User, user_id)
```

### 查询（列表）

```python
stmt = select(User).where(User.status == 1)
result = await db.scalars(stmt)
items = result.all()
```

### 更新

```python
user = await db.get(User, user_id)
if not user:
    return None
user.name = "new"
await db.commit()
await db.refresh(user)
return user
```

### 删除

```python
await db.execute(delete(User).where(User.id == user_id))
await db.commit()
```

## 迁移说明

- 新增接口/服务时，只能调用异步 CRUD。
- 发现同步 CRUD 使用时，应在同一个改动里改为异步。
