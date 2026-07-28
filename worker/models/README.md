# SimpleCNN 모델 파일

과제 제공 파일인 `model_state_dict.pth`를 이 폴더에 둡니다.

이 프로젝트는 파일을 안전하게 읽기 위해 `torch.load(..., weights_only=True)`를 사용하고, 파일에서 확인한 구조를 `worker/model.py`에 재현합니다.

- 입력: grayscale `1 × 128 × 128`
- 구조: `Conv2d(1→16) → MaxPool → Conv2d(16→32) → MaxPool → Linear(32768→2)`
- 출력: 2개 클래스 softmax

`model.pth`는 전체 객체 피클이며 `__main__.SimpleCNN` 클래스 경로에 의존하므로 사용하지 않습니다. `model_state_dict.pth`만 사용합니다.

학습 코드가 제공되지 않았으므로 클래스 순서와 학습 전처리 기준은 팀이 강사에게 확인해 문서화해야 합니다. 현재 코드의 `index 1 = pneumonia`는 과제 데모를 위한 명시적 가정입니다.
