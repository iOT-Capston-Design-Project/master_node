from enum import Enum


class PostureType(Enum):
    """환자 자세 유형"""
    UNKNOWN = 0
    SITTING = 1
    LEFT_SIDE = 2       # 좌측위
    RIGHT_SIDE = 3      # 우측위
    SUPINE = 4          # 앙와위 (등)
    PRONE = 5           # 복와위 (배)
    SUPINE_LEFT = 6     # 앙와위 + 왼쪽 다리 올림
    SUPINE_RIGHT = 7    # 앙와위 + 오른쪽 다리 올림


class BodyPart(Enum):
    """압력 측정 신체 부위"""
    OCCIPUT = "occiput"             # 후두부 (머리 뒤)
    SCAPULA = "scapula"             # 견갑골 (어깨뼈)
    RIGHT_ELBOW = "right_elbow"     # 오른쪽 팔꿈치
    LEFT_ELBOW = "left_elbow"       # 왼쪽 팔꿈치
    HIP = "hip"                     # 엉덩이
    RIGHT_HEEL = "right_heel"       # 오른쪽 발뒤꿈치
    LEFT_HEEL = "left_heel"         # 왼쪽 발뒤꿈치
