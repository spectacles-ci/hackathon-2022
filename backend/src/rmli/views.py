import asyncio
import json
from typing import Any
import statistics

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
    AbandonedDashboardResult,
    DashboardUsage,
    OverusedQueryResult,
    QueryUsage,
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


@app.post("/stats/inactive_users", response_model=InactiveUserResult)
async def inactive_users(config: LookerConfig) -> InactiveUserResult:
    client = get_looker_client(config)
    inactive_user_pct, sample_inactive_users = await get_inactive_user_percentage(
        client
    )
    return InactiveUserResult(
        pct_inactive=inactive_user_pct, sample_user_names=sample_inactive_users
    )


@app.post("/stats/slow_explores", response_model=SlowExploresResult)
async def slow_explores(config: LookerConfig) -> SlowExploresResult:
    client = get_looker_client(config)
    results = await get_longest_running_explores(client)
    slow_explores = [ExplorePerformance.parse_obj(result) for result in results]
    top_3 = sorted(
        slow_explores, key=lambda explore: explore.avg_runtime, reverse=True
    )[:3]
    return SlowExploresResult(slow_explores=top_3)


@app.post("/stats/large_explores", response_model=ExploreSizeResult)
async def large_explores(config: LookerConfig) -> ExploreSizeResult:
    client = get_looker_client(config)
    results = await get_explore_field_count(client)
    large_explores = [ExploreSize.parse_obj(result) for result in results]
    top_3 = sorted(
        large_explores, key=lambda explore: explore.field_count, reverse=True
    )[:3]
    median_explore_size = int(
        statistics.median([explore.field_count for explore in large_explores])
    )
    return ExploreSizeResult(
        large_explores=top_3, median_explore_size=median_explore_size
    )


@app.post("/stats/unused_explores", response_model=UnusedExploreResult)
async def unused_explores(config: LookerConfig) -> UnusedExploreResult:
    client = get_looker_client(config)
    results = await get_unused_explores(client)
    explores = [ExploreQueries.parse_obj(result) for result in results]
    count_explores = len(explores)
    unused_explores = [explore for explore in explores if explore.query_count == 0]
    count_unused_explores = len(unused_explores)
    unused_percentage = count_unused_explores / count_explores
    top_3 = sorted(unused_explores, key=lambda explore: explore.query_count)[:3]
    return UnusedExploreResult(
        unused_explores=top_3, unused_percentage=unused_percentage
    )


@app.post(
    "/stats/abandoned_dashboards",
    response_model=AbandonedDashboardResult,
    response_model_by_alias=False,
)
async def abandoned_dashboards(config: LookerConfig) -> AbandonedDashboardResult:
    client = get_looker_client(config)
    results = await get_dashboard_usage(client)
    dashboards = [DashboardUsage.parse_obj(result) for result in results]
    dashboard_count = len(dashboards)
    abandoned_dashboards = [
        dashboard for dashboard in dashboards if dashboard.query_count == 0
    ]
    abandoned_dashboard_count = len(abandoned_dashboards)
    pct_abandoned = abandoned_dashboard_count / dashboard_count
    sample_abandoned_dashboards = sorted(
        abandoned_dashboards, key=lambda dashboard: dashboard.dashboard_id
    )[:3]

    return AbandonedDashboardResult(
        pct_abandoned=pct_abandoned,
        count_abandoned=abandoned_dashboard_count,
        sample_abandoned_dashboards=sample_abandoned_dashboards,
    )


@app.post(
    "/stats/overused_queries",
    response_model=OverusedQueryResult,
    response_model_by_alias=False,
)
async def overused_queries(config: LookerConfig) -> OverusedQueryResult:
    client = get_looker_client(config)
    results = await get_query_usage(client)
    queries = [QueryUsage.parse_obj(result) for result in results]
    return OverusedQueryResult(sample_overused_queries=queries)


@app.get("/")
async def health_check() -> str:
    return "ok"


@backoff.on_exception(backoff.expo, SDKError, max_tries=3)
async def get_dashboard_usage(
    client: LookerSdkClient,
) -> list[dict[str, Any]]:
    """Get all dashboards and their query volume in the last 90 days"""
    all_dashboards = client.all_dashboards(fields="id,title")

    query = WriteQuery(
        model="system__activity",
        view="history",
        fields=["history.real_dash_id", "history.query_run_count"],
        filters={"history.created_date": "last 90 days"},
    )
    try:
        results_raw = client.run_inline_query(result_format="json", body=query)
    except SDKError as e:
        # TODO: Replace with our own error handling
        raise e
    else:
        results = json.loads(results_raw)

    output = []

    for dashboard in all_dashboards:
        query_count = 0
        for result in results:
            if result["history.real_dash_id"] == dashboard.id:
                query_count += result["history.query_run_count"]
        if dashboard.id and dashboard.title:
            output.append(
                {
                    "dashboard_id": dashboard.id,
                    "dashboard_title": dashboard.title,
                    "query_count": query_count,
                }
            )

    return output


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
        filters={
            "history.created_date": "last 90 days",
            "history.query_run_count": ">= 100",
        },
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
async def get_inactive_user_percentage(
    client: LookerSdkClient,
) -> tuple[float, list[str]]:
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
    active_users_list = [str(user["history.user_id"]) for user in active_users]

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
    inactive_users = [user for user in all_users if user.id not in active_users_list]
    inactive_users_count = len(inactive_users)
    inactive_user_percentage = inactive_users_count / all_users_count

    sample_count = 0
    sample_user_names = []
    i = 0

    while sample_count < 3 and i + 1 <= inactive_users_count:
        inactive_user_id = str(inactive_users[i].id)
        display_name = client.user(inactive_user_id).display_name
        if display_name:
            sample_user_names.append(display_name)
            sample_count += 1
        i += 1

    return inactive_user_percentage, sample_user_names


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
                    if model.name and model_explore.name and not model_explore.hidden:
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

    return explores


@backoff.on_exception(backoff.expo, SDKError, max_tries=3)
async def get_query_usage(client: LookerSdkClient) -> list[dict[str, Any]]:
    """Get queries most frequently run queries in last 7 days"""
    query = WriteQuery(
        model="system__activity",
        view="history",
        fields=[
            "query.view",
            "query.model",
            "query.id",
            "history.issuer_source",
            "history.source",
            "history.database_result_query_count",
            "history.cache_result_query_count",
        ],
        limit="10",
        sorts=["history.database_result_query_count desc"],
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
