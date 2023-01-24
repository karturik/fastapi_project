from typing import Optional, List

from pydantic import BaseModel


class TaskInput(BaseModel):
    sku: int
    link: str
    query: str


class Id(BaseModel):
    id: int


class Res(BaseModel):
    res: Optional[int]
    status: Optional[str]
    sku: int
    link: str
    query: str
    toloka_task_id: Optional[str]


class Message(BaseModel):
    message: str


class Task(BaseModel):
    id: int
    sku: int
    link: str
    query: str
    toloka_task_id: Optional[str]
    ans: Optional[List[int]]
    overlap: Optional[int]
    remaining_overlap: Optional[int]
    count_tasksik: Optional[int]
    res: Optional[int]
    is_more: Optional[bool]
    pool_id: Optional[int]
    status: str

    class Config:
        orm_mode = True


class Balance(BaseModel):
    requests_done: int
    requests_available: int
