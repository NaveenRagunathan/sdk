import os
import re
import uuid as uuid
import sys
import shutil

import aiohttp
import aiofiles
import urllib.parse
from typing import Union, Optional
from loguru import logger
from urllib.request import urlopen
from urllib.error import URLError

from vikit.common.decorators import log_function_params


def get_canonical_name(file_path: str):
    """
    Get the canonical name of a file, without the extension
    """
    return os.path.splitext(os.path.basename(file_path))[0]


def get_max_filename_length(path="."):
    """
    get the max file name for the current OS

    params:
        path: the file path

    return: file name max length.
    """
    try:
        return os.pathconf(path, "PC_NAME_MAX")
    except (AttributeError, ValueError, os.error):
        # PC_NAME_MAX may not be available or may fail for certain paths on some OSes
        # Returns a common default value (255) in this case
        return 255


def create_non_colliding_file_name(canonical_name: str = None, extension: str = "xyz"):
    """
    Transforms the filename to prevent collisions zith other files,
    by adding a UUID as suffix

    params:
        canonical_name: a name used as the target file name prefix
        extension: the extension of the file

    return: the non-colliding name
    """
    target_name = canonical_name + "_UID_" + str(uuid.uuid4()) + "." + extension

    val_target_name, error = get_path_type(target_name)
    if error:
        logger.warning(
            f"Error creating non-colliding file name: {val_target_name['path']}"
        )

    logger.debug(f"val_target_name['path']: {val_target_name['path']}")
    return val_target_name["path"]


def get_safe_filename(filename):
    return re.sub(r"(?u)[^-\w.]", "", filename.strip().replace(" ", "_"))


def get_max_remote_path_length():
    """
    Get the maximum length of a remote path
    """
    return 2048


def is_valid_path(path: Optional[Union[str, os.PathLike]]) -> bool:
    """
    Check if the path is valid

    Args:
        path (str, os.PathLike): The path to validate

    Returns:
        bool: True if the path is valid, False otherwise
    """
    path = get_path_type(path)
    if path["type"] == "error" or path["type"] == "none":
        return False
    return True


def get_path_type(path: Optional[Union[str, os.PathLike]]) -> dict:
    """
    Validate the path and return its type

    Args:
        path (str, os.PathLike, ): The path to validate

    Returns:
        dict: The path type and the path itself
        Path type can be local, http, https, s3, gs, None, undefined, error,
        error : message if the path is invalid, None if no error
    """
    logger.debug(f"Checking path: {path}")
    error = None
    result = ({"type": "undefined", "path": "undefined"}, "undefined path")

    if path is None:
        return {"type": "none", "path": path}, "The path is None"

    if len(path) > get_max_filename_length():
        return {
            "type": "error",
            "path": "",
        }, "The file name is too long for local filesystem storage"

    if os.path.exists(path) or is_valid_filename(filename=os.path.basename(path)):
        if path.startswith("file://"):
            logger.debug(f"Path is a local url format: {path}")
            return {"type": "local_url_format", "path": path}, None
        else:
            logger.debug(f"Path is a PathLike object: {path}")
            return {"type": "local", "path": path}, None
    else:
        # Check if the path is a URL
        parsed_uri = urllib.parse.urlparse(str(path))

        if parsed_uri.scheme in ["http", "https", "s3", "gs"]:
            return {"type": parsed_uri.scheme, "path": path}, None

    # by default, consider it as a local path
    return result, error


def is_valid_filename(filename: str) -> bool:
    """
    Check if the provided string is a valid filename for the local file system.

    Args:
        filename (str): The filename to check.

    Returns:
        bool: True if valid, False otherwise.
    """
    logger.debug(f"Checking filename: {filename}")
    # Check for invalid characters
    if sys.platform.startswith("win"):
        # Windows filename restrictions
        invalid_chars = r'[<>:"/\\|?*\x00-\x1F]'
        reserved_names = ["CON", "PRN", "AUX", "NUL"] + [
            f"{name}{i}" for name in ["COM", "LPT"] for i in range(1, 10)
        ]
        if any(filename.upper().startswith(reserved) for reserved in reserved_names):
            return False
    else:
        # Unix/Linux/MacOS filename restrictions
        invalid_chars = r"/"

    if re.search(invalid_chars, filename):
        return False

    # Check for leading or trailing spaces or dots which can be problematic
    if filename.strip(" .") != filename:
        return False

    # Check the length of the filename
    if len(filename) > get_max_filename_length():
        return False

    return True


TIMEOUT = 5  # TODO: set to global config , seconds before stopping the request to check an URL exists


def web_url_exists(url):
    """
    Check if a URL exists on the web
    """
    try:
        urlopen(url, timeout=TIMEOUT)
        return True
    except URLError:
        return False
    except ValueError:
        return False


@log_function_params
def url_exists(url: str):
    """
    Check if a URL exists somewhere on the internet or locally. To be superseded by a more
    versatile and unified library in the future.

    Args:
        url (str): The URL to check

    Returns:
        bool: True if the URL exists, False otherwise
    """
    url_exists = False
    assert url, "url cannot be None"

    if os.path.exists(url):
        url_exists = True

    if web_url_exists(url):
        url_exists = True

    return url_exists


@log_function_params
async def download_file(url, local_path):
    """
    Download a file from a URL to a local file asynchronously

    Args:
        url (str): The URL to download the file from
        local_path (str): The filename to save the file to

    Returns:
        str: The filename of the downloaded file
    """
    if not url:
        raise ValueError("URL must be provided")

    path_desc, error = get_path_type(url)

    if not error:
        if path_desc["type"] == "http" or path_desc["type"] == "https":
            async with aiohttp.ClientSession() as session:
                logger.debug(f"Downloading file from {url} to {local_path}")
                async with session.get(url) as response:
                    if response.status == 200:
                        # Utilisez aiofiles pour écrire le contenu de manière asynchrone
                        async with aiofiles.open(url, "wb") as f:
                            while (
                                True
                            ):  # Lire le contenu par morceaux pour ne pas surcharger la mémoire
                                chunk = await response.content.read(1024)
                                if not chunk:
                                    break
                                await f.write(chunk)
                        return local_path
        elif path_desc["type"] == "local":
            logger.debug(f"Copying file from {url} to {local_path}")
            shutil.copyfile(url, local_path)
            return local_path
        elif path_desc["type"] == "local_url_format":
            url = url.replace("file://", "")
            logger.debug(f"Copying file from {url} to {local_path}")
            shutil.copyfile(url, local_path)
            return local_path
    else:
        raise ValueError(f"Unsupported remote path type: {url}")
