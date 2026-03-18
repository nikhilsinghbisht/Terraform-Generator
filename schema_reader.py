import requests


def fetch_resource_schema(resource_name):

    base_url = "https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/"

    url = base_url + resource_name

    try:
        response = requests.get(url, timeout=15)

        if response.status_code == 200:
            return response.text[:20000]

        return ""

    except Exception as e:
        print("Schema fetch error:", e)
        return ""