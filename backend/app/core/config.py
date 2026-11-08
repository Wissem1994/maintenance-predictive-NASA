from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("PREDICTMAINT_DATABASE_URL", "sqlite:///./data/predictmaint.db")
    raw_dir: Path = Path(os.getenv("PREDICTMAINT_RAW_DIR", "data/raw/nasa_ims"))
    artifact_dir: Path = Path(os.getenv("PREDICTMAINT_ARTIFACT_DIR", "artifacts"))
    tick_seconds: float = float(os.getenv("PREDICTMAINT_TICK_SECONDS", "2"))
    origins: str = os.getenv("PREDICTMAINT_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
