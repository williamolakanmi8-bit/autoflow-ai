from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # LLM
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    default_llm_provider: str = Field(default="openai", env="DEFAULT_LLM_PROVIDER")

    # Gmail
    gmail_credentials_path: str = Field(default="credentials/gmail_credentials.json")
    gmail_token_path: str = Field(default="credentials/gmail_token.json")
    gmail_sender_email: str = Field(default="", env="GMAIL_SENDER_EMAIL")

    # HubSpot
    hubspot_access_token: str = Field(default="", env="HUBSPOT_ACCESS_TOKEN")

    # Slack
    slack_bot_token: str = Field(default="", env="SLACK_BOT_TOKEN")
    slack_signing_secret: str = Field(default="", env="SLACK_SIGNING_SECRET")
    slack_approval_channel_id: str = Field(default="", env="SLACK_APPROVAL_CHANNEL_ID")

    # Sheets
    sheets_credentials_path: str = Field(default="credentials/sheets_credentials.json")
    outcome_sheet_id: str = Field(default="", env="OUTCOME_SHEET_ID")

    # Supabase
    supabase_url: str = Field(default="", env="SUPABASE_URL")
    supabase_key: str = Field(default="", env="SUPABASE_KEY")

    # App
    webhook_secret: str = Field(default="", env="WEBHOOK_SECRET")
    hitl_threshold_contacts: int = Field(default=50, env="HITL_THRESHOLD_CONTACTS")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
