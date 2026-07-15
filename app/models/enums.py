"""ERD의 Enum 정의를 그대로 옮긴 Python Enum 클래스들.

dbdiagram.io ERD 원문:
    Enum gender { M [male], F [female] }
    Enum role { PENDING [권한 부여 대기], STAFF [제한된 CRUD], ADMIN [전체 CRUD] }
    Enum department { MEDICAL [의료진], DEV [개발팀], RESEARCH [연구진] }
"""

import enum


class GenderEnum(str, enum.Enum):
    M = "M"
    F = "F"


class RoleEnum(str, enum.Enum):
    PENDING = "PENDING"
    STAFF = "STAFF"
    ADMIN = "ADMIN"


class DepartmentEnum(str, enum.Enum):
    MEDICAL = "MEDICAL"
    DEV = "DEV"
    RESEARCH = "RESEARCH"
