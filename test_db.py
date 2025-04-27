import requests
import os

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

def get_covid_data():
    url = "http://localhost:8000/ingest"
    try:
        response = requests.post(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        return data
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")  # HTTP error
    except Exception as err:
        print(f"An error occurred: {err}")  # Other errors
    return None


def post_covid_data():
    url = "http://localhost:8000/ingest"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "sources": [
            {
                "source_type": "rest",
                "url": "https://disease.sh/v3/covid-19/countries",
                "headers": {}
            }
        ],
        "transformation_rules": [
            {
                "field": "cases",
                "operation": "rename",
                "params": {
                    "new_name": "total_cases"
                }
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        return data
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")  # HTTP error
    except Exception as err:
        print(f"An error occurred: {err}")  # Other errors
    return None

if __name__ == "__main__":
    covid_data = post_covid_data()
    print(covid_data)
    # print(covid_data)
    # if covid_data:
    #     # Example: Print data for the first 5 countries
    #     for country in covid_data[:5]:
    #         print(f"Country: {country['country']}")
    #         print(f"  Total Cases: {country['cases']}")
    #         print(f"  Total Deaths: {country['deaths']}")
    #         print(f"  Total Recovered: {country['recovered']}")
    #         print("-" * 40)



