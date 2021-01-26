from re import sub
from pickle import dump, load
from typing import Tuple, Union
from os.path import isfile

from requests import get as request


def get_content(url: str, return_cached: bool = False) -> Union[str, Tuple[str, bool]]:
    page = None
    file_name: str = "cache/" + sub(
        r"[^a-zA-Z0-9_ ]+", "", url.replace("/", "_")
    ) + ".obj"

    # Cache.
    cached: bool = isfile(file_name)
    if cached:
        # print("Retrieving '" + url + "' from cache")
        file = open(file_name, "rb")
        page = load(file)
        file.close()
    else:
        # Request.
        # print("Requesting '" + url + "' and caching")
        page = request(url)  # timeout=(1, None)
        file = open(file_name, "wb")
        dump(page, file)
        file.close()

    if return_cached:
        return page.content.decode("utf-8"), cached
    return page.content.decode("utf-8")
