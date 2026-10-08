from models.users import User

users = [
    User(username="小明"),
    User(username="小红"),
    User(username="小刚"),
]

print("第1行:", users[1])
print("第2行:", users[1].username)
