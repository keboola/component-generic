from typing import Dict, Any


class NoDataFoundException(Exception):
    pass


def get_data_from_path(json_path: str, data: Dict[str, Any], separator: str = '.', strict: bool = True) -> Any:
    """Mock function to fetch data using a dot-separated path notation. Replace with actual implementation."""
    keys = json_path.split(separator)
    for key in keys:
        if key not in data:
            if strict:
                raise NoDataFoundException(f"Key '{key}' not found in login data.")
            return None
        data = data[key]
    return data
