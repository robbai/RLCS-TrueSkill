from re import sub
from pickle import dump, load
from os.path import isfile

from requests import get as request


def get_content(url: str) -> str:
    page = None
    file_name: str = "cache/" + sub(
        r"[^a-zA-Z0-9_ ]+", "", url.replace("/", "_")
    ) + ".obj"

    # Cache.
    if isfile(file_name):
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

    return page.content.decode("utf-8")
