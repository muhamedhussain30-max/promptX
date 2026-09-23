from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    display_name: str


class UserOut(BaseModel):
    id: str
    username: str
    display_name: str
    is_host: bool

    model_config = {"from_attributes": True}
