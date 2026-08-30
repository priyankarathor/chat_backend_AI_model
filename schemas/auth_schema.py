from pydantic import BaseModel, EmailStr, Field

class RegisterUser(BaseModel):
    name : str = Field(..., min_length=2, max_length=100)
    email:EmailStr
    password:str = Field(...,min_length=5, max_length=20)

class UserResponse(BaseModel):
    name: str
    email:EmailStr


class LoginUser(BaseModel):
    email:EmailStr

    password:str = Field(

        ...,
        min_length=5,
        max_length=20
    )

class userResponse(BaseModel):
    name:str
    email:EmailStr

class TokenResponse(BaseModel):
    access_token:str
    token_type:str    