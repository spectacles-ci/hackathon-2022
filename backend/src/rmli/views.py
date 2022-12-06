import asyncio
import json
from typing import Any

import backoff
import looker_sdk
from fastapi import FastAPI
from looker_sdk.error import SDKError
from looker_sdk.sdk.api40.methods import Looker40SDK as LookerSdkClient
from looker_sdk.sdk.api40.models import User, WriteQuery

from rmli.models import (
    ExplorePerformance,
    ExploreQueries,
    ExploreSize,
    ExploreSizeResult,
    InactiveUserResult,
    LookerConfig,
    SlowExploresResult,
    UnusedExploreResult,
)

app = FastAPI()


class AppApiSettings(looker_sdk.api_settings.ApiSettings):
    def __init__(self, *args, **kw_args) -> None:  # type: ignore
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


def get_looker_client(config: LookerConfig) -> LookerSdkClient:
    """Set up the Looker API client using a LookerConfig."""
    return looker_sdk.init40(config_settings=AppApiSettings(**dict(config)))


@app.post(
    "/stats/inactive_users",
    response_model=InactiveUserResult,
    response_model_by_alias=False,
)
async def inactive_users(config: LookerConfig) -> InactiveUserResult:
    client = get_looker_client(config)
    inactive_user_pct = await get_inactive_user_percentage(client)
    return InactiveUserResult(pct_inactive=inactive_user_pct)


@app.post(
    "/stats/slow_explores",
    response_model=SlowExploresResult,
    response_model_by_alias=False,
)
async def slow_explores(config: LookerConfig) -> SlowExploresResult:
    client = get_looker_client(config)
    results = await get_longest_running_explores(client)
    slow_explores = [ExplorePerformance.parse_obj(result) for result in results]
    top_3 = sorted(
        slow_explores, key=lambda explore: explore.avg_runtime, reverse=True
    )[:3]
    return SlowExploresResult(slow_explores=top_3)


@app.post(
    "/stats/large_explores",
    response_model=ExploreSizeResult,
    response_model_by_alias=False,
)
async def large_explores(config: LookerConfig) -> ExploreSizeResult:
    client = get_looker_client(config)
    results = await get_explore_field_count(client)
    slow_explores = [ExploreSize.parse_obj(result) for result in results]
    top_3 = sorted(
        slow_explores, key=lambda explore: explore.field_count, reverse=True
    )[:3]
    return ExploreSizeResult(large_explores=top_3)


@app.post(
    "/stats/unused_explores",
    response_model=UnusedExploreResult,
    response_model_by_alias=False,
)
async def unused_explores(config: LookerConfig) -> UnusedExploreResult:
    client = get_looker_client(config)
    results = await get_unused_explores(client)
    print(results)
    slow_explores = [ExploreQueries.parse_obj(result) for result in results]
    top_3 = sorted(slow_explores, key=lambda explore: explore.query_count)[:3]
    return UnusedExploreResult(unused_explores=top_3)


@app.post("/")
async def health_check() -> str:
    return "ok"


@backoff.on_exception(backoff.expo, SDKError, max_tries=3)
async def get_longest_running_explores(client: LookerSdkClient) -> Any:
    """Get the 10 Explores with the longest average runtime in Looker"""
    query = WriteQuery(
        model="system__activity",
        view="history",
        fields=[
            "query.view",
            "query.model",
            "history.average_runtime",
            "history.max_runtime",
        ],
        filters={"history.created_date": "last 90 days"},
        limit="10",
        sorts=["history.average_runtime desc"],
    )
    try:
        results_raw = client.run_inline_query(result_format="json", body=query)
    except SDKError as e:
        # TODO: Replace with our own error handling
        raise e
    else:
        results = json.loads(results_raw)

    return results


@backoff.on_exception(backoff.expo, SDKError, max_tries=3)
async def get_inactive_user_percentage(client: LookerSdkClient) -> float:
    """Get the percentage of inactive users in Looker"""
    query = WriteQuery(
        model="system__activity",
        view="history",
        fields=["history.user_id"],
        filters={"history.created_date": "last 30 days"},
        limit="50000",
    )
    try:
        results_raw = client.run_inline_query(result_format="json", body=query)
    except SDKError as e:
        # TODO: Replace with our own error handling
        raise e
    else:
        active_users = json.loads(results_raw)

    # Get the IDs of all the users with queries in the last 30 days
    active_users_list = [user["history.user_id"] for user in active_users]

    offset = 0
    keep_going = True
    all_users: list[User] = []

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
        [user for user in all_users if user.id and int(user.id) in active_users_list]
    )
    inactive_user_percentage = (all_users_count - active_users_count) / all_users_count

    return inactive_user_percentage


@backoff.on_exception(backoff.expo, SDKError, max_tries=3)
async def get_explore_field_count(client: LookerSdkClient) -> list[dict[str, Any]]:
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
                    if model.name and explore.name:
                        explores.append({"model": model.name, "explore": explore.name})

        if len(models_page) < 100:
            keep_going = False
        else:
            offset += 100

    # Get all the number of fields in each explore
    tasks = (
        get_explore_field_counts(client, explore["model"], explore["explore"])
        for explore in explores
    )
    explore_fields: list[dict[str, Any]] = await asyncio.gather(*tasks)
    return explore_fields


@backoff.on_exception(backoff.expo, SDKError, max_tries=3)
async def get_unused_explores(client: LookerSdkClient) -> list[dict[str, Any]]:
    """Get explore usage in the last 90 days"""
    query = WriteQuery(
        model="system__activity",
        view="history",
        fields=["query.model", "query.view", "history.query_run_count"],
        filters={
            "history.created_date": "last 90 days",
            "history.workspace_id": "production",
        },
        limit="50000",
    )
    try:
        results_raw = client.run_inline_query(result_format="json", body=query)
    except SDKError as e:
        # TODO: Replace with our own error handling
        raise e
    else:
        results = json.loads(results_raw)

    offset = 0
    keep_going = True
    explores: list[dict[str, Any]] = []

    # Get all the explores in Looker
    while keep_going:
        models_page = client.all_lookml_models(
            fields="name,explores", limit=100, offset=offset
        )
        for model in models_page:
            if model.explores:
                for model_explore in model.explores:
                    if model.name and model_explore.name:
                        explores.append(
                            {"model": model.name, "explore": model_explore.name}
                        )

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
        explore for explore in explores if int(explore["query_run_count"]) < 50
    ]

    return unused_explores


@backoff.on_exception(backoff.expo, SDKError, max_tries=3)
async def get_unused_fields(client: LookerSdkClient) -> list[dict[str, Any]]:
    """Get field usage in the last 90 days"""
    query = WriteQuery(
        model="system__activity",
        view="field_usage",
        fields=[
            "field_usage.model",
            "field_usage.explore",
            "field_usage.view",
            "field_usage.field",
            "field_usage.times_used",
        ],
        limit="50000",
    )
    try:
        results_raw = client.run_inline_query(result_format="json", body=query)
    except SDKError as e:
        # TODO: Replace with our own error handling
        raise e
    else:
        results = json.loads(results_raw)

    offset = 0
    keep_going = True
    explores: list[dict[str, Any]] = []

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


async def get_explore_fields(
    client: LookerSdkClient, model: str, explore: str
) -> dict[str, Any]:
    print(f"Getting fields for {model}.{explore}")
    explore_fields = client.lookml_model_explore(
        lookml_model_name=model, explore_name=explore, fields="fields"
    )

    fields = []
    if explore_fields.fields:
        if explore_fields.fields.dimensions:
            fields.extend(
                [dimension.name for dimension in explore_fields.fields.dimensions]
            )
        if explore_fields.fields.measures:
            fields.extend([measure.name for measure in explore_fields.fields.measures])

    return {
        "model": model,
        "explore": explore,
        "fields": fields,
    }


async def get_explore_field_counts(
    client: LookerSdkClient, model: str, explore: str
) -> dict[str, Any]:
    fields = await get_explore_fields(client, model, explore)

    result = {
        "model": fields["model"],
        "explore": fields["explore"],
        "field_count": len(fields["fields"]),
    }
    return result