"""
复现 MissingGreenlet —— 不碰你的 MySQL、不碰 Redis，用内存 SQLite 跑。

形状和你 crud/favorite.py 里那个坑【一模一样】：
    先 await 拿到一个对象（await db.get(...)）
    再点它身上那个 relationship 属性（a.books）

四枪，顺序别反：
    第一枪：不加 joinedload —— 看真实的报错长什么样
    第二枪：加上 joinedload —— 看它怎么就好了
    第三枪：把属性访问【包进一个 async 函数】再 await —— 桥搭起来了吗？
    第四枪：同一个属性访问，放进 db.run_sync() 里 —— 这次为什么行

跑法（要 aiosqlite，借来用，不进项目依赖）：
    cd D:\\toutiao\\toutiao_backend
    uv run --with aiosqlite python _demo_missing_greenlet.py
"""

import asyncio

import sqlalchemy
from sqlalchemy import ForeignKey, String, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, joinedload, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Author(Base):
    __tablename__ = "author"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20))
    books: Mapped[list["Book"]] = relationship()


class Book(Base):
    __tablename__ = "book"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(20))
    author_id: Mapped[int] = mapped_column(ForeignKey("author.id"))


def 打枪(编号: int, 标题: str) -> None:
    print()
    print("=" * 68)
    print(f"第{'一二三四'[编号 - 1]}枪：{标题}")
    print("=" * 68)


async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        db.add_all([
            Author(id=1, name="鲁迅", books=[Book(id=1, title="呐喊")]),
            Author(id=2, name="老舍", books=[Book(id=2, title="骆驼祥子")]),
        ])
        await db.commit()

        # ── 第一枪 ───────────────────────────────────────────────
        打枪(1, "不加 joinedload —— 拿到作者之后，才去点它的 relationship")
        a = await db.get(Author, 1)
        print(f"  await db.get(Author, 1) 回来了，手上是：{a}")
        print(f"  点【已经拿到的】属性没事：a.name = {a.name!r}")
        print("  现在点 a.books（它身上那个 relationship，从没查过）...")
        try:
            print(f"     ✅ 成功了：{a.books}")
        except Exception as e:
            print(f"     ❌ {type(e).__name__}")
            print(f"        {e}")
        print()
        print("  ⚠️ 注意：此刻 session 还开着（还在 with 块里），照样炸。")
        print("     —— 所以病根不是『session 关早了』。")

        # ── 第二枪 ───────────────────────────────────────────────
        打枪(2, "加上 joinedload —— 同一个动作，怎么就没事了")
        stmt = select(Author).options(joinedload(Author.books)).where(Author.id == 1)
        result = await db.execute(stmt)
        # ⚠️ 坑：joinedload 打的是【集合】时，一个作者会被 JOIN 出好几行，
        #    SQLAlchemy 要你显式调 .unique() 去重，否则 scalar_one() 直接报
        #    InvalidRequestError: The unique() method must be invoked on this Result...
        a1 = result.unique().scalar_one()
        print(f"  查询时就把它扛回来了。现在点 a1.books：{a1.books}")
        print("  ✅ 成功 —— 因为【没有第 2 条 SQL 要发】，那个属性早装满了。")

        # ── 第三枪 ───────────────────────────────────────────────
        打枪(3, "把属性访问包进一个 async def 再 await —— 这样能行吗？")
        print("  换一个从没碰过的作者（id=2），免得上面几枪把数据预加载进去了。")

        async def 拿书名(作者):
            # 注意：这个函数【是 async def】，括号里也【没有 await】——
            #       它只是被外面 await 了一下。
            return [b.title for b in 作者.books]

        a2 = await db.get(Author, 2)
        print(f"  await db.get(Author, 2) → {a2}")
        print("  现在 await 拿书名(a2) ...")
        try:
            print(f"     ✅ 成功了：{await 拿书名(a2)}")
        except Exception as e:
            print(f"     ❌ {type(e).__name__}")
            print(f"        {e}")

        # ── 第四枪 ───────────────────────────────────────────────
        打枪(4, "放进 db.run_sync() 里 —— 这次为什么就行")
        print("  run_sync 的意思是：把这段【同步】代码交给 SQLAlchemy，让它自己搭桥。")

        def 拿书名_同步(session, 作者id):
            return [b.title for b in session.get(Author, 作者id).books]

        print(f"     db.run_sync(拿书名_同步, 1) → {await db.run_sync(拿书名_同步, 1)}")
        print("     ✅ 成功 —— 因为这回是 SQLAlchemy 亲手把桥搭起来了。")

    print()
    print(f"  （SQLAlchemy 版本 {sqlalchemy.__version__}）")
    await engine.dispose()


asyncio.run(main())
