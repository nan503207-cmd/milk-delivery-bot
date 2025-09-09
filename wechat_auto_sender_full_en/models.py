# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Numeric
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    wx_display_name = Column(String, nullable=False)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    preferred_send_time = Column(String, nullable=True)
    active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)

    subscriptions = relationship("Subscription", back_populates="customer")
    tasks = relationship("Task", back_populates="customer")

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    type = Column(String, nullable=False)  # 'by_bottle' or 'by_amount'
    unit_price = Column(Numeric(10, 2), nullable=True)
    status = Column(String, default="active")
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    note = Column(Text, nullable=True)

    customer = relationship("Customer", back_populates="subscriptions")
    transactions = relationship("LedgerTransaction", back_populates="subscription")
    tasks = relationship("Task", back_populates="subscription")

class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    ts = Column(DateTime, default=datetime.now, nullable=False)
    kind = Column(String, nullable=False)  # purchase/delivery/refund/manual_adjust
    bottle_delta = Column(Integer, default=0)
    amount_delta = Column(Numeric(10, 2), default=0)
    ref_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    memo = Column(Text, nullable=True)

    subscription = relationship("Subscription", back_populates="transactions")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    send_time = Column(DateTime, nullable=False, default=datetime.now)
    template_key = Column(String, nullable=False)
    payload_json = Column(Text, nullable=True)
    status = Column(String, default="pending")
    result_log = Column(Text, nullable=True)
    try_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)

    customer = relationship("Customer", back_populates="tasks")
    subscription = relationship("Subscription", back_populates="tasks")
