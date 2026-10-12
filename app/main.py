import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Response
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_session, make_engine
from app.models import Base, Issue
from app.schemas import IssueCreate, IssueRead, IssueUpdate

SessionDep = Annotated[Session, Depends(get_session)]
IssueId = Annotated[int, Path(gt=0)]


def create_app(database_url: str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        engine = make_engine(database_url or os.getenv("DATABASE_URL", "sqlite:////data/issues.db"))
        application.state.engine = engine
        try:
            Base.metadata.create_all(engine)
            yield
        finally:
            engine.dispose()

    application = FastAPI(
        title="Request Log — 業務改善リクエスト管理API",
        description="改善要望の登録・一覧・詳細・部分更新を提供する1日版MVP。",
        version="0.1.0",
        lifespan=lifespan,
    )

    @application.get("/health", tags=["health"], responses={503: {"description": "DB unavailable"}})
    def health(session: SessionDep) -> dict[str, str]:
        try:
            session.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            raise HTTPException(status_code=503, detail="Database unavailable") from error
        return {"status": "ok"}

    @application.post("/issues", response_model=IssueRead, status_code=201, tags=["issues"])
    def create_issue(payload: IssueCreate, response: Response, session: SessionDep) -> Issue:
        issue = Issue(**payload.model_dump())
        session.add(issue)
        session.commit()
        session.refresh(issue)
        response.headers["Location"] = f"/issues/{issue.id}"
        return issue

    @application.get("/issues", response_model=list[IssueRead], tags=["issues"])
    def list_issues(
        session: SessionDep,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[Issue]:
        return list(session.scalars(select(Issue).order_by(Issue.id).offset(offset).limit(limit)))

    def find_issue(issue_id: int, session: Session) -> Issue:
        issue = session.get(Issue, issue_id)
        if issue is None:
            raise HTTPException(status_code=404, detail="Issue not found")
        return issue

    @application.get(
        "/issues/{issue_id}",
        response_model=IssueRead,
        tags=["issues"],
        responses={404: {"description": "Issue not found"}},
    )
    def get_issue(issue_id: IssueId, session: SessionDep) -> Issue:
        return find_issue(issue_id, session)

    @application.patch(
        "/issues/{issue_id}",
        response_model=IssueRead,
        tags=["issues"],
        responses={404: {"description": "Issue not found"}},
    )
    def update_issue(issue_id: IssueId, payload: IssueUpdate, session: SessionDep) -> Issue:
        issue = find_issue(issue_id, session)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(issue, key, value)
        session.commit()
        session.refresh(issue)
        return issue

    return application


app = create_app()
