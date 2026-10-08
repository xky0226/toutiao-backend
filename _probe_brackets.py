"""
探针：`list[X]` 里的方括号，和 `真的一批[0]` 里的方括号，是同一件事吗？

不改任何生产代码。只干一件事：把"方括号"的两个用法摆在一起，
让电脑自己说它们一样不一样。

跑法：
    cd D:\\toutiao\\toutiao_backend
    .venv\\Scripts\\python.exe _probe_brackets.py
"""

from schemas.users import UserInfoResponse

print("=" * 64)
print("①  list[UserInfoResponse]  —— 它到底是个什么东西？")
print("=" * 64)

形状 = list[UserInfoResponse]
print(f"    打印它自己         →  {形状}")
print(f"    问它属于哪个类     →  {type(形状)}")

print()
print("    你说它是『一批值』。一批值至少得能【数】、能【取】：")
try:
    print(f"    数一数几个 len(它)  →  {len(形状)}")
except Exception as e:
    print(f"    数一数几个 len(它)  →  ❌ {type(e).__name__}: {e}")
try:
    print(f"    取第0个   它[0]     →  {形状[0]}")
except Exception as e:
    print(f"    取第0个   它[0]     →  ❌ {type(e).__name__}: {e}")

print()
print("=" * 64)
print("②  真造一批值来对照 —— 跟上面差在哪，一眼看出来")
print("=" * 64)

真的一批 = [UserInfoResponse(id=1, username="a"), UserInfoResponse(id=2, username="b")]
print(f"    打印它自己         →  {真的一批}")
print(f"    问它属于哪个类     →  {type(真的一批)}")
print(f"    数一数几个         →  {len(真的一批)}")
print(f"    取第0个            →  {真的一批[0]}")

print()
print("=" * 64)
print("③  两个方括号，里面装的东西根本不是一类")
print("=" * 64)
print(f"    list[UserInfoResponse] 方括号里装的是  →  {UserInfoResponse}")
print(f"        这是一{'个类（模具）' if isinstance(UserInfoResponse, type) else '批值'}")
print()
print(f"    真的一批[0] 取出来的是                 →  {真的一批[0]}")
print(f"        这是一{'个类（模具）' if isinstance(真的一批[0], type) else '个实例（月饼）'}")

print()
print("=" * 64)
print("④  电脑的结论（不是我说的，是它自己吐的）")
print("=" * 64)
print("    list[UserInfoResponse]  数不出长度、取不出元素   →  里面【一个值都没有】")
print("    真的一批                能数(2)、能取([0])      →  里面【有两个值】")
