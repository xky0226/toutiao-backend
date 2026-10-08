resp = {"code": 200, "message": "success", "data": {"id": 5}}

try:
    print("① 点号版 resp.code    ->", resp.code)
except AttributeError as e:
    print("① 点号版 resp.code    -> 报错:", e)

print("② 开柜子 resp['code']  ->", resp["code"])
