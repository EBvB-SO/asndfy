# models/auth_models.py
from pydantic import BaseModel, EmailStr
from typing      import Generic, TypeVar
from pydantic import BaseModel


T = TypeVar("T")

class SignUpRequest(BaseModel):
    name: str
    email: str
    password: str

class SignInRequest(BaseModel):
    email: str
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    message: str
    success: bool

class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str

class BaseResponse(BaseModel):
    success: bool
    message: str

class DataResponse(BaseResponse, BaseModel, Generic[T]):
    data: T
