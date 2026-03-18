import json
import subprocess


# --------------------------------------------------
# Load Terraform Provider Schema
# --------------------------------------------------

def load_provider_schema():

    try:

        result = subprocess.run(
            ["terraform", "providers", "schema", "-json"],
            capture_output=True,
            text=True
        )

        data = json.loads(result.stdout)

        return data

    except Exception:
        return None


# --------------------------------------------------
# Extract Resource Schema
# --------------------------------------------------

def get_resource_schema(resource):

    schema = load_provider_schema()

    if not schema:
        return None

    try:

        provider = schema["provider_schemas"]["registry.terraform.io/hashicorp/azurerm"]

        resource_schema = provider["resource_schemas"][resource]

        attributes = resource_schema["block"]["attributes"]

        blocks = resource_schema["block"].get("block_types", {})

        required = []
        optional = []
        nested_blocks = []

        for attr, info in attributes.items():

            if info.get("required"):
                required.append(attr)
            else:
                optional.append(attr)

        for block in blocks.keys():
            nested_blocks.append(block)

        return {
            "required": required,
            "optional": optional,
            "blocks": nested_blocks
        }

    except KeyError:
        return None


# --------------------------------------------------
# Helper Functions
# --------------------------------------------------

def get_required_attributes(schema):

    if not schema:
        return []

    return schema.get("required", [])


def detect_dependency_attributes(schema):

    if not schema:
        return []

    dependency_keywords = ["id", "ids", "subnet", "network", "resource_group"]

    deps = []

    for attr in schema.get("optional", []):

        for word in dependency_keywords:

            if word in attr:
                deps.append(attr)

    return deps


def get_nested_blocks(schema):

    if not schema:
        return []

    return schema.get("blocks", [])