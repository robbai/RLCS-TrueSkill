from os import remove
from re import sub
from os.path import isfile

from requests import get as request

ENABLE_CACHING: bool = True


def get_cache_name(url: str, params={}, headers={}) -> str:
    return (
        "cache/"
        + sub(
            r"[^a-zA-Z0-9_ ]+",
            "",
            url.replace("/", "_") + str({**params, **headers}).replace(" ", "_"),
        )
        + ".json"
    )


def get_content(url: str, params={}, headers={}) -> str:
    file_name: str = get_cache_name(url, params, headers)

    # Cache.
    if ENABLE_CACHING and isfile(file_name):
        file = open(file_name, "r")
        content = file.read()
        file.close()
    else:
        # Request.
        content = request(url, params=params, headers=headers).content.decode("utf-8")

    return content


def cache(url: str, content, params={}, headers={}, overwrite: bool = False):
    file_name: str = get_cache_name(url, params, headers)
    if not ENABLE_CACHING or (not overwrite and isfile(file_name)):
        return
    file = open(file_name, "w")
    file.write(content)
    file.close()


def remove_cache(url: str, params={}, headers={}):
    file_name: str = get_cache_name(url, params, headers)
    if ENABLE_CACHING and isfile(file_name):
        remove(file_name)
