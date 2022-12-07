import abc
from typing import Any, Literal, Type

from pydantic import BaseModel, Field

Grade = Literal["bad", "ok", "good"]


class LookerConfig(BaseModel):
    host_url: str
    port: int
    client_id: str
    client_secret: str


class Explore(BaseModel):
    model_name: str
    explore_name: str


class ExploreSize(BaseModel):
    model_name: str = Field(alias="model")
    explore_name: str = Field(alias="explore")
    field_count: int


class ExplorePerformance(BaseModel):
    model_name: str = Field(alias="query.model")
    explore_name: str = Field(alias="query.view")
    avg_runtime: float = Field(alias="history.average_runtime")  # seconds
    max_runtime: float = Field(alias="history.max_runtime")  # seconds


class ExploreQueries(BaseModel):
    model_name: str = Field(alias="model")
    explore_name: str = Field(alias="explore")
    query_count: int = Field(alias="query_run_count")


class ExploreUnusedFields(BaseModel):
    model_name: str
    explore_name: str
    pct_unused: float


class TestResult(BaseModel, abc.ABC):
    name: str

    @property
    @abc.abstractmethod
    def grade(self) -> Grade:
        """Calculate a grade for this test result given the input data."""
        raise NotImplementedError

    def dict(self, *args, **kwargs) -> dict[str, Any]:
        """Include the computed grade in the dict representation."""
        base = super().dict(*args, **kwargs)
        return {**base, "grade": self.grade}

    class Config:
        @staticmethod
        def schema_extra(schema: dict[str, Any], model: Type["TestResult"]) -> None:
            schema["properties"]["grade"] = {
                "title": "Grade",
                "type": "string",
                "enum": ["bad", "ok", "good"],
            }


class InactiveUserResult(TestResult):
    name: Literal["Inactive Users"] = "Inactive Users"
    test_id: Literal["inactive_users"] = "inactive_users"
    pct_inactive: float
    sample_user_names: list[str]

    @property
    def grade(self) -> Grade:
        if self.pct_inactive > 0.3:
            return "bad"
        elif self.pct_inactive > 0.1:
            return "ok"
        else:
            return "good"


class SlowExploresResult(TestResult):
    name: Literal["Slow Explores"] = "Slow Explores"
    test_id: Literal["slow_explores"] = "slow_explores"
    slow_explores: list[ExplorePerformance]  # sorted by avg_runtime, descending

    @property
    def grade(self) -> Grade:
        if self.slow_explores[0].avg_runtime > 40:
            return "bad"
        elif self.slow_explores[0].avg_runtime > 20:
            return "ok"
        else:
            return "good"
        return "bad"


class ExploreSizeResult(TestResult):
    name: Literal["Large Explores"] = "Large Explores"
    test_id: Literal["large_explores"] = "large_explores"
    large_explores: list[ExploreSize]  # sorted by field_count, descending
    median_explore_size: int

    @property
    def grade(self) -> Grade:
        if self.large_explores[0].field_count >= 750:
            return "bad"
        elif self.large_explores[0].field_count >= 300:
            return "ok"
        else:
            return "good"


class UnusedExploreResult(TestResult):
    name: Literal["Unused Explores"] = "Unused Explores"
    test_id: Literal["unused_explores"] = "unused_explores"
    unused_explores: list[ExploreQueries]  # sorted by query_count, descending

    @property
    def grade(self) -> Grade:
        return "bad"


class UnusedFieldsResult(TestResult):
    name: Literal["Unused Fields"] = "Unused Fields"
    test_id: Literal["unused_fields"] = "unused_fields"
    pct_unused: float

    @property
    def grade(self) -> Grade:
        return "bad"


class UnusedFieldsExploreResult(TestResult):
    name: Literal["Explores with Unused Fields"] = "Explores with Unused Fields"
    test_id: Literal["explores_with_unused_fields"] = "explores_with_unused_fields"
    explores: list[ExploreUnusedFields]

    @property
    def grade(self) -> Grade:
        return "bad"
