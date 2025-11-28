import numpy as np
from joblib import load
from logging import getLogger
from sklearn.preprocessing import MinMaxScaler
from sklearn.multioutput import MultiOutputClassifier
from typing import Optional
import os

from domain.enums import PostureType
from domain.models import PostureDetectionResult


class PostureDetectionModel:
    """ML 모델을 사용한 자세 감지"""

    _scaler: Optional[MinMaxScaler] = None
    _predictor: Optional[MultiOutputClassifier] = None

    def __init__(self):
        self._logger = getLogger("PostureDetectionModel")

    def _load_models(self) -> bool:
        """모델 파일 로드 (싱글톤 패턴으로 한 번만 로드)"""
        if PostureDetectionModel._scaler and PostureDetectionModel._predictor:
            return True

        model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
        scaler_path = os.path.join(model_dir, "scaler.pkl")
        predictor_path = os.path.join(model_dir, "posture.pkl")

        if not os.path.exists(scaler_path) or not os.path.exists(predictor_path):
            self._logger.error(f"Model files not found: {model_dir}")
            return False

        PostureDetectionModel._scaler = load(scaler_path)
        PostureDetectionModel._predictor = load(predictor_path)

        self._logger.info("Posture detection models loaded successfully")
        return True

    def _convert(self, heatmap: np.ndarray) -> np.ndarray:
        """(16, 7)를 -> (1, 90)로 변경 (2행씩 묶어서 진행)"""
        head = heatmap[0:2, [0, 3, 6]].flatten().reshape(1, 6)  # 2x3으로 변경 -> 1x6으로 변경
        body = heatmap[2:14, :].flatten().reshape(1, 84)  # 12x7 -> 1x84로 변경
        return np.concatenate([head, body], axis=1)

    def detect(self, pressure_map: np.ndarray) -> PostureDetectionResult:
        """압력 맵으로부터 자세 감지"""
        if not self._load_models():
            self._logger.error("Models cannot be loaded")
            return PostureDetectionResult(posture_type=PostureType.UNKNOWN)

        raw = self._convert(pressure_map)
        scaled = PostureDetectionModel._scaler.transform(raw)
        prediction = PostureDetectionModel._predictor.predict(scaled)[0]

        posture = prediction[0]
        risky_part_flags = prediction[1:]
        upper_body, right_leg, left_leg, feet = (
            risky_part_flags[0],
            risky_part_flags[1],
            risky_part_flags[2],
            risky_part_flags[3],
        )

        result = PostureDetectionResult(posture_type=PostureType.UNKNOWN)

        match posture:
            case 0:  # 정자세
                result.posture_type = PostureType.SUPINE
                result.occiput = True
                result.scapula = True
                result.hip = True
                result.left_heel = True
                result.right_heel = True
                result.left_elbow = True
                result.right_elbow = True
                if left_leg:
                    result.right_heel = False
                    result.posture_type = PostureType.SUPINE_RIGHT
                if right_leg:
                    result.left_heel = False
                    result.posture_type = PostureType.SUPINE_LEFT
            case 1:  # 측면왼
                result.posture_type = PostureType.LEFT_SIDE
                result.left_elbow = True
                result.left_heel = True
            case 2:  # 측면오
                result.posture_type = PostureType.RIGHT_SIDE
                result.right_elbow = True
                result.right_heel = True
            case 3:  # 엎드림
                result.posture_type = PostureType.PRONE
            case 5:  # 앉음
                result.posture_type = PostureType.SITTING
                result.hip = True

        return result
