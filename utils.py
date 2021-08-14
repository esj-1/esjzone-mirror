"""
Copyright 2021-2022 sam01101 (https://github.com/sam01101).

此源代码的使用受 GNU AFFERO GENERAL PUBLIC LICENSE version 3 许可证的约束, 可以在以下链接找到该许可证.
Use of this source code is governed by the GNU AGPLv3 license that can be found through the following link.

https://github.com/sam01101/esjzone-mirror/blob/master/LICENSE
"""

endpoint = "https://www.esjzone.cc/"
topic_regex = r"/forum/(\d+)/"
thread_id_regex = r"/forum/\d+/(\d+)/"
post_id_regex = r"/forum/\d+/\d+.html"
script_val_regex = r"var mem_id='(u\d+)',.+token='(.+)';"
data_url_regex = r"bid=(\d+)"
symbol_list = {
    "\\": "-",
    "/": "-",
    ":": "：",
    "*": "☆",
    "?": "？",
    "\"": "",
    "<": "《",
    ">": "》",
    "|": "-",
    ".": "。",
    ",": "，",
    ";": "；",
    "(": "（",
    ")": "）",
    "\t": " ",
    "\n": " ",
}


def contain(string: str, array):
    if isinstance(array, dict):
        return any(symbol in string for symbol in array.keys())
    elif isinstance(array, list) or isinstance(array, tuple):
        return any(symbol in string for symbol in array)
    return False


def escape_symbol(string: str):
    while contain(string, symbol_list):
        for char, replace_char in symbol_list.items():
            string = string.replace(char, replace_char)
    return string
