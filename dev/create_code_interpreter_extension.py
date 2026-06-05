import os
import vertexai
from dotenv import load_dotenv
from vertexai.preview.extensions import Extension

load_dotenv()

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

if not PROJECT:
    raise ValueError("GOOGLE_CLOUD_PROJECT environment variable must be set.")

vertexai.init(project=PROJECT, location=LOCATION)


def create_code_interpreter_extension():
    print(f"Creating Code Interpreter Extension in {PROJECT}/{LOCATION}...")

    try:
        extension = Extension.from_hub("code_interpreter")

        print("\n✅ Successfully created Code Interpreter Extension!")
        print(f"Resource Name: {extension.resource_name}")
        print("-" * 50)
        print("Please update the following line in your .env file:")
        print(f"CODE_INTERPRETER_EXTENSION_NAME='{extension.resource_name}'")
        print("-" * 50)

    except Exception as e:
        print(f"❌ Failed to create Code Interpreter Extension: {e}")


if __name__ == "__main__":
    create_code_interpreter_extension()
