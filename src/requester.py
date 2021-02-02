from re import sub
from pickle import dump, load
from os.path import isfile

from requests import get as request


def get_content(url: str, can_cache: bool = True) -> str:
    page: "requests.models.Response" = None
    file_name: str = "cache/" + sub(
        r"[^a-zA-Z0-9_ ]+", "", url.replace("/", "_")
    ) + ".obj"

    # Cache.
    cached: bool = can_cache and isfile(file_name)
    if cached:
        file = open(file_name, "rb")
        page = load(file)
        file.close()
    else:
        # Request.
        page = request(url)
        if can_cache:
            file = open(file_name, "wb")
            dump(page, file)
            file.close()

    return page.content.decode("utf-8")
