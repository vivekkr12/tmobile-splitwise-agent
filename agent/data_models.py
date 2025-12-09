from pydantic import BaseModel
from typing import List


class LineCharge(BaseModel):
    phone: str
    owner: str
    line_amount: float
    equipement_amount: float
    one_time_amount: float


class TMobileBill(BaseModel):
    month: str
    year: str
    total_due: float
    plan: float
    equipment: float
    one_time_charges: float
    line_charges: List[LineCharge]
