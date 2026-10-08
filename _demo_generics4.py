"""
ApiResponse[UserLoginResponse] 盖出来，到底几层？

跑法：  .venv\\Scripts\\python.exe _demo_generics4.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from schemas.users import ApiResponse, UserInfoResponse, UserLoginResponse

# 真盖一个出来
r = ApiResponse[UserLoginResponse](
    code=200,
    message="success",
    data=UserLoginResponse(
        token="eyJhbGciOi...",
        userInfo=UserInfoResponse(id=1, username="张三", nickname="小张"),
    ),
)

print("=" * 66)
print("① 盖出来的实物：")
print(json.dumps(r.model_dump(), ensure_ascii=False, indent=2))

print("\n② 谁负责哪一层（数一数有几个模具）：")
print(f"   第1层  ApiResponse        -> {list(ApiResponse[UserLoginResponse].model_fields)}")
print(f"   第2层  UserLoginResponse  -> {list(UserLoginResponse.model_fields)}")
print(f"   第3层  UserInfoResponse   -> {list(UserInfoResponse.model_fields)}")

print("\n③ 数模型个数 = 数层数：")
print("   参与的有几个模型？ApiResponse / UserLoginResponse / UserInfoResponse -> 3 个 -> 3 层")

print("\n④ 对照 /info 那个接口（凹槽里按的是平的 UserInfoResponse）：")
print(f"   ApiResponse[UserInfoResponse].data -> "
      f"{ApiResponse[UserInfoResponse].model_fields['data'].annotation}")
print("   参与的有几个模型？ApiResponse / UserInfoResponse -> 2 个 -> 2 层")

print("\n⑤ 注意『键』和『层』不是一回事：")
print("   /info 的响应：顶层有 3 个【键】(code/message/data)，但只有 2 个【模型】-> 2 层")

sys.stdout.flush()
