from fastapi import FastAPI
from pydantic import BaseModel
import looker_sdk

app = FastAPI()


class AppApiSettings(looker_sdk.api_settings.ApiSettings):
    def __init__(self, *args, **kw_args):
        self.host_url = kw_args.pop("host_url")
        self.port = kw_args.pop("port")
        self.client_id = kw_args.pop("client_id")
        self.client_secret = kw_args.pop("client_secret")
        super().__init__(*args, **kw_args)

    def read_config(self) -> looker_sdk.api_settings.SettingsConfig:
        config = super().read_config()
        # See api_settings.SettingsConfig for required fields
        config["base_url"] = f"{self.host_url}:{self.port}"
        config["client_id"] = self.client_id
        config["client_secret"] = self.client_secret
        return config


class LookerConfig(BaseModel):
    host_url: str
    port: int
    client_id: str
    client_secret: str


@app.post("/")
async def root(config: LookerConfig):
    client = looker_sdk.init40(config_settings=AppApiSettings(**dict(config)))
    my_user = client.me()
    return my_user
