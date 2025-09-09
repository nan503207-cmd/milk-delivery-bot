# -*- coding: utf-8 -*-
# 重置所有表结构（DROP + CREATE）
from sqlalchemy import create_engine
from config import DB_URL
from models import Base

engine = create_engine(DB_URL, future=True)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("✅ Database schema reset done.")
