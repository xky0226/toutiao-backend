# 🚀 Toutiao 缓存设计文档

> 从零开始，为你的新闻应用搭建 Redis 缓存层

---

## 目录

1. [缓存基础概念](#1-缓存基础概念)
2. [项目现状与瓶颈分析](#2-项目现状与瓶颈分析)
3. [Redis 简介](#3-redis-简介)
4. [缓存架构设计](#4-缓存架构设计)
5. [缓存策略表（按接口）](#5-缓存策略表按接口)
6. [缓存工作流](#6-缓存工作流)
7. [缓存 Key 命名规范](#7-缓存-key-命名规范)
8. [缓存失效策略](#8-缓存失效策略)
9. [分步实现指南](#9-分步实现指南)
10. [Redis 安装与启动](#10-redis-安装与启动)
11. [总结与下一步](#11-总结与下一步)

---

## 1. 缓存基础概念

### 1.1 什么是缓存？

**缓存（Cache）** 是一个临时存储数据的层，把"慢"的操作结果存起来，下次请求时直接返回，避免重复计算或重复查数据库。

一个生活类比：你做饭时会把常用调料放在灶台边（缓存），而不是每次用都去楼下超市买（数据库）。

### 1.2 为什么需要缓存？

看一个简单对比：

| 操作 | 耗时 | 量级 |
|---|---|---|
| CPU L1 缓存访问 | ~1 ns | 纳秒级 |
| 内存访问 | ~100 ns | 纳秒级 |
| **Redis 访问** | **~1 ms** | **毫秒级** |
| MySQL 查询（有索引） | ~10-50 ms | 毫秒级 |
| MySQL 复杂查询 | ~100-500 ms | 毫秒级 |

**结论：** Redis 比 MySQL 快 **10-50 倍**。在高并发场景下，缓存是保护数据库的第一道防线。

### 1.3 缓存金字塔

```
                    ┌──────────────────┐
                    │   CPU L1/L2/L3   │  ~1 ns
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │    进程内存缓存    │  ~100 ns
                    │  (Python dict)   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   Redis (内存)   │  ~1 ms      ← 我们在这里
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │     MySQL 磁盘   │  ~10-50 ms
                    └──────────────────┘
```

越往上越快，但空间越小、成本越高。Redis 处于"快"和"大"之间的黄金平衡点。

### 1.4 常见缓存模式（Cache Patterns）

#### Cache-Aside（旁路缓存）⭐ 最常用

这是我们项目将采用的主要模式：

```
读请求：
  1. 读缓存 → 命中 → 直接返回 ✅
  2. 未命中 → 查数据库
  3. 结果写入缓存（设 TTL）
  4. 返回结果

写请求：
  1. 更新数据库
  2. 删除缓存（不是更新缓存！）
```

> **为什么是"删除"而不是"更新"缓存？**
> 因为更新操作往往涉及复杂计算，删掉缓存让下次读请求重新回填，更简单可靠。

#### Read-Through（穿透读）

缓存层自动回填，应用层只跟缓存打交道。

#### Write-Through / Write-Behind（穿透写 / 异步写）

写操作同步或异步经过缓存层写入数据库。我们后面会用到 **Write-Behind** 来处理浏览量。

### 1.5 缓存三要素

设计缓存时，始终问自己这三个问题：

| 要素 | 含义 | 我们的关注点 |
|---|---|---|
| **命中率** | 请求中多少从缓存返回 | 命中率越高，效果越好 |
| **过期策略** | 数据多久过期 | 不同接口不同 TTL |
| **失效策略** | 数据更新时怎么处理缓存 | Cache-Aside 的"删缓存" |

---

## 2. 项目现状与瓶颈分析

### 2.1 当前请求链路

```
浏览器 → FastAPI Router → CRUD 函数 → SQLAlchemy → MySQL
                                              ↑
                                        所有请求都在这里
```

**问题：** 没有缓存层，**每个请求**都直连 MySQL。

### 2.2 逐接口分析

我们用三个维度来评估每个接口：**频率**（调用多不多）、**代价**（查询重不重）、**变化率**（数据动不动）。

| 接口 | 访问频率 | 查询代价 | 数据变化率 | 瓶颈评分 ⭐ |
|---|---|---|---|---|
| `GET /api/news/categories` | 每次进首页 | 1 次 SELECT | 几乎不变 | 🔴 极高 |
| `GET /api/news/list` | 每次滚动/切换分类 | 1 SELECT + 1 COUNT | 低（新文章） | 🔴 高 |
| `GET /api/news/detail` | 每次点文章 | 1 SELECT + 1 UPDATE + 1 SELECT | 内容不变，浏览量变 | 🔴 极高 |
| `GET /api/user/info` | 每次进个人中心 | 1 SELECT | 不常变 | 🟡 中 |
| `GET /api/favorite/check` | 每次看详情（带登录） | 1 SELECT | 用户操作时变 | 🟡 中 |
| 其他写接口 | 用户主动操作 | 各 1-2 次 | - | 🟢 低 |

### 2.3 最大的瓶颈 — 新闻详情

`GET /api/news/detail` 一个请求做了 **3 次数据库操作**：

```
开始请求
  ├── ① SELECT news WHERE id = ?        → 读新闻内容
  ├── ② UPDATE news SET views = views + 1  → 增加浏览量（带 COMMIT）
  └── ③ SELECT ... WHERE category_id = ?   → 查相关新闻
返回结果
```

如果 1000 人同时看一篇文章，MySQL 要承受 3000 次查询。加入缓存后，只需：
```
开始请求
  ├── ① 查 Redis → 命中 → 返回新闻内容 ✅
  ├── ② Redis INCR views (原子 +1，不碰 MySQL)
  └── ③ 查 Redis → 命中 → 返回相关新闻 ✅
返回结果
```

MySQL 零负担。

### 2.4 热数据识别

```
高价值缓存目标（读多写少）：
  ✅ 新闻分类  — 几乎不变
  ✅ 新闻详情  — 内容不变
  ✅ 新闻列表  — 短时间不变
  ✅ 用户信息  — 低频更新

低价值缓存目标（读少写多 或 用户专属）：
  ❌ 收藏/历史列表  — 数据属于个人，缓存收益低
  ❌ 注册/登录  — 本身低频，且有安全考虑
```

---

## 3. Redis 简介

### 3.1 Redis 是什么？

**Redis**（Remote Dictionary Server）是一个基于内存的 Key-Value 数据库。简单说就是一个"跑在服务器上的超级字典"。

### 3.2 为什么选 Redis？

| 对比项 | Redis | Python dict（本地内存） |
|---|---|---|
| 存储位置 | 独立进程/服务器 | 当前进程内 |
| 生命周期 | 持久化，重启不丢 | 进程重启就丢 |
| 多进程共享 | ✅ 多个 worker 共享 | ❌ 每个 worker 独立 |
| 分布式 | ✅ 可集群 | ❌ |
| 过期策略 | ✅ 原生支持 TTL | ❌ 自己实现 |
| 数据结构 | String/Hash/List/Set/ZSet | 只有 dict/list |

对于 FastAPI（往往是多 worker 或异步），本地 dict 无法跨进程共享，**Redis 是唯一选择**。

### 3.3 我们会用到的 Redis 数据结构

| 数据结构 | 用途 | 示例 |
|---|---|---|
| **String** | 缓存 JSON 序列化的数据 | 分类列表、新闻详情 |
| **Hash** | 存储浏览量（字段=新闻ID，值=浏览量） | 批量增减 views |
| **Set** | 集合运算（不重复） | 缓存标记、数据同步标记 |
| **Sorted Set** | 排行榜、热门文章 | 按浏览量排行的热门新闻 |

### 3.4 Redis 过期机制

- **TTL（Time To Live）**：写入时设置过期时间，到期自动删除
- **惰性删除**：当 key 被访问时才检查是否过期
- **定期删除**：Redis 每秒抽检一次，删除过期 key

我们主要依赖 **TTL**：每个缓存 key 设置合理的过期时间，到期自然失效。

---

## 4. 缓存架构设计

### 4.1 整体架构

```
                         ┌─────────────────────────────┐
                         │          浏览器               │
                         │    (Vue 3 + Pinia)           │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │        FastAPI 服务           │
                         │                              │
                         │   ┌─────────────────────┐   │
                         │   │    Cache Layer       │   │
                         │   │  (utils/cache)       │   │
                         │   │                      │   │
                         │   │  ┌────────────────┐  │   │
                         │   │  │  Redis Client   │  │   │
                         │   │  └───────┬────────┘  │   │
                         │   │          │           │   │
                         │   │  ┌────────────────┐  │   │
                         │   │  │   Decorators   │  │   │
                         │   │  └────────────────┘  │   │
                         │   └─────────────────────┘   │
                         │            │                │
                         └────────────┼────────────────┘
                                      │
                    ┌─────────────────┼────────────────┐
                    ▼                                  ▼
          ┌─────────────────┐               ┌─────────────────┐
          │     Redis       │               │     MySQL       │
          │   (内存缓存)     │◄──── 回填 ────│   (主存储)       │
          └─────────────────┘               └─────────────────┘
```

### 4.2 缓存模块结构

我们在 `utils/` 下新建 `cache/` 包：

```
utils/cache/
├── __init__.py      # 导出核心工具
├── client.py        # Redis 连接客户端
├── decorators.py    # 缓存装饰器
├── keys.py          # Key 命名常量
└── backends.py      # (可选) 缓存后端抽象
```

### 4.3 各组件职责

| 组件 | 职责 |
|---|---|
| **`client.py`** | 创建 Redis 连接池，提供 `get_redis()` 异步依赖 |
| **`decorators.py`** | 提供 `@cached()` 装饰器，一行代码给接口加缓存 |
| **`keys.py`** | 统一管理缓存 key，避免字符串散落各处 |
| **`config/redis.py`** | Redis 连接配置（host、port、password 等） |

### 4.4 核心设计原则

1. **数据访问层不改** — 缓存加在 router 层或 CRUD 层，不影响已有代码
2. **逐模块渐进** — 先从收益最高的 news 模块开始，再扩展
3. **TTL 兜底** — 所有缓存 key 都有过期时间，防止数据永久不一致
4. **写操作删缓存** — Cache-Aside 模式：更新数据后删除缓存，不直接更新缓存

---

## 5. 缓存策略表（按接口）

### 5.1 总览

| # | 接口 | 缓存模式 | 缓存 Key | TTL | 失效时机 |
|---|---|---|---|---|---|
| 1 | `GET /api/news/categories` | Cache-Aside | `toutiao:news:categories` | 3600s (1h) | 后台修改分类 |
| 2 | `GET /api/news/list` | Cache-Aside | `toutiao:news:list:{categoryId}:{page}:{size}` | 300s (5min) | 新文章发布 |
| 3 | `GET /api/news/detail` | Cache-Aside | `toutiao:news:detail:{id}` | 600s (10min) | 文章内容更新 |
| 4 | `GET /api/news/detail` → views | Write-Behind | Hash: `toutiao:news:views` | 无（写回DB后删） | 批量写回 MySQL |
| 5 | `GET /api/favorite/check` | Cache-Aside | `toutiao:fav:check:{userId}:{newsId}` | 300s (5min) | 收藏/取消收藏 |
| 6 | `GET /api/user/info` | Cache-Aside | `toutiao:user:info:{userId}` | 1800s (30min) | 用户更新资料 |
| 7 | Token 验证 | 进程内缓存 | — | Token 剩余有效期 | Token 过期/刷新 |

### 5.2 各接口详解

#### ① 新闻分类 `GET /api/news/categories`

```
Key:      toutiao:news:categories
TTL:      3600 秒（1 小时）
类型:     String（存 JSON 数组）
策略:     Cache-Aside

为什么 1 小时 TTL？
→ 分类数据几乎不变（"社会"、"体育"这种分类不会小时级变动）
→ 1 小时够长保证高命中率，后台修改分类后最多 1 小时生效
```

#### ② 新闻列表 `GET /api/news/list`

```
Key:      toutiao:news:list:{categoryId}:{page}:{size}
TTL:      300 秒（5 分钟）
类型:     String（存 JSON 对象，含 list + total + hasMore）
策略:     Cache-Aside

为什么 5 分钟 TTL？
→ 新闻列表有新增可能，TTL 太长会漏新文章
→ 5 分钟的延迟对用户来说可以接受
→ 分页参数不同 ⇒ key 不同，确保翻页正确
```

**注意：** 如果新闻列表是动态排序的（按时间/热度），TTL 不能太长。如果按发布时间倒序，只需保证 TTL 内新文章出现即可。

#### ③ 新闻详情 `GET /api/news/detail`

```
Key:      toutiao:news:detail:{newsId}
TTL:      600 秒（10 分钟）
类型:     String（存 JSON 对象，含新闻所有字段）
策略:     Cache-Aside（内容部分）+ Write-Behind（浏览量部分）

为什么内容 10 分钟？
→ 文章发布后内容不修改，理论上可以更长
→ 10 分钟是保守选择，未来可以延长到 1 小时

浏览量怎么办？
→ 浏览量不适合缓存（每次 +1 就变了）
→ 解决方案：浏览量在 Redis 里用 INCR 原子递增
   → 定时任务每 5 分钟批量写回 MySQL
   → 读浏览量也从 Redis 读，保证实时
```

#### ④ 浏览量特殊处理（重要！）

这是当前最大的性能问题 —— 每次看文章都触发 MySQL UPDATE + COMMIT。

改造方案：

```
请求来了：
  Redis INCR toutiao:news:views:{newsId}     ← 0.1ms，不碰 MySQL

定时任务（每 5 分钟）：
  Redis HGETALL toutiao:news:views           ← 取出所有增量
  → UPDATE news SET views = views + Δ ...    ← 批量更新 MySQL
  → Redis DEL toutiao:news:views             ← 清空增量

读浏览量：
  先读 Redis 里的增量值 + MySQL 里的基础值 = 实时浏览量
```

这样浏览量从 **每次写 MySQL** 变成了 **每 5 分钟批量写一次**，降幅巨大。

#### ⑤ 用户信息 `GET /api/user/info`

```
Key:      toutiao:user:info:{userId}
TTL:      1800 秒（30 分钟）
类型:     String（存 JSON 对象）
策略:     Cache-Aside
失效:     用户调用 PUT /api/user/update 时删除该 key
```

#### ⑥ 收藏检查 `GET /api/favorite/check`

```
Key:      toutiao:fav:check:{userId}:{newsId}
TTL:      300 秒（5 分钟）
类型:     String（存 "true" / "false"）
策略:     Cache-Aside
失效:     用户收藏/取消收藏时删除 key
```

#### ⑦ Token 验证（进程内缓存）

这是一个特殊的优化——`get_current_user` 在每个认证请求上都要查两次数据库：

```
每次认证请求:
  SELECT FROM user_token WHERE token = ?
  SELECT FROM user WHERE id = ?
```

优化方案：使用 Python 的 `functools.lru_cache` 或一个简单的 `dict` + TTL 做进程内缓存：

```python
# 伪代码
_token_cache = {}  # {token: (user, expire_time)}

def get_cached_user(token):
    if token in _token_cache and _token_cache[token][1] > now:
        return _token_cache[token][0]
    user = db_query(...)  # 查数据库
    _token_cache[token] = (user, token_expire_time)
    return user
```

> 为什么不用 Redis？Token 验证是每个请求都会调用的"热路径"，用进程内内存比 Redis 还快（100 ns vs 1 ms）。缺点是每个 worker 进程独立，但 token 信息本身不跨 worker 共享也能正常工作。

---

## 6. 缓存工作流

### 6.1 读缓存流程（Cache-Aside）

```
                  ┌──────────┐
                  │  请求来了  │
                  └─────┬────┘
                        ▼
              ┌─────────────────┐
         ┌────│  查 Redis (key)  │────┐
         │    └────────┬────────┘    │
         │             │             │
         ▼             ▼             │
     ┌────────┐   ┌──────────┐      │
     │  命中   │   │  未命中   │      │
     └───┬────┘   └─────┬────┘      │
         │              │           │
         ▼              ▼           │
   ┌──────────┐  ┌──────────┐      │
   │ 反序列化  │  │ 查 MySQL  │      │
   └────┬─────┘  └─────┬────┘      │
        │              │           │
        │              ▼           │
        │        ┌──────────┐      │
        │        │ 写入 Redis│──────┘
        │        │ (设 TTL) │
        │        └──────────┘
        │              │
        ▼              ▼
   ┌──────────────────────────┐
   │       返回结果            │
   └──────────────────────────┘
```

### 6.2 写缓存流程（Cache-Aside）

```
                  ┌──────────┐
                  │  写请求    │
                  │(增/删/改) │
                  └─────┬────┘
                        ▼
              ┌─────────────────┐
              │  更新 MySQL      │
              └────────┬────────┘
                        ▼
              ┌─────────────────┐
              │  删除 Redis key  │   ← 关键：删缓存，不是改缓存
              └────────┬────────┘
                        ▼
              ┌─────────────────┐
              │  返回成功        │
              └─────────────────┘
```

> 下一次读请求发现缓存未命中，会把新数据重新加载到缓存。这确保了缓存和数据库永远一致。

### 6.3 浏览量特殊流程（Write-Behind）

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  用户看文章    │    │    Redis     │    │    MySQL     │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       │  GET detail       │                   │
       │──────────────────►│                   │
       │◄──────────────────│ (命中缓存内容)     │
       │                   │                   │
       │  INCR views:101   │                   │
       │──────────────────►│                   │
       │◄──────────────────│ (返回 +1 后值)    │
       │                   │                   │
       │  返回详情(含浏览量) │                   │
       │◄──────────────────│                   │
       │                   │                   │
       │     ... 5 分钟后 ...                   │
       │                   │                   │
       │                   │  HGETALL views     │
       │                   │──────────────────►│
       │                   │◄──────────────────│ {101: 50, 102: 30}
       │                   │                   │
       │                   │  UPDATE SET views  │
       │                   │  WHERE id IN (...) │
       │                   │──────────────────►│  ← 批量更新
       │                   │                   │
       │                   │  DEL views         │
       │                   │──────────────────►│
```

### 6.4 缓存预热

应用启动时，主动把热数据加载到 Redis：

```python
@app.on_event("startup")
async def warmup_cache():
    """启动时缓存预热"""
    redis = await get_redis()
    db = next(get_db())

    # 1. 预热分类（几乎不变，预热后很少失效）
    categories = await get_categories(db)
    await redis.setex("toutiao:news:categories", 3600, json.dumps(categories))

    # 2. 预热前 N 条热门新闻详情
    hot_news = await get_hot_news(db, limit=10)
    for news in hot_news:
        key = f"toutiao:news:detail:{news.id}"
        await redis.setex(key, 600, json.dumps(news.to_dict()))
```

这样应用一启动，用户第一次访问时就能命中缓存。

---

## 7. 缓存 Key 命名规范

### 7.1 命名格式

```
toutiao:{模块}:{实体}:{标识}
```

- 统一前缀 `toutiao:` — 避免和其他应用的 Redis key 冲突
- 冒号 `:` 分隔 — Redis 官方推荐的分隔风格
- 全部小写 — 避免大小写混乱

### 7.2 完整 Key 列表

| Key | 说明 |
|---|---|
| `toutiao:news:categories` | 新闻分类列表 |
| `toutiao:news:list:{categoryId}:{page}:{size}` | 新闻列表（带分页参数） |
| `toutiao:news:detail:{newsId}` | 新闻详情 |
| `toutiao:news:views` | 浏览量增量 Hash |
| `toutiao:news:related:{newsId}` | 相关新闻列表 |
| `toutiao:user:info:{userId}` | 用户信息 |
| `toutiao:fav:check:{userId}:{newsId}` | 收藏状态检查 |

### 7.3 在代码中统一管理

不要到处写字符串拼 key，而是在 `keys.py` 中集中管理：

```python
# utils/cache/keys.py

def categories_key() -> str:
    return "toutiao:news:categories"

def news_list_key(category_id: int, page: int, size: int) -> str:
    return f"toutiao:news:list:{category_id}:{page}:{size}"

def news_detail_key(news_id: int) -> str:
    return f"toutiao:news:detail:{news_id}"

def news_views_hash_key() -> str:
    return "toutiao:news:views"

def user_info_key(user_id: int) -> str:
    return f"toutiao:user:info:{user_id}"

def fav_check_key(user_id: int, news_id: int) -> str:
    return f"toutiao:fav:check:{user_id}:{news_id}"
```

---

## 8. 缓存失效策略

### 8.1 三种失效方式

| 方式 | 原理 | 我们的用法 |
|---|---|---|
| **主动失效** | 写操作后主动删缓存 | 用户更新信息、收藏/取消收藏 |
| **被动失效** | TTL 到期自动删除 | 所有缓存 key 的主要失效方式 |
| **版本失效** | 数据整体变更时递增版本号 | 未来扩展（全量刷新） |

### 8.2 缓存三大问题及应对

#### 🛡️ 缓存穿透

**问题：** 请求的 key 在缓存和数据库中都不存在，每次都会穿透到数据库。

**例子：** 攻击者用不存在的新闻 ID（如 -1、999999）大量请求详情接口。

**解决方案：**
- **缓存空值**：查询结果为空也缓存（TTL 设短一些，如 60 秒）
- **布隆过滤器**：拦截不存在的 key（项目初期不急需）

```python
value = await redis.get(key)
if value is not None:
    return deserialize(value)  # 可能是空值标记

result = await query_db()
if result is None:
    await redis.setex(key, 60, "__NULL__")  # 缓存空值
else:
    await redis.setex(key, ttl, serialize(result))
return result
```

#### 🛡️ 缓存击穿

**问题：** 热点 key 在过期瞬间，大量请求同时涌入数据库。

**例子：** 头条新闻的详情缓存刚好过期，1000 个人同时访问。

**解决方案：**
- **互斥锁（Mutex）**：第一个请求去查 DB 并重建缓存，其他请求等待（适合我们的场景）
- **永不过期 + 后台刷新**：复杂但效果更好（未来优化方向）

```python
# 装饰器中加锁逻辑（简化版）
async def get_or_rebuild(key, ttl, fetch_func):
    value = await redis.get(key)
    if value is not None:
        return deserialize(value)

    # 尝试获取锁（防击穿）
    lock_key = f"lock:{key}"
    locked = await redis.setnx(lock_key, "1", ttl=10)
    if locked:
        try:
            value = await fetch_func()
            await redis.setex(key, ttl, serialize(value))
            return value
        finally:
            await redis.delete(lock_key)
    else:
        # 等一会儿再试（别人在重建）
        await asyncio.sleep(0.1)
        return await get_or_rebuild(key, ttl, fetch_func)
```

#### 🛡️ 缓存雪崩

**问题：** 大量 key 在同一时间过期，大量请求同时涌入数据库。

**例子：** 所有新闻分类缓存 TTL=3600，整点全部过期。

**解决方案：**
- **TTL 加随机值**：基础 TTL + 随机 0~300 秒
- **多级缓存**：本地内存 + Redis 两级（未来扩展）

```python
# 在装饰器中：ttl = base_ttl + random.randint(0, 300)
```

---

## 9. 分步实现指南

### 第一阶段：基础建设

#### Step 1 — 安装 Redis 依赖

```bash
# 在 toutiao_backend 虚拟环境中
pip install redis[hiredis]
```

- `redis` — Python 官方 Redis 客户端，支持异步
- `hiredis` — C 语言编写的 Redis 解析器，性能更好（可选）

#### Step 2 — 创建 Redis 配置

```python
# config/redis.py
from pydantic import BaseSettings

class RedisConfig(BaseSettings):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""      # 没有密码则留空
    decode_responses: bool = True  # 自动返回字符串而不是 bytes

    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"

redis_config = RedisConfig()
```

#### Step 3 — 创建 Redis 客户端

```python
# utils/cache/client.py
from redis import asyncio as aioredis
from config.redis import redis_config

_redis_pool = None

async def get_redis() -> aioredis.Redis:
    """获取 Redis 连接（全局单例连接池）"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            redis_config.url,
            encoding="utf-8",
            decode_responses=redis_config.decode_responses,
        )
    return _redis_pool

async def close_redis():
    """关闭 Redis 连接（应用关闭时调用）"""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None
```

#### Step 4 — 创建缓存装饰器

```python
# utils/cache/decorators.py
import json
import functools
from redis import asyncio as aioredis
from utils.cache.client import get_redis

def cached(ttl: int, key_builder: callable):
    """
    缓存装饰器 —— 自动查缓存 + 回填

    用法：
        @cached(ttl=3600, key_builder=lambda: "toutiao:news:categories")
        async def get_categories(db):
            return await db.execute(...)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            redis = await get_redis()
            cache_key = key_builder(*args, **kwargs)

            # 1. 尝试从缓存获取
            cached_value = await redis.get(cache_key)
            if cached_value is not None:
                return json.loads(cached_value)

            # 2. 缓存未命中，执行原函数
            result = await func(*args, **kwargs)

            # 3. 结果写入缓存
            if result is not None:
                await redis.setex(cache_key, ttl, json.dumps(result, default=str))

            return result
        return wrapper
    return decorator
```

#### Step 5 — 创建 Key 管理

```python
# utils/cache/keys.py
def categories_key() -> str:
    return "toutiao:news:categories"

def news_list_key(category_id: int, page: int, size: int) -> str:
    return f"toutiao:news:list:{category_id}:{page}:{size}"

def news_detail_key(news_id: int) -> str:
    return f"toutiao:news:detail:{news_id}"

def news_views_hash_key() -> str:
    return "toutiao:news:views"

def news_views_key(news_id: int) -> str:
    return f"toutiao:news:views:count:{news_id}"

def user_info_key(user_id: int) -> str:
    return f"toutiao:user:info:{user_id}"

def fav_check_key(user_id: int, news_id: int) -> str:
    return f"toutiao:fav:check:{user_id}:{news_id}"
```

### 第二阶段：新闻模块缓存（最大收益）

#### Step 6 — 新闻分类缓存

```python
# routers/news.py 改造
from utils.cache.decorators import cached
from utils.cache.keys import categories_key

# 原函数加个缓存装饰器
@cached(ttl=3600, key_builder=lambda: categories_key())
async def get_categories_data(db):
    """获取分类数据（加缓存）"""
    return await get_categories(db)

# router 里调用方式不变
@router.get("/categories")
async def list_categories(skip: int = 0, limit: int = 20, db=Depends(get_db)):
    data = await get_categories_data(db)
    return {"code": 200, "message": "success", "data": data}
```

#### Step 7 — 新闻列表缓存

```python
# routers/news.py 改造
@cached(ttl=300, key_builder=lambda category_id, page, page_size:
        news_list_key(category_id, page, page_size))
async def get_news_list_data(category_id, page, page_size, db):
    """获取新闻列表（带缓存）"""
    skip = (page - 1) * page_size
    news_list = await get_news_list(db, category_id, skip, page_size)
    total = await get_news_count(db, category_id)
    has_more = (skip + page_size) < total
    return build_news_list_response(news_list, total, has_more)
```

#### Step 8 — 新闻详情缓存 + 浏览量分离

这是核心改造，详细步骤：

**改造前：**
```python
@router.get("/detail")
async def news_detail(news_id: int, db=Depends(get_db)):
    news = await get_news_detail(db, news_id)
    await increase_news_views(db, news_id)
    related = await get_related_news(db, news_id, news.category_id)
    ...
```

**改造后：**
```python
@router.get("/detail")
async def news_detail(news_id: int, db=Depends(get_db)):
    # 1. 新闻内容从缓存获取
    news = await get_cached_news_detail(news_id, db)

    # 2. 浏览量在 Redis 里原子递增
    views = await increment_views_in_redis(news_id)

    # 3. 相关新闻也从缓存获取
    related = await get_cached_related_news(news_id, news.category_id, db)

    # 4. 组装返回（浏览量用 Redis 里的值覆盖）
    return {
        "code": 200,
        "message": "success",
        "data": {**news, "views": views, "related": related}
    }
```

浏览量独立的 Redis 操作：
```python
async def increment_views_in_redis(news_id: int) -> int:
    """在 Redis 中原子增加浏览量"""
    redis = await get_redis()
    key = news_views_key(news_id)
    return await redis.incr(key)  # INCR 原子操作，返回 +1 后的值
```

#### Step 9 — 浏览量批量刷回 MySQL

```python
# utils/tasks.py （或在 main.py 中用 BackgroundTasks）
import json

async def sync_views_to_db():
    """定时任务：把 Redis 里的浏览量增量写回 MySQL"""
    redis = await get_redis()
    hash_key = news_views_hash_key()

    # 获取所有增量
    views_data = await redis.hgetall(hash_key)
    if not views_data:
        return

    # 批量更新 MySQL
    async with AsyncSessionLocal() as db:
        for news_id, delta in views_data.items():
            news_id = int(news_id)
            await db.execute(
                update(News)
                .where(News.id == news_id)
                .values(views=News.views + int(delta))
            )
        await db.commit()

    # 清空 Redis 增量
    await redis.delete(hash_key)
```

> 可以把 `sync_views_to_db` 注册到 FastAPI 的 `lifespan` 事件中，配合 `asyncio.create_task` 实现定时执行。

### 第三阶段：用户模块缓存

#### Step 10 — 用户信息缓存

```python
# routers/users.py 改造

@router.get("/info")
async def get_user_info(current_user=Depends(get_current_user)):
    """获取当前用户信息（带缓存）"""
    redis = await get_redis()
    key = user_info_key(current_user.id)

    # 查缓存
    cached = await redis.get(key)
    if cached:
        return {"code": 200, "message": "success", "data": json.loads(cached)}

    # 构造用户信息
    data = {
        "id": current_user.id,
        "username": current_user.username,
        "nickname": current_user.nickname,
        "avatar": current_user.avatar,
        "gender": current_user.gender,
        "bio": current_user.bio
    }

    # 写入缓存
    await redis.setex(key, 1800, json.dumps(data))
    return {"code": 200, "message": "success", "data": data}


@router.put("/update")
async def update_user(...):
    # ... 更新逻辑 ...
    # 更新成功后删除缓存
    await redis.delete(user_info_key(current_user.id))
```

#### Step 11 — 收藏检查缓存

```python
# routers/favorite.py 改造

@router.get("/check")
async def check_favorite(news_id: int, current_user=Depends(get_current_user)):
    redis = await get_redis()
    key = fav_check_key(current_user.id, news_id)

    cached = await redis.get(key)
    if cached is not None:
        return {"code": 200, "data": {"isFavorite": cached == "true"}}

    result = await check_favorite_db(current_user.id, news_id)
    await redis.setex(key, 300, "true" if result else "false")

    return {"code": 200, "data": {"isFavorite": result}}
```

### 第四阶段：收尾

#### Step 12 — 注册 Redis 生命周期

```python
# main.py
from contextlib import asynccontextmanager
from utils.cache.client import get_redis, close_redis

@asynccontextmanager
async def lifespan(app):
    # 启动：Redis 连接池自动初始化（懒加载）
    # 可选：缓存预热
    yield
    # 关闭：清理 Redis 连接
    await close_redis()

app = FastAPI(lifespan=lifespan)
```

#### Step 13 — 测试

```bash
# 1. 确保 Redis 在运行
redis-cli ping   # 应返回 PONG

# 2. 启动项目
uvicorn main:app --reload

# 3. 测试缓存
# 第一次请求 → 查 MySQL，写入 Redis
curl http://127.0.0.1:8000/api/news/categories
# 第二次请求 → 直接走 Redis（看日志确认没有 SQL 查询）

# 4. 验证 Redis 里有数据
redis-cli keys 'toutiao:*'
```

---

## 10. Redis 安装与启动

### 方式一：Docker（推荐，最简单）

```bash
# 拉取并运行 Redis
docker run -d --name toutiao-redis -p 6379:6379 redis:7-alpine

# 验证
docker ps
redis-cli ping  # 或在 docker 内执行: docker exec toutiao-redis redis-cli ping
```

### 方式二：Windows WSL + Ubuntu

```bash
# 1. 打开 WSL (Ubuntu)
wsl

# 2. 安装 Redis
sudo apt update
sudo apt install redis-server

# 3. 启动 Redis
sudo service redis-server start

# 4. 验证
redis-cli ping  # 应输出 PONG
```

### 方式三：Windows 原生

下载 Windows 版 Redis（从 [tporadowski/redis](https://github.com/tporadowski/redis/releases) 或 Microsoft Open Tech 的移植版）：

```bash
# 下载 Redis-x64-xxx.zip，解压后运行
redis-server.exe
```

### 验证连接

```bash
# 设置一个 key
redis-cli set test hello

# 读取
redis-cli get test     # → "hello"

# 查看所有 toutiao 相关 key
redis-cli keys 'toutiao:*'

# 监控 Redis 实时操作
redis-cli monitor
```

### Python 端验证

```python
# 在项目目录下运行 Python
import asyncio
from redis import asyncio as aioredis

async def test():
    r = aioredis.Redis(host="localhost", port=6379, decode_responses=True)
    await r.set("test", "Redis 连接成功！")
    val = await r.get("test")
    print(val)  # → "Redis 连接成功！"
    await r.close()

asyncio.run(test())
```

---

## 11. 总结与下一步

### 收益预估

| 指标 | 改造前 | 改造后 |
|---|---|---|
| 分类接口延迟 | ~30ms（查 MySQL） | ~1ms（查 Redis） |
| 列表接口延迟 | ~50ms | ~1ms |
| 详情接口延迟 | ~100ms（3 次操作） | ~2ms |
| 浏览量写压力 | 每次请求写 MySQL | 每 5 分钟批量写一次 |
| MySQL 总查询量 | 基准 100% | 降低 70%+ |

### 下一步计划

完成缓存层后，后续优先级：

```
1.  🔴 缓存设计（本文档） ✅
2.  🔴 安装 Redis + 基础建设
3.  🔴 新闻模块缓存（分类/列表/详情）
4.  🟡 浏览量批量写回（定时任务）
5.  🟡 用户模块缓存（info + 收藏 check）
6.  🟢 Token 验证进程内缓存
7.  🟢 缓存监控 + Prometheus 指标
8.  🟢 多级缓存（本地内存 + Redis）
```

### 学习资源

- [Redis 官方文档](https://redis.io/docs/) — 权威参考
- [Redis 命令参考](https://redis.io/commands/) — 所有命令速查
- [redis-py 文档](https://redis-py.readthedocs.io/) — Python 客户端

---

> 💡 **记住缓存的核心思想：用空间换时间，用内存换数据库。**
> 缓存不是银弹，但在这个新闻应用场景下，它是投入产出比最高的性能优化手段。
