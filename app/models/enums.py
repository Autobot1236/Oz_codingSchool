import enum


class Gender(str, enum.Enum):
    M = "male"
    F = "female"

class Role(str, enum.Enum):
    PENDING = "권한 부여 대기"
    STAFF = "폐렴 추적 관련 데이터 CRUD 허용"
    ADMIN = "전체데이터 CRUD 허용"

class Department(str, enum.Enum):
    MEDICAL = "의료진"
    DEV = "개발팀"
    RESEARCH = "연구진"
