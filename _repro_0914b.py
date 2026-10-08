from schemas.users import UserLoginResponse, UserInfoResponse

resp = UserLoginResponse(
    token="abc123",
    userInfo=UserInfoResponse(id=1, username="小红")
)

# 你的原答案：方括号版
try:
    print("① 方括号版 resp[1][1]  ->", resp[1][1])
except TypeError as e:
    print("① 方括号版 resp[1][1]  -> 报错:", e)

# 正确写法：点号版
print("② 点号版   resp.userInfo.username ->", resp.userInfo.username)
