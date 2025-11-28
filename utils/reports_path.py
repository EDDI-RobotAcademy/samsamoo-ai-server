# utils/reports_path.py
import os
from pathlib import Path

def _project_root() -> Path:
    """
    저장소 루트를 탐색:
    - generated_reports / pyproject.toml / .git 중 하나가 있으면 거기까지 올라감
    """
    p = Path(__file__).resolve()
    for _ in range(8):
        cand = p.parent
        if (cand / "generated_reports").exists() or \
           (cand / "pyproject.toml").exists() or \
           (cand / ".git").exists():
            return cand
        p = cand
    return Path.cwd()

def get_reports_base_dir() -> Path:
    """
    generated_reports 디렉토리 절대경로 반환.
    - REPORTS_BASE_DIR 환경변수가 있으면 그걸 사용
    - 없으면 프로젝트 루트 기준 generated_reports 사용
    """
    env = os.getenv("REPORTS_BASE_DIR")
    base = Path(env).expanduser().resolve() if env else (_project_root() / "generated_reports")
    base.mkdir(parents=True, exist_ok=True)
    return base
