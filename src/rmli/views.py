from fastapi import FastAPI
from pydantic import BaseModel
import looker_sdk
from looker_sdk.error import SDKError
import asyncio
import json
import backoff

app = FastAPI()
LookerSdkClient = looker_sdk.methods40.Looker40SDK


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
        get_unused_fields(client),
    )
    return results


@backoff.on_exception(backoff.expo, SDKError, max_tries=3)
async def get_longest_running_queries(client: LookerSdkClient):
    """Get the 10 queries with the longest average runtime in Looker"""
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
        "sorts": ["history.average_runtime desc"],
    }
    try:
        results_raw = client.run_inline_query(result_format="json", body=query_body)
    except SDKError as e:
        # TODO: Replace with our own error handling
        raise e
    else:
        results = json.loads(results_raw)

    return results


@backoff.on_exception(backoff.expo, SDKError, max_tries=3)
async def get_inactive_user_percentage(
    client: LookerSdkClient,
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
    except SDKError as e:
        # TODO: Replace with our own error handling
        raise e
    else:
        active_users = json.loads(results_raw)

    # Get the IDs of all the users with queries in the last 30 days
    active_users_list = [user["history.user_id"] for user in active_users]

    offset = 0
    keep_going = True
    all_users = []

    # Get all the users in Looker
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

    # Filter out disabled users and Looker employees
    all_users = [
        user
        for user in all_users
        if not user.is_disabled and not user.verified_looker_employee
    ]

    # Do some counting
    all_users_count = len(all_users)
    active_users_count = len(
        [user for user in all_users if int(user.id) in active_users_list]
    )
    inactive_user_percentage = (all_users_count - active_users_count) / all_users_count

    return inactive_user_percentage


@backoff.on_exception(backoff.expo, SDKError, max_tries=3)
async def get_explore_and_field_count(client: LookerSdkClient):
    """Get the number of explores and fields in Looker"""
    offset = 0
    keep_going = True
    explores = []

    # Get all the explores in Looker
    while keep_going:
        models_page = client.all_lookml_models(
            fields="name,explores", limit=100, offset=offset
        )
        for model in models_page:
            if model.explores:
                for explore in model.explores:
                    explores.append({"model": model.name, "explore": explore.name})

        if len(models_page) < 100:
            keep_going = False
        else:
            offset += 100

    # Get all the number of fields in each explore
    tasks = tuple(
        get_explore_field_counts(client, explore["model"], explore["explore"])
        for explore in explores
    )
    explore_fields = await asyncio.gather(*tasks)

    return explore_fields


@backoff.on_exception(backoff.expo, SDKError, max_tries=3)
async def get_unused_explores(client: LookerSdkClient):
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
    except SDKError as e:
        # TODO: Replace with our own error handling
        raise e
    else:
        results = json.loads(results_raw)

    offset = 0
    keep_going = True
    explores = []

    # Get all the explores in Looker
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

    # Get the run count for each explore
    for explore in explores:
        explore["query_run_count"] = 0
        for result in results:
            if (
                result["query.model"] == explore["model"]
                and result["query.view"] == explore["explore"]
            ):
                explore["query_run_count"] += result["history.query_run_count"]

    # Filter out explores with less than 50 runs in the last 90 days
    unused_explores = [
        explore for explore in explores if explore["query_run_count"] < 50
    ]

    return unused_explores


@backoff.on_exception(backoff.expo, SDKError, max_tries=3)
async def get_unused_fields(client: LookerSdkClient):
    """Get field usage in the last 90 days"""
    query_body = {
        "model": "system__activity",
        "view": "field_usage",
        "fields": [
            "field_usage.model",
            "field_usage.explore",
            "field_usage.view",
            "field_usage.field",
            "field_usage.times_used",
        ],
        "limit": "50000",
    }
    try:
        results_raw = client.run_inline_query(result_format="json", body=query_body)
    except SDKError as e:
        # TODO: Replace with our own error handling
        raise e
    else:
        results = json.loads(results_raw)

    offset = 0
    keep_going = True
    explores = []

    # Get all the explores in Looker
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

    # Get the fields for each explore
    tasks = tuple(
        get_explore_fields(client, explore["model"], explore["explore"])
        for explore in explores
    )
    explore_fields = await asyncio.gather(*tasks)

    # Get the run count for each field
    output = []
    for explore in explore_fields:
        for field in explore["fields"]:
            times_used = 0
            for result in results:
                if (
                    result["field_usage.model"] == explore["model"]
                    and result["field_usage.explore"] == explore["explore"]
                    and result["field_usage.field"] == field
                ):
                    times_used += result["field_usage.times_used"]
            output.append(
                {
                    "model": explore["model"],
                    "explore": explore["explore"],
                    "field": field,
                    "times_used": times_used,
                }
            )

    # Filter out fields with less than 50 runs in the last 90 days
    unused_fields = [field for field in output if field["times_used"] < 50]

    return unused_fields


async def get_explore_fields(client, model, explore):
    print(f"Getting fields for {model}.{explore}")
    explore_fields = client.lookml_model_explore(
        lookml_model_name=model, explore_name=explore, fields="fields"
    )

    dimensions = [dimension.name for dimension in explore_fields.fields.dimensions]
    measures = [measure.name for measure in explore_fields.fields.measures]
    fields = dimensions + measures

    return {
        "model": model,
        "explore": explore,
        "fields": fields,
    }


async def get_explore_field_counts(client, model, explore):
    fields = await get_explore_fields(client, model, explore)

    result = {
        "model": fields["model"],
        "explore": fields["explore"],
        "field_count": len(fields["fields"]),
    }
    return result
