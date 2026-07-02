# Deployment on Google Cloud Run

These instructions walk through the process of deploying the Data Science agent to Google Cloud Run with Agent Engine for session and memory storage.

## 1 - Authenticate the Google Cloud CLI, and enable Google Cloud APIs.

Please follow the mandatory authentication and API enablement steps detailed in the [Authenticate the Google Cloud CLI](../README.md#authenticate-the-google-cloud-cli) section in the Setup guide.

## 2 - Create a Vertex AI Reasoning Engine for memory storage (optional)

If you want persistent memory across sessions, create a Reasoning Engine in Vertex AI. See the [Vertex AI documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/reasoning-engine) for details.

**Note:** The full resource path format is:
```
projects/<PROJECT_NUMBER>/locations/<REGION>/reasoningEngines/<ENGINE_ID>
```

## 3 - Create a service account for the agent

Create a dedicated service account with the minimum required permissions:

```bash
export PROJECT_ID="<YOUR_PROJECT_ID>"
export SERVICE_ACCOUNT_NAME="ds-adk-agent"

gcloud iam service-accounts create ${SERVICE_ACCOUNT_NAME} \
  --display-name="Data Science ADK Agent" \
  --project=${PROJECT_ID}

# Grant required roles
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.user"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/logging.logWriter"
```

## 4 - Deploy the agent to Cloud Run
To deploy the Data Science agent with the Web UI enabled, use the `Dockerfile_ui` file.

1. Build the container image:

    **Note:** The `cloudbuild_ui.yaml` is used to explicitly configure Cloud Build to use `Dockerfile_ui`, as the standard `gcloud builds submit` command defaults to the standard `Dockerfile`.

    ```bash
    gcloud builds submit --config cloudbuild_ui.yaml .
    ```

2. Deploy the container to Cloud Run:
    ```bash
    export MEMORY_SERVICE_URI="<YOUR_REASONING_ENGINE_RESOURCE_PATH>"  # Optional

    gcloud run deploy data-science-agent \
      --image gcr.io/${PROJECT_ID}/data-science-agent-ui \
      --port 8080 \
      --memory 2G \
      --cpu 2 \
      --project ${PROJECT_ID} \
      --allow-unauthenticated \
      --ingress=all \
      --service-account ds-adk-agent@${PROJECT_ID}.iam.gserviceaccount.com \
      --set-env-vars ARTIFACT_BUCKET_NAME=${ARTIFACT_BUCKET_NAME},SERVE_WEB_INTERFACE=True,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=us-central1,GOOGLE_GENAI_USE_VERTEXAI=TRUE,BQ_DATASET_ID=forecasting_sticker_sales,BQ_DATA_PROJECT_ID=${PROJECT_ID},BQ_COMPUTE_PROJECT_ID=${PROJECT_ID},ROOT_AGENT_MODEL=gemini-2.5-flash,ANALYTICS_AGENT_MODEL=gemini-2.5-flash,BIGQUERY_AGENT_MODEL=gemini-2.5-flash,BQML_AGENT_MODEL=gemini-2.5-flash,BASELINE_NL2SQL_MODEL=gemini-2.5-flash,CHASE_NL2SQL_MODEL=gemini-2.5-flash,MEMORY_SERVICE_URI=${MEMORY_SERVICE_URI},OTEL_TRACES_EXPORTER=none,DATASET_CONFIG_FILE=./dataset_configs/forecasting_sticker_sales_dataset_config.json \
      --region us-central1
    ```

    > [!CAUTION]
    > The `--allow-unauthenticated` flag makes your Cloud Run service publicly accessible without requiring Google Cloud IAM authentication. Do not use this for sensitive internal deployments.

    **Note:**
    - Sessions use in-memory storage by default (lost on restart)
    - For persistent sessions across restarts, the `MEMORY_SERVICE_URI` will be used for both memory and session storage
    - Ensure `MEMORY_SERVICE_URI` is set without quotes

## 5 - Test the Cloud Run Deployment

Open the Cloud Run Service URL outputted by the previous step.
You should see the ADK Web UI for the Data Science Agent.

**Example Deployment:**
After deploying to Cloud Run, access the UI at your service URL:
```
https://YOUR-SERVICE-NAME-PROJECT-ID.REGION.run.app/dev-ui/
```

## Clean up

You can clean up this agent sample by:
- Deleting the [Cloud Run Services](https://console.cloud.google.com/run).
- Deleting the GCS bucket (if created).
- Deleting the service account (if no longer needed).
