import os
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup


HEADER=(
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:12.0) Gecko/20100101 Firefox/12.0"
    }
)


def get_url(url: str, get_raw_data: bool = False):
    response = requests.get(url, headers=HEADER)
    if not response.ok:
        response.raise_for_status()
    
    if get_raw_data:
        return BeautifulSoup(response.content, 'html.parser')
    return response.content


def get_file_type_from_url(url: str):
    # Parse the URL to get the path
    parsed_url = urlparse(url)
    path = parsed_url.path

    # Get the file extension from the path
    _, ext = os.path.splitext(path)

    # Remove the leading dot from the extension
    file_type = ext[1:] if ext else None

    return file_type


def get_file_name_from_url(url: str):
    # Parse the URL to get the path
    parsed_url = urlparse(url)
    path = parsed_url.path

    # Get the file name from the path
    file_name = os.path.basename(path)

    return file_name