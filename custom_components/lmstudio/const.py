"""Constants for the LM Studio integration."""

DOMAIN = "lmstudio"

CONF_API_TOKEN = "api_token"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_CONTEXT_LENGTH = "context_length"
CONF_FLASH_ATTENTION = "flash_attention"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 2137

DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 600
DEFAULT_CONTEXT_LENGTH = 0
DEFAULT_FLASH_ATTENTION = False

CONF_CHAT_MODEL = "chat_model"
CONF_MAX_HISTORY = "max_history"
CONF_MAX_TOKENS = "max_tokens"
CONF_TEMPERATURE = "temperature"

DEFAULT_MAX_HISTORY = 10
DEFAULT_MAX_TOKENS = 0
DEFAULT_TEMPERATURE = 0.7
DEFAULT_CHAT_MODEL = ""
MAX_TOOL_ITERATIONS = 10

# Kept for backwards compatibility with imports.
UPDATE_INTERVAL_SECONDS = DEFAULT_SCAN_INTERVAL

ATTR_ARCHITECTURE = "architecture"
ATTR_DISPLAY_NAME = "display_name"
ATTR_FORMAT = "format"
ATTR_INSTANCE_IDS = "instance_ids"
ATTR_KEY = "key"
ATTR_LOADED = "loaded"
ATTR_MAX_CONTEXT_LENGTH = "max_context_length"
ATTR_MODEL_TYPE = "model_type"
ATTR_PARAMS = "params_string"
ATTR_PUBLISHER = "publisher"
ATTR_QUANTIZATION = "quantization"
ATTR_SIZE_BYTES = "size_bytes"

SERVICE_DOWNLOAD_MODEL = "download_model"

CONF_MODEL = "model"
CONF_CONFIG_ENTRY = "config_entry"

DOWNLOAD_UPDATE_INTERVAL_SECONDS = 5
DOWNLOAD_TERMINAL_STATUSES = frozenset(
    {"completed", "failed", "error", "cancelled", "canceled"}
)

ATTR_DOWNLOADED_BYTES = "downloaded_bytes"
ATTR_DOWNLOAD_ERROR = "error"
ATTR_DOWNLOAD_MODEL = "model"
ATTR_DOWNLOAD_PROGRESS = "progress"
ATTR_DOWNLOAD_STARTED_AT = "started_at"
ATTR_DOWNLOAD_COMPLETED_AT = "completed_at"
ATTR_JOB_ID = "job_id"
ATTR_TOTAL_SIZE_BYTES = "total_size_bytes"

ATTR_EFFECTIVE_CONTEXT_LENGTH = "effective_context_length"
ATTR_EFFECTIVE_FLASH_ATTENTION = "effective_flash_attention"
ATTR_OVERRIDE = "override"
ATTR_USES_DEFAULT = "uses_default"

UNIQUE_ID_CONTEXT_LENGTH_SUFFIX = "context_length"
UNIQUE_ID_FLASH_ATTENTION_SUFFIX = "flash_attention"
