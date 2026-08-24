import yaml


def load_config(config_file: str) -> dict:
    """Load configuration from a YAML file."""
    try:
        with open(config_file, "r") as file:
            config = yaml.safe_load(file)
        return config
    except Exception as e:
        print(f"Error loading configuration from YAML: {e}")
        return {}
