import numpy as np
from scipy.interpolate import RectBivariateSpline


class HeatmapConverter:
    """Head와 Body 데이터를 합쳐서 Heatmap으로 변환"""

    def _resize_with_interpolation(
        self, origin: np.ndarray, shape: tuple[int, int]
    ) -> np.ndarray:
        """2D 배열을 보간법으로 리사이즈

        Args:
            origin: 원본 2D 배열
            shape: 목표 (rows, cols)

        Returns:
            리사이즈된 배열
        """
        if origin.ndim != 2:
            raise ValueError("origin must be a 2D numpy array")

        target_rows, target_cols = int(shape[0]), int(shape[1])
        current_rows, current_cols = origin.shape

        if target_rows <= 0 or target_cols <= 0:
            raise ValueError("target shape must be positive integers")

        # 리사이즈 불필요
        if current_rows == target_rows and current_cols == target_cols:
            return origin

        # 스플라인 차수 (cubic)
        order = 3

        # RectBivariateSpline은 각 축에 최소 2개 포인트 필요
        can_use_spline = current_rows >= 2 and current_cols >= 2

        if can_use_spline:
            kx = min(order, max(1, current_rows - 1))
            ky = min(order, max(1, current_cols - 1))

            # 좌표 그리드 (0~1 정규화)
            x_orig = np.linspace(0, 1, current_cols)
            y_orig = np.linspace(0, 1, current_rows)
            x_new = np.linspace(0, 1, target_cols)
            y_new = np.linspace(0, 1, target_rows)

            spline = RectBivariateSpline(y_orig, x_orig, origin, kx=kx, ky=ky)
            resized = spline(y_new, x_new)
            return np.asarray(resized, dtype=np.float32)

        # 폴백: 차원이 1인 경우
        result = origin

        # 열 리사이즈
        if current_cols != target_cols:
            if current_cols == 1:
                result = np.repeat(result, target_cols, axis=1)
            else:
                x_old = np.linspace(0, 1, result.shape[1])
                x_new = np.linspace(0, 1, target_cols)
                result = np.vstack([np.interp(x_new, x_old, row) for row in result])

        # 행 리사이즈
        if result.shape[0] != target_rows:
            if result.shape[0] == 1:
                result = np.repeat(result, target_rows, axis=0)
            else:
                y_old = np.linspace(0, 1, result.shape[0])
                y_new = np.linspace(0, 1, target_rows)
                result = np.vstack(
                    [np.interp(y_new, y_old, result[:, j]) for j in range(result.shape[1])]
                ).T

        return result.astype(np.float32)

    def convert(self, head: np.ndarray, body: np.ndarray) -> np.ndarray:
        """Head와 Body 데이터를 합쳐서 Heatmap으로 변환

        Args:
            head: (2, 3) 형태의 head 데이터
            body: (12, 7) 형태의 body 데이터

        Returns:
            (14, 7) 형태의 heatmap
        """
        if head.ndim != 2 or body.ndim != 2:
            raise ValueError("head and body must be 2D numpy arrays")

        head_rows, head_cols = head.shape
        body_rows, body_cols = body.shape

        target_cols = max(head_cols, body_cols)

        # 열 수가 다르면 보간으로 맞춤
        head_resized = (
            self._resize_with_interpolation(head, (head_rows, target_cols))
            if head_cols != target_cols
            else head
        )
        body_resized = (
            self._resize_with_interpolation(body, (body_rows, target_cols))
            if body_cols != target_cols
            else body
        )

        # 세로로 병합: (2, 7) + (12, 7) = (14, 7)
        merged = np.concatenate((head_resized, body_resized), axis=0)

        return merged.astype(np.float32)
