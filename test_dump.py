from pydantic import BaseModel, Field
from pydantic_core import to_json

class MyModel(BaseModel):
    a: int
    b: dict = Field(exclude=True)

m = MyModel(a=1, b={"huge": "payload"})
print(m.model_dump(mode='json'))
print(to_json(m))
