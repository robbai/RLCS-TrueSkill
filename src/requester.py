from os import remove
from re import sub
from pickle import load
from os.path import isfile

from requests import get as request


def get_content(url: str, can_cache: bool = True) -> str:
    content: str = None
    file_name: str = "cache/" + sub(r"[^a-zA-Z0-9_ ]+", "", url.replace("/", "_"))

    # Cache.
    if can_cache and isfile(file_name + ".obj"):
        file = open(file_name + ".obj", "rb")
        content = load(file).content.decode("utf-8")
        file.close()
        remove(file_name + ".obj")
        file = open(file_name + ".json", "w")
        file.write(content)
        file.close()
    elif can_cache and isfile(file_name + ".json"):
        file = open(file_name + ".json", "r")
        content = file.read()
        file.close()
    else:
        # Request.
        content = request(url).content.decode("utf-8")
        if can_cache:
            file = open(file_name + ".json", "w")
            file.write(content)
            file.close()

    return content
