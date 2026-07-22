from pydantic import BaseModel


class AccessTokenData(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class AccessTokenResponse(BaseModel):
    success: bool = True
    data: AccessTokenData
    message: str = "Access Token이 재발급되었습니다."
