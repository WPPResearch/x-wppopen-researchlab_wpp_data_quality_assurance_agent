# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

# Define the path to the .env file
env_file_path = Path(__file__).parent.parent / ".env"
print(env_file_path)

# Load environment variables from the specified .env file
load_dotenv(dotenv_path=env_file_path)


def load_csv_to_bigquery(data_project_id, dataset_name, table_name, csv_filepath):
    """Loads a CSV file into a BigQuery table.

    Args:
        data_project_id: GCP Project for BQ data.
        dataset_name: The name of the BigQuery dataset.
        table_name: The name of the BigQuery table.
        csv_filepath: The path to the CSV file.
    """

    client = bigquery.Client(project=data_project_id)

    dataset_ref = client.dataset(dataset_name)
    table_ref = dataset_ref.table(table_name)

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,  # Skip the header row
        autodetect=True,  # Automatically detect the schema
    )

    with open(csv_filepath, "rb") as source_file:
        job = client.load_table_from_file(source_file, table_ref, job_config=job_config)

    job.result()  # Wait for the job to complete

    print(f"Loaded {job.output_rows} rows into {dataset_name}.{table_name}")


def create_dataset_if_not_exists(compute_project_id, data_project_id, dataset_name):
    """Creates a BigQuery dataset if it does not already exist.

    Args:
        compute_project_id: GCP Project for BQ compute.
        data_project_id: GQP Project for BQ data.
        dataset_name: The name of the BigQuery dataset.
    """
    client = bigquery.Client(project=compute_project_id)
    dataset_full_name = f"{data_project_id}.{dataset_name}"

    try:
        client.get_dataset(dataset_full_name)  # Make an API request.
        print(f"Dataset {dataset_full_name} already exists")
    except Exception:
        dataset = bigquery.Dataset(dataset_full_name)
        dataset.location = "US"  # Set the location (e.g., "US", "EU")
        dataset = client.create_dataset(dataset, timeout=30)  # Make an API request.
        print(f"Created dataset {dataset_full_name}")


def sanitize_table_name(filename):
    """Sanitizes a filename into a BigQuery-compatible table name."""
    # Use the name after the '/' and remove .csv
    name = filename.replace(".csv", "")
    # BigQuery table names: letters, numbers, underscores only
    # Replacing - and . with _ to ensure it's a valid BQ name
    sanitized = name.replace("-", "_").replace(".", "_")
    return sanitized


def main():
    import argparse

    current_directory = os.getcwd()
    print(f"Current working directory: {current_directory}")

    # Load environment variables
    env_data_project_id = os.getenv("BQ_DATA_PROJECT_ID")
    env_compute_project_id = os.getenv("BQ_COMPUTE_PROJECT_ID")

    parser = argparse.ArgumentParser(description="Load a CSV file into BigQuery.")
    parser.add_argument("--file", required=True, help="Path to the CSV file to upload.")
    parser.add_argument(
        "--bq-data-project-id",
        default=env_data_project_id,
        help="GCP Project for BQ data.",
    )
    parser.add_argument(
        "--bq-compute-project-id",
        default=env_compute_project_id,
        help="GCP Project for BQ compute.",
    )
    parser.add_argument(
        "--dataset-name",
        default="synthetic_data",
        help="The name of the BigQuery dataset.",
    )

    args = parser.parse_args()

    data_project_id = args.bq_data_project_id
    compute_project_id = args.bq_compute_project_id
    dataset_name = args.dataset_name
    csv_filepath = args.file

    if not data_project_id:
        raise ValueError(
            "BQ_DATA_PROJECT_ID not set via argument or environment variable.",
        )
    if not compute_project_id:
        raise ValueError(
            "BQ_COMPUTE_PROJECT_ID not set via argument or environment variable.",
        )

    print("Creating dataset.")
    create_dataset_if_not_exists(compute_project_id, data_project_id, dataset_name)

    filename = os.path.basename(csv_filepath)
    table_name = sanitize_table_name(filename)

    print(f"\nProcessing {filename} -> Table: {table_name}")
    try:
        load_csv_to_bigquery(data_project_id, dataset_name, table_name, csv_filepath)
    except Exception as e:
        print(f"Failed to upload {filename}: {e}")


if __name__ == "__main__":
    main()
