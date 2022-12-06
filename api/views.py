from fastapi import FastAPI
from pydantic import BaseModel
import looker_sdk
import asyncio
import json
import backoff

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
    results = await asyncio.gather(
        get_longest_running_queries(client),
        get_inactive_user_percentage(client),
        get_explore_and_field_count(client),
        get_unused_explores(client),
    )
    return results


@backoff.on_exception(backoff.expo, looker_sdk.error.SDKError, max_tries=3)
async def get_longest_running_queries(client: looker_sdk.sdk.api40.methods.Looker40SDK):
    """Get the longest running queries in Looker"""
    query_body = {
        "model": "system__activity",
        "view": "history",
        "fields": [
            "query.view",
            "query.model",
            "history.average_runtime",
            "history.max_runtime",
        ],
        "filters": {"history.created_date": "last 90 days"},
        "limit": "10",
    }
    try:
        results_raw = client.run_inline_query(result_format="json", body=query_body)
    except looker_sdk.error.SDKError as e:
        # TODO: Replace with our own error handling
        raise e
    else:
        results = json.loads(results_raw)

    return results


@backoff.on_exception(backoff.expo, looker_sdk.error.SDKError, max_tries=3)
async def get_inactive_user_percentage(
    client: looker_sdk.sdk.api40.methods.Looker40SDK,
):
    """Get the percentage of inactive users in Looker"""
    query_body = {
        "model": "system__activity",
        "view": "history",
        "fields": ["history.user_id"],
        "filters": {"history.created_date": "last 30 days"},
        "limit": "50000",
    }
    try:
        results_raw = client.run_inline_query(result_format="json", body=query_body)
    except looker_sdk.error.SDKError as e:
        # TODO: Replace with our own error handling
        raise e
    else:
        active_users = json.loads(results_raw)

    active_users_list = [user["history.user_id"] for user in active_users]

    offset = 0
    keep_going = True
    all_users = []

    while keep_going:

        users = client.all_users(
            fields="id,is_disabled,verified_looker_employee",
            limit=100,
            offset=offset,
        )

        if len(users) == 0:
            keep_going = False
        else:
            all_users.extend(users)
            offset += 100

    all_users = [
        user
        for user in all_users
        if not user.is_disabled and not user.verified_looker_employee
    ]

    all_users_count = len(all_users)

    active_users_count = len(
        [user for user in all_users if int(user.id) in active_users_list]
    )

    inactive_user_percentage = (all_users_count - active_users_count) / all_users_count

    return inactive_user_percentage


@backoff.on_exception(backoff.expo, looker_sdk.error.SDKError, max_tries=3)
async def get_explore_and_field_count(client: looker_sdk.sdk.api40.methods.Looker40SDK):
    """Get the number of explores and fields in Looker"""
    offset = 0
    keep_going = True
    explores = []

    while keep_going:
        models_page = client.all_lookml_models(
            fields="name,explores", limit=100, offset=offset
        )
        for model in models_page:
            for explore in model.explores:
                explores.append({"model": model.name, "explore": explore.name})

        if len(models_page) < 100:
            keep_going = False
        else:
            offset += 100

    async def get_explore_fields(client, model, explore):
        print(f"Getting fields for {model}.{explore}")
        explore_fields = client.lookml_model_explore(
            lookml_model_name=model, explore_name=explore, fields="fields"
        )
        return {
            "model": model,
            "explore": explore,
            "field_count": len(explore_fields.fields.dimensions)
            + len(explore_fields.fields.measures)
            + len(explore_fields.fields.parameters),
        }

    tasks = tuple(
        get_explore_fields(client, explore["model"], explore["explore"])
        for explore in explores
    )

    explore_fields = await asyncio.gather(*tasks)

    return explore_fields


@backoff.on_exception(backoff.expo, looker_sdk.error.SDKError, max_tries=3)
async def get_unused_explores(client: looker_sdk.sdk.api40.methods.Looker40SDK):
    """Get explore usage in the last 90 days"""
    query_body = {
        "model": "system__activity",
        "view": "history",
        "fields": ["query.model", "query.view", "history.query_run_count"],
        "filters": {
            "history.created_date": "last 90 days",
            "history.workspace_id": "production",
        },
        "limit": "50000",
    }
    try:
        results_raw = client.run_inline_query(result_format="json", body=query_body)
    except looker_sdk.error.SDKError as e:
        # TODO: Replace with our own error handling
        raise e
    else:
        results = json.loads(results_raw)

    offset = 0
    keep_going = True
    explores = []

    while keep_going:
        models_page = client.all_lookml_models(
            fields="name,explores", limit=100, offset=offset
        )
        for model in models_page:
            for explore in model.explores:
                explores.append({"model": model.name, "explore": explore.name})

        if len(models_page) < 100:
            keep_going = False
        else:
            offset += 100

    for explore in explores:
        explore["query_run_count"] = 0
        for result in results:
            if (
                result["query.model"] == explore["model"]
                and result["query.view"] == explore["explore"]
            ):
                explore["query_run_count"] += result["history.query_run_count"]

    return explores
