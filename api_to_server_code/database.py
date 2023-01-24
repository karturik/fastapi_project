import json

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

with open("config.json") as config:
    c = json.load(config)
    user = c["user"]
    password = c["password"]
    url = c["database-url"]
    port = c["database-port"]
    database = c["database-name"]

engine = create_engine(f'postgresql+psycopg2://{user}:{password}@{url}:{port}/{database}')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
