This folder contains the instructions and datasets used for generating a new synthetic dataset with Gemini.

## Datasets

The following datasets were provided by Konstantinos Karagiannis and are used as a basis for the synthetic data generation:

  * **Dataset 1:** [OI\_operational\_data\_sample\_20260203.csv](https://drive.google.com/file/d/1wU_N-eZRckSBzDwl2sjsK_D-trdw1-SL/view?usp=drive_link)
  * **Dataset 2 (Training Dataset):** [OI\_training\_data\_sample\_20260203.csv](https://drive.google.com/file/d/1d1H1CGq8rDj0SCeUbRdW8Af_w5sZTsIt/view?usp=drive_link)

## Synthetic Dataset Generation Instructions

The following steps are applied to **Dataset 2** to create the new synthetic dataset:

1.  Extract the schema: Execute the script `extract_schema.py`. This will analyze your dataset and output a file named `<dataset>_schema.txt` containing the unique values for each column.
1.  Edit and version the schema to meet your requirements. Our changes for this dataset are:
    - Drop the empty columns in the schema.
    - For security reasons, create new unique values for specific columns as advised by Kostas. The columns for which new unique values are created are:
        * **`brand__brand`**
        * **`brand__advertiser_name`**
        * **`campaign__campaign_name`**
        * **`campaign__media_buy_name`**
        * **`creative__name`**
        * *(Note: `campaign__media_buy_name` was added to the list as its data was similar to `campaign__campaign_name`.)*
    - Drop the column **`creative__gcs_path`** to reduce the dataset size.
1. Version the schema file properly, such as
`OI_operational_data_sample_20260203_schema_v1.txt`.
1. Generate new data: Once your schema is ready, use it as input to the `synthetic_generator.py` script. This will generate new synthetic data based on your edited schema version. The output file will be named automatically by the script: it replaces `schema` with `synthetic_dataset` and uses the `.csv` extension. For example:
    - `OI_training_data_sample_20260203_schema_v1.txt` → `OI_training_data_sample_20260203_synthetic_dataset_v1.csv`

## Agent-to-Agent (A2A) Development Scripts

These scripts demonstrate how to interact with the deployed Data Science Agent using the A2A API.

### `a2a_simple_chat.py`
This script establishes a connection to the deployed agent and sends a basic "Hello" message. It is useful for:
- Verifying connectivity to the Cloud Run instance.
- Confirming the agent is responsive.
- Inspecting the raw A2A message structure.

**Usage:**
```bash
uv run python3 dev/a2a_simple_chat.py
```

### `a2a_artifact_handling.py`
This script demonstrates more advanced A2A interactions, including session management and artifact retrieval. It:
- Starts a new session with the agent.
- Requests the generation of a report (e.g., "Generate a sample report").
- Processes the agent's response to identify and download generated artifacts (like PDF reports).
- Continues the conversation within the same session context.

**Usage:**
```bash
uv run python3 dev/a2a_artifact_handling.py
```

## System Administration Scripts

### `create_memory_bank.py`
This script creates and configures the Vertex AI memory bank required by the Data Science Agent. It sets up the custom `DATA_QUALITY_ISSUES` topic used by the agent to persist known anomalies, missing data events, and schema discrepancies across chat sessions.

Once the engine is generated, the script outputs the required `MEMORY_SERVICE_URI`, which you must paste into the `.env` file under the respective key block for the agent's memory tools to engage.

**Usage:**
```bash
uv run python3 dev/create_memory_bank.py
```
