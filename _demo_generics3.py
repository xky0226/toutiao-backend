"""
UserInfoResponse 这个『类』自己身上，装着数据吗？

跑法：  .venv\\Scripts\\python.exe _demo_generics3.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from schemas.users import ApiResponse, UserInfoResponse

print("=" * 66)
print("① 『类』本身 —— 手里有数据吗？")
print("   UserInfoResponse =", UserInfoResponse)
print("   它身上只有一份【字段清单】，光有名字和类型，一个值都没有：")
for n, f in UserInfoResponse.model_fields.items():
    print(f"     {n}: {f.annotation}")

print("\n② 想要有值，得【造一个】出来：")
u = UserInfoResponse(id=1, username="张三")
print("   u =", u)
print("   u.username =", u.username)
print("   这时候张三才出现")

print("\n③ 它俩是不一样的东西：")
print("   UserInfoResponse is u ?", UserInfoResponse is u)
print("   UserInfoResponse 的类型 ->", type(UserInfoResponse))
print("   u 的类型               ->", type(u))
print("   ↑ 一个是模具，一个是月饼")

print("\n④ 那 ApiResponse[...] 方括号里塞的是哪一个？")
print("   ApiResponse[UserInfoResponse].data 的类型 =",
      ApiResponse[UserInfoResponse].model_fields["data"].annotation)
print("   ↑ 是【类】。因为这是对 FastAPI 立的规矩，不是某一份具体数据")
try:
    ApiResponse[u]
    print("   ApiResponse[u]（塞月饼）-> 居然没报错？")
except Exception as e:
    print(f"   ApiResponse[u]（塞月饼）-> {type(e).__name__}: {str(e).splitlines()[0]}")

sys.stdout.flush()
