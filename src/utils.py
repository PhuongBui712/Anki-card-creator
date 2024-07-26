import os
import requests
import warnings
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from typing import Literal, Callable, Union
from dotenv import load_dotenv


load_dotenv()


REQUEST_HEADER=(
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:12.0) Gecko/20100101 Firefox/12.0"
    }
)


def incorrect_url_warning(message, category, filename, lineno, line=None):
    return f'{category.__name__}: {message}\n'
# Set the custom warning format
warnings.formatwarning = incorrect_url_warning



def check_url(input_url: str, response_url: str) -> bool:
    return input_url == response_url


def get_url(url: str,
            get_raw_data: bool = False,
            check_url: Callable[[str, str], bool] = check_url) -> Union[BeautifulSoup, str]:
    response = requests.get(url, headers=REQUEST_HEADER)
    if not response.ok:
        response.raise_for_status()

    if check_url is not None and check_url(url, response.url) == False:
        warnings.warn(f'Error happened when connecting to {url}', UserWarning)
        return None
    
    if not get_raw_data:
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


def get_media_path(audio_file_name: str, media_type: Literal['audio', 'image'] = 'audio'):
    if media_type == 'audio':
        dir_path = os.getenv('PRONOUNCE_PATH')
    else:
        dir_path = os.path.join(os.getenv('COLLECTION_MEDIA_PATH'), os.getenv('ILLUSTRATIVE_IMAGE_PATH'))

    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    return os.path.join(dir_path, audio_file_name)