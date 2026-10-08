"""
探针：ApiResponse 带方括号 vs 不带方括号，到底差在哪？

不改任何生产代码，只是把 schemas/users.py 里那个类拿出来照一照。

跑法：
    cd D:\\toutiao\\toutiao_backend
    .venv\\Scripts\\python.exe _probe_generics.py
"""

import json

from schemas.users import ApiResponse, UserInfoResponse

print("=" * 60)
print("① 不带方括号：data 字段是什么类型？")
print("=" * 60)
print(f"  ApiResponse.model_fields['data'].annotation  →  {ApiResponse.model_fields['data'].annotation}")

print()
print("=" * 60)
print("② 带方括号：同一个字段，变成了什么？")
print("=" * 60)
造出来的 = ApiResponse[UserInfoResponse]
print(f"  ApiResponse[UserInfoResponse].model_fields['data'].annotation")
print(f"      →  {造出来的.model_fields['data'].annotation}")

print()
print("=" * 60)
print("③ 方括号是不是『开柜子取东西』？—— 造出来的和原来的是不是同一个物种")
print("=" * 60)
print(f"  ApiResponse[UserInfoResponse] is ApiResponse            →  {造出来的 is ApiResponse}")
print(f"  ApiResponse[UserInfoResponse] is ApiResponse[list[int]] →  {造出来的 is ApiResponse[list[int]]}")
print(f"  它俩是同一个类吗     →  {造出来的 == ApiResponse[UserInfoResponse]}")
print(f"  ApiResponse[UserInfoResponse] 还是不是 BaseModel 的子类 →  "
      f"{issubclass(造出来的, ApiResponse)}")
print(f"  type(ApiResponse[UserInfoResponse])  →  {type(造出来的)}")

print()
print("=" * 60)
print("④ 实弹：同一份脏数据喂给两个版本，看谁拦得住")
print("=" * 60)
脏数据 = {"code": 200, "message": "success", "data": {"id": "不是数字", "username": 123}}

print("  喂给 ApiResponse（没方括号）：")
try:
    ApiResponse(**脏数据)
    print("      → 放行 ❌ 校验躺平了")
except Exception as e:
    print(f"      → 拦住 ✅ {type(e).__name__}")

print("  喂给 ApiResponse[UserInfoResponse]（有方括号）：")
try:
    造出来的(**脏数据)
    print("      → 放行 ❌")
except Exception as e:
    print(f"      → 拦住 ✅ {type(e).__name__}")

print()
print("=" * 60)
print("⑤ /docs 里给前端看的样子（schema）")
print("=" * 60)
print("  没方括号：")
print("     " + json.dumps(ApiResponse.model_json_schema()["properties"]["data"], ensure_ascii=False))
print("  有方括号：")
print("     " + json.dumps(造出来的.model_json_schema()["properties"]["data"], ensure_ascii=False))
