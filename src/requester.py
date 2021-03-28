from os import remove
from re import sub
from os.path import isfile

from requests import get as request


def get_cache_name(url: str) -> str:
    return "cache/" + sub(r"[^a-zA-Z0-9_ ]+", "", url.replace("/", "_")) + ".json"


def get_content(url: str) -> str:
    file_name: str = get_cache_name(url)

    # Cache.
    if isfile(file_name):
        file = open(file_name, "r")
        content = file.read()
        file.close()
    else:
        # Request.
        content = request(url).content.decode("utf-8")

    return content


def cache(url: str, content, overwrite: bool = False):
    file_name: str = get_cache_name(url)
    if not overwrite and isfile(file_name):
        return
    file = open(file_name, "w")
    file.write(content)
    file.close()


def remove_cache(url: str):
    file_name: str = get_cache_name(url)
    if isfile(file_name):
        remove(file_name)
