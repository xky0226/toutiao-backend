"""
演示：ApiResponse[T] 里的方括号，是"填格子"，不是"开柜子取东西"。

同名方括号，三种活法：
    站在【数据】身上（列表）-> 数第几个        lst[1]
    站在【数据】身上（字典）-> 报名字取        d["date"]
    站在【类】身上          -> 填参数，不取东西  ApiResponse[UserInfoResponse]

跑法：  .venv\\Scripts\\python.exe _demo_generics.py
"""

import json
import sys
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """母版：data 那一格故意空着（T 就是那个空格子的名字）"""

    code: int = 0
    message: str = "ok"
    data: Optional[T] = None


class UserInfoResponse(BaseModel):
    id: int
    username: str


class NewsItem(BaseModel):
    id: int
    title: str


print("=" * 64)
print("1) 方括号两边，到底造出了什么？")
a = ApiResponse[UserInfoResponse]
b = ApiResponse[list[NewsItem]]
print(f"   ApiResponse[UserInfoResponse] = {a}")
print(f"   ApiResponse[list[NewsItem]]   = {b}")
print(f"   是同一个东西吗？ {a is b}")
print("   ↑ 这行就是铁证：它们压根是两个不同的类，不是同一个东西的两种解释")

print()
print("2) 同一个母版刻出来的两枚印章，data 那一格不一样：")
for m in (a, b):
    print(f"   {m.__name__:32s} data -> "
          f"{json.dumps(m.model_json_schema()['properties']['data'], ensure_ascii=False)}")

print()
print("3) 所以校验的尺子天生就不同 —— 同一枚印章，塞错了形状它会拦：")
print("   ✅ 对的形状：", a(code=200, message="ok", data={"id": 1, "username": "张三"}))
try:
    bad = a(code=200, message="ok", data={"id": 1, "title": "某条新闻"})  # 这是 NewsItem 的形状
    print("   ❌ 该拦没拦：", bad)
except Exception as e:
    first = str(e).splitlines()[0]
    print(f"   ✅ 拦住了：{type(e).__name__}: {first}")

print()
print("4) 母版不带方括号，data 那格还空着，FastAPI 就不知道按什么校验：")
try:
    print("   ApiResponse（裸的）data ->",
          json.dumps(ApiResponse.model_json_schema()["properties"]["data"], ensure_ascii=False))
except Exception as e:
    print(f"   裸的母版连 schema 都画不出来：{type(e).__name__}: {str(e).splitlines()[0]}")

print()
print("5) 三种方括号并排看（这才是你卡住的地方）：")
lst = [10, 20, 30]
d = {"date": "2026-10-05"}
print(f"   lst[1]           -> {lst[1]:<12} 站在数据上：数第几个")
print(f"   d['date']        -> {d['date']:<12} 站在数据上：报名字取")
print(f"   ApiResponse[...] -> {'造出一个新类':<12} 站在类上：填格子，不取东西")
print()
print("   判据：方括号左边那个东西，是【已经装好数据的盒子】，还是【还没造东西的模具】？")
print("         盒子 -> 开柜子取    |    模具 -> 填格子")

sys.stdout.flush()
