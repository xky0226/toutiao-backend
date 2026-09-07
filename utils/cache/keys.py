def categories_key() -> str:
    return "toutiao:news:categories"

def news_list_key(category_id: int, page: int, size: int) -> str:
    return f"toutiao:news:list:{category_id}:{page}:{size}"

def news_detail_key(news_id: int) -> str:
    return f"toutiao:news:detail:{news_id}"

def news_views_hash_key() -> str:
    return "toutiao:news:views"

def news_views_pending_key() -> str:
    return "toutiao:news:views:pending"

def news_views_key(news_id: int) -> str:
    return f"toutiao:news:views:{news_id}"

def user_info_key(user_id: int) -> str:
    return f"toutiao:user:info:{user_id}"

def fav_check_key(user_id: int, news_id: int) -> str:
    return f"toutiao:fav:check:{user_id}:{news_id}"