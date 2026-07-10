import math
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel


class R(BaseModel):
    conf: float


print(jsonable_encoder(R(conf=math.nan)))
