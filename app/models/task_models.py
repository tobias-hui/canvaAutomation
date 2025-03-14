from sqlalchemy import Column, String, DateTime, JSON
from datetime import datetime
from app.core.database import Base
from pydantic import HttpUrl, AnyUrl

def serialize_request_data(data: dict) -> dict:
    """序列化请求数据，处理特殊类型"""
    serialized = {}
    for key, value in data.items():
        if hasattr(value, '__str__') and isinstance(value, AnyUrl):
            serialized[key] = str(value)
        elif isinstance(value, dict):
            serialized[key] = serialize_request_data(value)
        else:
            serialized[key] = value
    return serialized

class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(String, primary_key=True, index=True)
    status = Column(String, index=True)
    message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    output_url = Column(String, nullable=True)
    error = Column(String, nullable=True)
    request_data = Column(JSON, nullable=True)  # 存储请求数据
    result = Column(JSON, nullable=True)  # 存储处理结果

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "status": self.status,
            "message": self.message,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "output_url": self.output_url,
            "error": self.error,
            "result": self.result
        } 