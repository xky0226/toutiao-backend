from pydantic_settings import BaseSettings, SettingsConfigDict


class AiConfig(BaseSettings):
    """AI 供应商配置。

    ⚠️ 密钥【只从环境变量 / .env 读】，源码里绝不写默认值 —— 这个项目要上 GitHub，
       源码里的任何密钥 = 公开密钥，爬虫秒扫。

    历史教训：这里原来写死了 api_key 的默认值，2026-10-12 上 GitHub 前扫出来才删掉
    （写死的那个 key 是 09-22 之前的旧 key，同日已轮换过）。

    注意 api_key【故意不给默认值】：读不到就直接启动报错，
    好过悄悄用一个空的 / 别人的 key 跑起来。
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"


ai_config = AiConfig()
