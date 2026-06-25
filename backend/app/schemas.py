from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EventCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=3000)
    start_date: date
    end_date: date
    duration_days: int = Field(ge=1, le=365)
    author_login: str = Field(min_length=1, max_length=80)

    @field_validator("name", "description", "author_login")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("Data końca nie może być wcześniejsza niż data początku.")
        total_days = (self.end_date - self.start_date).days + 1
        if self.duration_days > total_days:
            raise ValueError("Długość wydarzenia nie może przekraczać zakresu dat.")
        return self


class ParticipantJoin(BaseModel):
    login: str = Field(min_length=1, max_length=80)

    @field_validator("login")
    @classmethod
    def strip_login(cls, value: str) -> str:
        return value.strip()


class BlockerRangeCreate(BaseModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("Data końca zakresu nie może być wcześniejsza niż data początku.")
        return self


class BlockerCreate(BaseModel):
    login: str = Field(min_length=1, max_length=80)
    dates: list[date] = Field(default_factory=list, max_length=366)
    ranges: list[BlockerRangeCreate] = Field(default_factory=list, max_length=50)

    @field_validator("login")
    @classmethod
    def strip_login(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_payload(self):
        if not self.dates and not self.ranges:
            raise ValueError("Podaj co najmniej jedną datę albo zakres dat.")
        return self


class BlockerRead(BaseModel):
    id: int
    date: date

    model_config = ConfigDict(from_attributes=True)


class ParticipantRead(BaseModel):
    id: int
    login: str
    blockers: list[BlockerRead]

    model_config = ConfigDict(from_attributes=True)


class EventRead(BaseModel):
    code: str
    name: str
    description: str
    start_date: date
    end_date: date
    duration_days: int
    created_by: str
    created_at: datetime
    participants: list[ParticipantRead]


class SuggestionRead(BaseModel):
    start_date: date
    end_date: date
    duration_days: int
    requested_duration_days: int
    shortened: bool


class SuggestionResponse(BaseModel):
    event_code: str
    requested_duration_days: int
    used_duration_days: int | None
    shortened: bool
    suggestions: list[SuggestionRead]


class OperationLogRead(BaseModel):
    id: int
    actor: str
    action: str
    details: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
