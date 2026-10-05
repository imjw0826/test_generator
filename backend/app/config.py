from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Study Question Generator"
    debug: bool = False
    database_url: str = "sqlite:///./data/study_questions.db"
    upload_dir: str = "data/uploads"
    figure_dir: str = "data/figures"
    generated_exam_dir: str = "data/generated_exams"
    figure_url_prefix: str = "/api/assets/figures"
    max_upload_size_mb: int = 50
    cors_origins: str = "http://localhost:3000"
    anthropic_api_key: str = ""
    deepseek_api_key: str = ""
    deepseek_anthropic_base_url: str = "https://api.deepseek.com/anthropic"
    llm_model: str = "claude-sonnet-5-5"
    llm_translation_model: str = "claude-sonnet-5-5"
    llm_outline_model: str = "claude-sonnet-5-5"
    llm_solution_model: str = "claude-opus-5-5"
    # Claude effort levels: low | medium | high | xhigh | max
    llm_extraction_effort: str = "medium"
    llm_translation_effort: str = "low"
    llm_outline_effort: str = "low"
    llm_solution_effort: str = "high"
    llm_max_retries: int = 3
    llm_include_page_image: bool = True
    llm_page_image_zoom: float = 2.0
    # pdf-inspector layout analysis (headings, scanned-page flags) during processing.
    pdf_structure_analysis: bool = True
    pdf_structure_timeout_seconds: float = 30.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def figure_path(self) -> Path:
        path = Path(self.figure_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def generated_exam_path(self) -> Path:
        path = Path(self.generated_exam_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
