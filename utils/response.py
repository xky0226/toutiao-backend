def ok(data=None, message="success"):
    return {"code": 200, "message": message, "data": data}

def error(data=None, message="error", code=400):
    return {"code": code, "message": message, "data": data}
