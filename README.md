# Home Assistant LM Studio Integration

Connect [Home Assistant](https://www.home-assistant.io/) to a local [LM Studio](https://lmstudio.ai/) server. View models, load and unload them, download from the catalog, and use LM Studio with **Assist** and **AI Task**.

## Requirements

- Home Assistant **2025.7** or newer (AI Task support)
- LM Studio with the local server enabled (default port `1234`; any port works)
- Network access from Home Assistant to the LM Studio host

## Installation

### HACS (recommended)

1. Open **HACS → Integrations → ⋮ → Custom repositories**
2. Add `https://github.com/Spoky03/homeassistant-lmstudio`
3. Category: **Integration**
4. Search for **LM Studio**, install, and restart Home Assistant
5. Go to **Settings → Devices & services → Add integration → LM Studio**

### Manual

1. Copy `custom_components/lmstudio` into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Add the integration via **Settings → Devices & services**

## Configuration

During setup you provide:

| Setting | Description |
|---------|-------------|
| **Host** | LM Studio server address (e.g. `127.0.0.1`) |
| **Port** | LM Studio server port (e.g. `2137`) |
| **API token** | Optional; required if authentication is enabled in LM Studio |

### Options

Open **Settings → Devices & services → LM Studio → Configure**:

| Option | Default | Description |
|--------|---------|-------------|
| Poll interval | 30s | How often model state is refreshed (5–600s) |
| Context length | 0 | Default load context length (`0` = model default) |
| Flash attention | Off | Enable flash attention when loading models |
| Conversation model | — | LLM model key for Assist / AI Task |
| Conversation prompt | — | Optional system prompt override |
| Home Assistant LLM APIs | — | Enable device control tools in conversations |
| Temperature | 0.7 | Chat temperature (0–2) |
| Max tokens | 0 | Chat max tokens (`0` = server default) |
| Max conversation history | 10 | Messages kept in chat context |

## Entities

### Hub device (`LM Studio (host:port)`)

| Entity | Type | Description |
|--------|------|-------------|
| Models | sensor | Total model count; attributes show loaded/available counts |
| Active downloads | sensor | Number of in-progress downloads |
| Conversation | conversation | Assist / voice conversation agent |
| AI Task | ai_task | Structured data generation via `ai_task.generate_data` |

### Per-model devices

Each model from LM Studio gets its own device:

| Entity | Type | Description |
|--------|------|-------------|
| Info | sensor | Model metadata (type, size, quantization, context length, etc.) |
| Loaded | binary_sensor | Whether the model is loaded in LM Studio |
| Load | switch | Load or unload the model |
| Context length | number | Per-model context length override (`0` = use integration default) |
| Flash attention | switch | Per-model flash attention override |

When a download starts, a temporary **Download progress** sensor is created for that job.

## Services

### `lmstudio.download_model`

Download a model from the LM Studio catalog.

```yaml
service: lmstudio.download_model
data:
  config_entry: <your lmstudio config entry>
  model: ibm/granite-4-micro
```

## Assist & AI Task

1. Load an LLM model in LM Studio
2. In integration **Options**, select it as **Conversation model**
3. Optionally enable **Home Assistant LLM APIs** for device control
4. **Assist:** Settings → Voice assistants → select the LM Studio conversation agent
5. **AI Task:** Settings → AI Task → set the LM Studio entity as preferred for data generation

## Development

A Docker-based test setup is included:

```bash
docker compose up -d
```

Home Assistant runs at http://127.0.0.1:8123 with this integration mounted from `custom_components/`.

## License

MIT — see [LICENSE](LICENSE).
