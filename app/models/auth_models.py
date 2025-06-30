# models/auth_models.py
from pydantic import BaseModel, EmailStr
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")

class SignUpRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

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
    data: Optional[T]

class DataResponse(BaseResponse, BaseModel, Generic[T]):
    data: T

class ForgotRequest(BaseModel):
    email: str