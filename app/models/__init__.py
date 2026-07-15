"""alembic/env.py가 `from app import models`로 이 파일을 import해서
Base.metadata에 테이블 정보를 등록한다. 여기서 import하지 않은 모델은
Alembic autogenerate가 감지하지 못하니, 새 모델을 추가할 때마다 반드시 이곳에도 추가할 것.
"""

from app.models.ai_analysis_result import AiAnalysisResult
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.user import User
from app.models.xray_image import XrayImage

__all__ = [
    "User",
    "Patient",
    "MedicalRecord",
    "XrayImage",
    "AiAnalysisResult",
]
