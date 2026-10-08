from models.favorite import Favorite
from models.news import News

fav_list = [
    Favorite(user_id=1, news_id=10, news=News(id=10, title="今天天气真好", content="正文")),
    Favorite(user_id=1, news_id=11, news=News(id=11, title="第二条新闻", content="正文")),
]

print("第1跳 fav_list[0]            ->", fav_list[0])
print("第2跳 fav_list[0].news       ->", fav_list[0].news)
print("第3跳 fav_list[0].news.title ->", fav_list[0].news.title)
