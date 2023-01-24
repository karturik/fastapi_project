import logging
from logging.handlers import RotatingFileHandler

import pydantic
from fastapi import FastAPI, Depends, Request, status, Header, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from sqlalchemy.orm import Session

import crud
from authorization import authorize
from database import SessionLocal
from models import Users
from schema import TaskInput, Id, Res, Message, Balance


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def increase_requests_done(db: Session, user: Users):
    if not user.can_do_requests():
        max_requests = user.requests_available
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your request limit is {max_requests}. You have already submitted {max_requests} tasks. "
                   f"To increase the limit, contact the administrator data-relevance.ru"
        )
    user.requests_done = Users.requests_done + 1
    db.commit()


def add_authorization(authorization: str = Header(""), db: Session = Depends(get_db)):
    if authorization == "":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    user = authorize(db, authorization)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user


app = FastAPI()

app.add_middleware(HTTPSRedirectMiddleware)


@app.post("/add_task", response_model=Id, responses={401: {"model": Message}})
def add_task(task_input: TaskInput, db: Session = Depends(get_db), user: Users = Depends(add_authorization)):
    increase_requests_done(db, user)
    return Id(id=crud.create_task(db, task_input, submitted_by_id=user.id, pool_id=user.pool).id)


@app.get("/get_task",
         response_model=Res,
         responses={202: {"model": Message}, 401: {"model": Message}, 404: {"model": Message}, 425: {"model": Res}})
def get_task(task_id: int, db: Session = Depends(get_db), user: Users = Depends(add_authorization)):
    task = crud.get_task(db, task_id)
    if task is None or task.submitted_by.id != user.id:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": "Not found"})

    res = Res(res=task.res, status=task.status, sku=task.sku, link=task.link, query=task.query, toloka_task_id=task.toloka_task_id)
    if task.status != "Done":
        return JSONResponse(status_code=status.HTTP_425_TOO_EARLY, content=res.dict())
    return res


@app.get("/check_balance", response_model=Balance, responses={401: {"model": Message}})
def check_balance(user: Users = Depends(add_authorization)):
    return Balance(requests_done=user.requests_done, requests_available=user.requests_available)
