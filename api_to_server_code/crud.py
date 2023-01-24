from sqlalchemy.orm import Session

import models
from schema import TaskInput


def get_task(db: Session, task_id: int):
    return db.query(models.Entries).filter(models.Entries.id == task_id).first()


def create_task(db: Session, task: TaskInput, **kwargs):
    entry = models.Entries(**task.dict(), status="Submitted", **kwargs)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
