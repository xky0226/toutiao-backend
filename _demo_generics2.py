"""
拿【你自己的真实模型】看：UserInfoResponse 到底几层？

跑法：  .venv\\Scripts\\python.exe _demo_generics2.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from schemas.users import ApiResponse, UserInfoResponse, UserLoginResponse


def show(title, model):
    print(f"\n{title}")
    print(f"   {model.__name__}")
    for name, f in model.model_fields.items():
        req = "必填" if f.is_required() else f"默认={f.default!r}"
        print(f"     - {name}: {f.annotation}   ({req})")


print("=" * 66)
show("① 光看 UserInfoResponse 自己 —— 它几层？", UserInfoResponse)
print("   ↑ 六行，全是平铺字段，一个嵌套都没有  ->  【它一层都不是，是平的】")

show("② 套进 ApiResponse 之后 —— 现在是几层？", ApiResponse[UserInfoResponse])
print("   ↑ 三层：code / message / data。data 那格的类型 = UserInfoResponse")

print("\n③ ApiResponse[UserInfoResponse] 的 properties（FastAPI 画 /docs 用的就是它）：")
sch = ApiResponse[UserInfoResponse].model_json_schema()
print(json.dumps(sch["properties"], ensure_ascii=False, indent=2))
print("   ↑ 注意 data 那行：它不是一个三层结构，是一个【指向 UserInfoResponse 的 $ref】")

show("④ 对照：真正嵌套的是这个（登录接口用的）", UserLoginResponse)
print("   ↑ 这个才是「里面还套一层」：userInfo 那个字段的类型才是 UserInfoResponse")

print("\n⑤ /info 接口实际吐出来的响应，就长这样（三层，只有一层嵌套）：")
print(json.dumps({
    "code": 200,
    "message": "查询成功",
    "data": {
        "id": 1, "username": "张三", "nickname": None,
        "avatar": None, "gender": None, "bio": None,
    },
}, ensure_ascii=False, indent=2))

sys.stdout.flush()
