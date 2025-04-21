from pydantic import BaseModel, Field
from datetime import datetime

class HealthVitals(BaseModel):
    glucose: float = Field(..., title="Blood Glucose Level (BGL)")
    diastolic: float = Field(..., title="Diastolic Blood Pressure")
    systolic: float = Field(..., title="Systolic Blood Pressure")
    heart_rate: float = Field(..., title="Heart Rate")
    temperature: float = Field(..., title="Body Temperature")
    spo2: float = Field(..., title="SPO2")
    timestamp: datetime = Field(default_factory=datetime.now, title="Record Timestamp")
