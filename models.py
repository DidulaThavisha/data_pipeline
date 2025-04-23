from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
import datetime
from database import Base

class DataRequest(Base):
    __tablename__ = "data_requests"
    
    id = Column(String, primary_key=True)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    records_processed = Column(Integer, default=0)
    error_message = Column(String, nullable=True)
    
    # Relationship to the processed data
    processed_data = relationship("ProcessedData", back_populates="request")

class ProcessedData(Base):
    __tablename__ = "processed_data"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, ForeignKey("data_requests.id"))
    source = Column(String, nullable=False)
    category = Column(String, index=True)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationship to the data request
    request = relationship("DataRequest", back_populates="processed_data")
