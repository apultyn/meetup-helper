import json
import secrets
import string
from datetime import date, timedelta
from itertools import combinations

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Blocker, Event, OperationLog, Participant
from .schemas import (
    BlockerCreate,
    BlockerRead,
    EventCreate,
    EventRead,
    EventUpdate,
    OperationLogRead,
    ParticipantJoin,
    ParticipantRead,
    SuggestionRead,
    SuggestionResponse,
)


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Meetup Helper API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def login_key(login: str) -> str:
    return login.strip().casefold()


def log_operation(db: Session, event_id: int | None, actor: str, action: str, details: dict) -> None:
    db.add(
        OperationLog(
            event_id=event_id,
            actor=actor.strip() or "system",
            action=action,
            details=json.dumps(details, ensure_ascii=False, default=str),
        )
    )


def generate_event_code(db: Session) -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(20):
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        exists = db.query(Event).filter(Event.code == code).first()
        if exists is None:
            return code
    raise HTTPException(status_code=500, detail="Nie udało się wygenerować unikalnego kodu.")


def get_event_or_404(db: Session, code: str) -> Event:
    event = db.query(Event).filter(Event.code == code.strip().upper()).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono wydarzenia o podanym kodzie.")
    return event


def get_participant(db: Session, event: Event, login: str) -> Participant | None:
    return (
        db.query(Participant)
        .filter(Participant.event_id == event.id, Participant.login_key == login_key(login))
        .first()
    )


def ensure_event_creator(event: Event, login: str) -> None:
    if login_key(event.created_by) != login_key(login):
        raise HTTPException(status_code=403, detail="Tylko twórca wydarzenia może wykonać tę operację.")


def get_or_create_participant(db: Session, event: Event, login: str) -> tuple[Participant, bool]:
    participant = get_participant(db, event, login)
    if participant is not None:
        return participant, False

    participant = Participant(event_id=event.id, login=login.strip(), login_key=login_key(login))
    db.add(participant)
    db.flush()
    return participant, True


def ensure_date_inside_event(event: Event, blocker_date: date) -> None:
    if blocker_date < event.start_date or blocker_date > event.end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Data {blocker_date.isoformat()} jest poza zakresem wydarzenia.",
        )


def expand_blocker_dates(payload: BlockerCreate) -> list[date]:
    dates = set(payload.dates)

    for blocker_range in payload.ranges:
        days_count = (blocker_range.end_date - blocker_range.start_date).days + 1
        for offset in range(days_count):
            dates.add(blocker_range.start_date + timedelta(days=offset))
            if len(dates) > 366:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Jedną operacją można dodać maksymalnie 366 dni blokerów.",
                )

    return sorted(dates)


def blocker_to_schema(blocker: Blocker) -> BlockerRead:
    return BlockerRead(id=blocker.id, date=blocker.date)


def participant_to_schema(participant: Participant) -> ParticipantRead:
    blockers = sorted(participant.blockers, key=lambda blocker: blocker.date)
    return ParticipantRead(
        id=participant.id,
        login=participant.login,
        blockers=[blocker_to_schema(blocker) for blocker in blockers],
    )


def event_to_schema(event: Event) -> EventRead:
    participants = sorted(event.participants, key=lambda participant: participant.login.casefold())
    return EventRead(
        code=event.code,
        name=event.name,
        description=event.description,
        start_date=event.start_date,
        end_date=event.end_date,
        duration_days=event.duration_days,
        created_by=event.created_by,
        created_at=event.created_at,
        participants=[participant_to_schema(participant) for participant in participants],
    )


def find_available_windows(event: Event, limit: int) -> SuggestionResponse:
    participants = sorted(event.participants, key=lambda participant: participant.login.casefold())
    blockers_by_participant = {
        participant.id: {blocker.date for blocker in participant.blockers}
        for participant in participants
    }
    requested_duration = event.duration_days
    total_days = (event.end_date - event.start_date).days + 1
    max_excluded_participants = max(len(participants) - 1, 0)

    for excluded_count in range(0, max_excluded_participants + 1):
        for duration in range(requested_duration, 0, -1):
            stage_suggestions: list[SuggestionRead] = []

            for excluded_participants in combinations(participants, excluded_count):
                excluded_ids = {participant.id for participant in excluded_participants}
                excluded_logins = [participant.login for participant in excluded_participants]
                blocked_dates: set[date] = set()

                for participant in participants:
                    if participant.id not in excluded_ids:
                        blocked_dates.update(blockers_by_participant[participant.id])

                for offset in range(0, total_days - duration + 1):
                    start = event.start_date + timedelta(days=offset)
                    window_dates = {start + timedelta(days=day) for day in range(duration)}

                    if window_dates.isdisjoint(blocked_dates):
                        stage_suggestions.append(
                            SuggestionRead(
                                start_date=start,
                                end_date=start + timedelta(days=duration - 1),
                                duration_days=duration,
                                requested_duration_days=requested_duration,
                                shortened=duration < requested_duration,
                                excluded_participants=excluded_logins,
                                excluded_participants_count=excluded_count,
                            )
                        )

            if stage_suggestions:
                suggestions = sorted(
                    stage_suggestions,
                    key=lambda suggestion: (
                        suggestion.start_date,
                        suggestion.end_date,
                        suggestion.excluded_participants,
                    ),
                )[:limit]

                return SuggestionResponse(
                    event_code=event.code,
                    requested_duration_days=requested_duration,
                    used_duration_days=duration,
                    used_excluded_participants_count=excluded_count,
                    shortened=duration < requested_duration,
                    suggestions=suggestions,
                )

    return SuggestionResponse(
        event_code=event.code,
        requested_duration_days=requested_duration,
        used_duration_days=None,
        used_excluded_participants_count=None,
        shortened=False,
        suggestions=[],
    )


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/events", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    event = Event(
        code=generate_event_code(db),
        name=payload.name,
        description=payload.description,
        start_date=payload.start_date,
        end_date=payload.end_date,
        duration_days=payload.duration_days,
        created_by=payload.author_login,
    )
    db.add(event)
    db.flush()

    participant = Participant(
        event_id=event.id,
        login=payload.author_login,
        login_key=login_key(payload.author_login),
    )
    db.add(participant)
    db.flush()

    log_operation(
        db,
        event.id,
        payload.author_login,
        "event.created",
        {"code": event.code, "name": event.name},
    )
    db.commit()
    db.refresh(event)
    return event_to_schema(event)


@app.get("/api/events/{code}", response_model=EventRead)
def read_event(code: str, db: Session = Depends(get_db)):
    return event_to_schema(get_event_or_404(db, code))


@app.patch("/api/events/{code}", response_model=EventRead)
def update_event(code: str, payload: EventUpdate, db: Session = Depends(get_db)):
    event = get_event_or_404(db, code)
    ensure_event_creator(event, payload.login)

    previous_settings = {
        "start_date": event.start_date.isoformat(),
        "end_date": event.end_date.isoformat(),
        "duration_days": event.duration_days,
    }
    removed_blockers: list[str] = []

    for blocker in list(event.blockers):
        if blocker.date < payload.start_date or blocker.date > payload.end_date:
            removed_blockers.append(blocker.date.isoformat())
            db.delete(blocker)

    event.start_date = payload.start_date
    event.end_date = payload.end_date
    event.duration_days = payload.duration_days

    log_operation(
        db,
        event.id,
        payload.login,
        "event.updated",
        {
            "previous": previous_settings,
            "current": {
                "start_date": event.start_date.isoformat(),
                "end_date": event.end_date.isoformat(),
                "duration_days": event.duration_days,
            },
            "removed_blockers": removed_blockers,
        },
    )
    db.commit()
    db.refresh(event)
    return event_to_schema(event)


@app.post("/api/events/{code}/participants", response_model=EventRead)
def join_event(code: str, payload: ParticipantJoin, db: Session = Depends(get_db)):
    event = get_event_or_404(db, code)
    _, created = get_or_create_participant(db, event, payload.login)

    log_operation(
        db,
        event.id,
        payload.login,
        "participant.created" if created else "participant.rejoined",
        {"login": payload.login},
    )
    db.commit()
    db.refresh(event)
    return event_to_schema(event)


@app.delete("/api/events/{code}/participants/{participant_id}", response_model=EventRead)
def delete_participant(
    code: str,
    participant_id: int,
    login: str = Query(min_length=1, max_length=80),
    db: Session = Depends(get_db),
):
    event = get_event_or_404(db, code)
    ensure_event_creator(event, login)

    participant = (
        db.query(Participant)
        .filter(Participant.id == participant_id, Participant.event_id == event.id)
        .first()
    )
    if participant is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono uczestnika.")
    if login_key(participant.login) == login_key(event.created_by):
        raise HTTPException(status_code=403, detail="Nie można usunąć twórcy wydarzenia.")

    removed_login = participant.login
    removed_blockers_count = len(participant.blockers)
    db.delete(participant)
    log_operation(
        db,
        event.id,
        login,
        "participant.deleted",
        {"login": removed_login, "removed_blockers_count": removed_blockers_count},
    )
    db.commit()
    db.refresh(event)
    return event_to_schema(event)


@app.post("/api/events/{code}/blockers", response_model=EventRead)
def add_blockers(code: str, payload: BlockerCreate, db: Session = Depends(get_db)):
    event = get_event_or_404(db, code)
    participant, participant_created = get_or_create_participant(db, event, payload.login)

    unique_dates = expand_blocker_dates(payload)
    for blocker_date in unique_dates:
        ensure_date_inside_event(event, blocker_date)

    existing_dates = {blocker.date for blocker in participant.blockers}
    created_dates: list[date] = []

    for blocker_date in unique_dates:
        if blocker_date in existing_dates:
            continue
        db.add(Blocker(event_id=event.id, participant_id=participant.id, date=blocker_date))
        created_dates.append(blocker_date)

    if participant_created:
        log_operation(db, event.id, payload.login, "participant.created", {"login": payload.login})

    log_operation(
        db,
        event.id,
        payload.login,
        "blockers.added",
        {
            "dates": [blocker_date.isoformat() for blocker_date in created_dates],
            "ranges": [
                {
                    "start_date": blocker_range.start_date.isoformat(),
                    "end_date": blocker_range.end_date.isoformat(),
                }
                for blocker_range in payload.ranges
            ],
        },
    )
    db.commit()
    db.refresh(event)
    return event_to_schema(event)


@app.delete("/api/events/{code}/blockers/{blocker_id}", response_model=EventRead)
def delete_blocker(
    code: str,
    blocker_id: int,
    login: str = Query(min_length=1, max_length=80),
    db: Session = Depends(get_db),
):
    event = get_event_or_404(db, code)
    participant = get_participant(db, event, login)
    if participant is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono uczestnika o podanym loginie.")

    blocker = db.query(Blocker).filter(Blocker.id == blocker_id, Blocker.event_id == event.id).first()
    if blocker is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono blokera.")
    if blocker.participant_id != participant.id:
        raise HTTPException(status_code=403, detail="Możesz usuwać tylko swoje blokery.")

    removed_date = blocker.date
    db.delete(blocker)
    log_operation(
        db,
        event.id,
        login,
        "blocker.deleted",
        {"date": removed_date.isoformat(), "blocker_id": blocker_id},
    )
    db.commit()
    db.refresh(event)
    return event_to_schema(event)


@app.get("/api/events/{code}/suggestions", response_model=SuggestionResponse)
def calculate_suggestions(
    code: str,
    limit: int = Query(default=10, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    event = get_event_or_404(db, code)
    response = find_available_windows(event, limit)
    log_operation(
        db,
        event.id,
        "system",
        "suggestions.calculated",
        {
            "requested_duration_days": event.duration_days,
            "used_duration_days": response.used_duration_days,
            "used_excluded_participants_count": response.used_excluded_participants_count,
            "suggestions_count": len(response.suggestions),
        },
    )
    db.commit()
    return response


@app.get("/api/events/{code}/logs", response_model=list[OperationLogRead])
def read_logs(code: str, db: Session = Depends(get_db)):
    event = get_event_or_404(db, code)
    return (
        db.query(OperationLog)
        .filter(OperationLog.event_id == event.id)
        .order_by(OperationLog.created_at.desc())
        .limit(100)
        .all()
    )
