from pydantic import BaseModel


class AccessTokenData(BaseModel):
    accessToken: str
    tokenType: str = "Bearer"
    expiresIn: int


class AccessTokenResponse(BaseModel):
    success: bool = True
    data: AccessTokenData
    message: str = "Access Token이 재발급되었습니다."
