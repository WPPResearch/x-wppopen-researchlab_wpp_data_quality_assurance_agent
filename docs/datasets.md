# Sample Datasets

The Data Science agent includes two different sample datasets that showcase
different aspects of its capabilities.

## Dataset Configuration
To configure the Data Science Agent to use the correct dataset, you
will need to give it the name of a dataset configuration file in
the environment variable `DATASET_CONFIG_FILE`. Two sample configuration
files are provided: `dataset_configs/forecasting_sticker_sales_dataset_config.json`
and `dataset_configs/flights_dataset_config.json`, corresponding to the two datasets
described below. In your `.env. file, set the environment variable
as either
```bash
DATASET_CONFIG_FILE='./dataset_configs/forecasting_sticker_sales_dataset_config.json'
```
or
```bash
DATASET_CONFIG_FILE='./dataset_configs/flights_dataset_config.json'
```
### Dataset Configuration File Format
The two provided configuration files give examples of how to specify
a dataset configuration. The file is a standard JSON format, with
two main sections: `datasets` and `cross_dataset_relations`.

Each entry in `datasets` must contain the following fields: `type`,
`name`, and `description`. The description field is passed to the
root data science agent to help it decide how to use that dataset,
so ensure the description is written to be useful to the agent.

The `cross_dataset_relations` element contains an array,
`foreign_keys`, with entries for each foreign key relation between the
datasets the agent has access to. A `foreign_key` entry has two
fields, `child` and `parent`, each with the same fields:
* `type`: The type of the dataset (must match the type in the
    datasets field)
* `dataset`: The name of the dataset (must be one of the datasets
    configured in the datasets field)
* `table`: The table in the dataset where the key field is found
* `column`: The column in the dataset containing the key entries.

## Forecasting Sticker Sales Dataset

***NOTE:** This dataset uses BigQuery only. Make sure to follow the steps in the
[BigQuery Setup](../README.md#bigquery-setup) section to setup and configure the
agent to access BigQuery.*

You first need to download the dataset from [GitHub](https://github.com/google/adk-samples/tree/main/python/agents/data-science/data_science/utils/data/).

You can upload any dataset you want to BigQuery using the `create_bq_table` script by providing the path to your CSV file (both relative and absolute paths are supported) and the target dataset name. To load the sticker sales dataset (or any other dataset of your choice), make sure you are still in the working directory (`agents/data-science`) and run the following commands:

```bash
python3 data_science/utils/create_bq_table.py --file /absolute/or/relative/path/to/train.csv --dataset-name forecasting_sticker_sales
python3 data_science/utils/create_bq_table.py --file /absolute/or/relative/path/to/test.csv --dataset-name forecasting_sticker_sales
```

Set the following environment variable in your `.env` file to use this dataset:
```
BQ_DATASET_ID='forecasting_sticker_sales'`
```
Dataset source: _Walter Reade and Elizabeth Park. Forecasting Sticker Sales.
https://kaggle.com/competitions/playground-series-s5e1, 2025. Kaggle._

## Cymbal Airlines Flights Dataset

***NOTE:** This dataset uses BigQuery. Follow the steps in the [BigQuery Setup](../README.md#bigquery-setup)
section to setup the database and configure the agent for database access.*

You can find the flights dataset [here on GitHub](https://github.com/google/adk-samples/tree/main/python/agents/data-science/flights_dataset).

1. Configure the environment variables as directed in the BigQuery Setup section below.
Also export the BigQuery dataset id for this sample dataset:

    ```bash
    export BQ_DATASET_ID=flights_dataset
    ```

1. Run this command to create a new BigQuery dataset:
    ```bash
    bq mk --location $GOOGLE_CLOUD_LOCATION --dataset $BQ_DATA_PROJECT_ID:$BQ_DATASET_ID
    ```
1. Run these commands from the `data-science/flights_dataset` directory to load the
data into BigQuery:

    ```bash
    bq --project_id=$BQ_DATA_PROJECT_ID --location=$GOOGLE_CLOUD_LOCATION \
        load --source_format=CSV --autodetect --skip_leading_rows=1 --replace \
        $BQ_DATASET_ID.flight_history flight_history_table.csv
    bq --project_id=$BQ_DATA_PROJECT_ID --location=$GOOGLE_CLOUD_LOCATION \
        load --source_format=CSV --autodetect --skip_leading_rows=1 \
        --allow_quoted_newlines --replace \
        $BQ_DATASET_ID.cymbalair_policies cymbalair_policies_table.csv
    bq --project_id=$BQ_DATA_PROJECT_ID --location=$GOOGLE_CLOUD_LOCATION \
        load --source_format=CSV --autodetect --skip_leading_rows=1 --replace \
        $BQ_DATASET_ID.ticket_sales_history ticket_sales_history_table.csv
    ```
