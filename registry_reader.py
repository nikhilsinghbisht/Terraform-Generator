import requests
from bs4 import BeautifulSoup


def fetch_registry_doc(resource):

    url = f"https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/{resource}"

    try:

        response = requests.get(url, timeout=15)

        if response.status_code != 200:
            return ""

        soup = BeautifulSoup(response.text, "html.parser")

        content = []

        for header in soup.find_all(["h2", "h3"]):

            title = header.get_text().strip()

            if title in ["Argument Reference", "Attributes Reference", "Import"]:

                content.append(f"\n### {title}\n")

                section = header.find_next_sibling()

                while section and section.name not in ["h2", "h3"]:

                    content.append(section.get_text())

                    section = section.find_next_sibling()

        return "\n".join(content)[:12000]

    except Exception:
        return ""