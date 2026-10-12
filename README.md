# 头条新闻 —— 全栈资讯平台后端

> FastAPI + SQLAlchemy 2.0（全异步）· **18 个 RESTful API** · Redis 缓存层 · SSE 流式 AI 问答

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)

## 亮点

### 1. 浏览量写放大治理：Redis INCR + Write-Behind 批量回写

**问题**：详情页每次请求都执行 `UPDATE news SET views = views + 1`。热点文章上，这是典型的**热点行写放大** —— 大量并发写锁在同一行上。

**方案**：

```
读取：Redis GET（命中直接返回）
写：  Redis INCR 原子自增      ← 不碰 MySQL，~1ms
      ↓
      计数落进 pending 登记簿（Redis Set）
      ↓
      后台定时任务（lifespan + create_task）批量捞出
      ↓
      回写 MySQL
```

**回写用 Lua 脚本实现「原子取回 + 清空」**，兼容没有 `GETDEL` 的 Redis 3.0（2.6+ 全兼容）。

> **认账点**：只有落库成功，才从登记簿里销掉。这是 **at-least-once** 的语义 —— 宁可重复回写一次（`views` 是增量累加，重复会导致多算，所以用 Lua 做原子取回避免），也不能丢一次。

### 2. 缓存一致性：一次「先 commit 再失效」的修复

**发现的隐患**：详情页缓存冻结了 `views` 字段。后台批量回写 MySQL 之后，**缓存里还是旧值** —— 用户会看到浏览量「先涨后回退」。

**修复**：回写落库后主动失效 detail 缓存，并且补了**崩溃兜底的僵尸分支**。次序是刻意安排的：

```
先 commit（数据真实落库）
    ↓
再失效缓存（此刻旧值才真正过时）
    ↓
最后销登记簿（认账殿后）
```

> 为什么不能反过来？如果先失效缓存、再 commit，中间崩溃 → 缓存被清空但 DB 没更新 → 下一次请求读回旧值并重新缓存，问题被「固化」了。

**失效粒度**：详情页 key 精准失效；列表页 / 相关推荐靠短 TTL 兜底，最终一致。

### 3. 自定义缓存装饰器

`utils/cache/` 包里自建了 `@cached(ttl, key_builder)`：

```python
@cached(ttl=300, key_builder=lambda cat, page, size: f"toutiao:news:list:{cat}:{page}:{size}")
async def get_news_list(cat, page, size): ...
```

一行接入 **Cache-Aside**（读 → 未命中查库 → 回写缓存），TTL 兜底 + 写操作主动失效。

| 接口 | 缓存 Key | TTL |
|---|---|---|
| 新闻分类 | `toutiao:news:categories` | 3600s |
| 新闻列表 | `toutiao:news:list:{cat}:{page}:{size}` | 300s |
| 新闻详情 | `toutiao:news:detail:{id}` | 600s |

### 4. SSE 流式 AI 问答（后端代理）

```
浏览器 ──→ 后端 ──→ DeepSeek API
                ←── SSE 逐字转发
```

API Key **全量存储在后端**，前端拿不到 —— 不做「前端直连 AI 接口」的快速实现。使用 `httpx.AsyncClient` + `StreamingResponse` 实现流式转发。

## 项目结构

```
toutiao_backend/
├── config/          # 配置层：db_conf.py / redis.py / ai.py
├── models/          # 6 个 SQLAlchemy ORM 模型
├── schemas/         # Pydantic v2 请求 / 响应校验
├── crud/            # 数据访问封装
├── routers/         # 18 个 API 路由
├── utils/cache/     # 缓存工具包（连接池 / Key 注册 / @cached 装饰器）
├── scheduler.py     # 浏览量批量回写后台任务
└── main.py          # 应用入口（lifespan 管理）
```

## 快速开始

```bash
pip install -e .

# 配置（源码里没有任何密钥，全部走环境变量）
cp config/.env.example .env
vim .env        # 填 API_KEY 和 DATABASE_URL

uvicorn main:app --reload --port 8000
```

## 安全设计

- **越权防护**：删除 / 修改接口强制携带 `user_id` 条件，从 SQL 层保证「只能操作自己的数据」，而不是在业务层做 if 判断。
- **密钥零明文**：`config/ai.py` 用 `pydantic-settings` 从 `.env` 读取，`api_key` **故意不设默认值** —— 读不到就直接启动报错，好过悄悄用一个空 key 跑起来。`.env` 已在 `.gitignore` 中。
- **Token 认证**：基于表存令牌 + 过期校验，通过 FastAPI `Depends` 依赖注入实现 `get_current_user` 全局复用。

## 技术栈

`Python 3.11+` · `FastAPI` · `SQLAlchemy 2.0 (async)` · `aiomysql` · `Redis` · `Pydantic v2` · `httpx` · `passlib + bcrypt`

## License

MIT
