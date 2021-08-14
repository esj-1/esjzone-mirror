"""
Copyright 2021-2022 sam01101 (https://github.com/sam01101).

此源代码的使用受 GNU AFFERO GENERAL PUBLIC LICENSE version 3 许可证的约束, 可以在以下链接找到该许可证.
Use of this source code is governed by the GNU AGPLv3 license that can be found through the following link.

https://github.com/sam01101/esjzone-mirror/blob/master/LICENSE
"""
import asyncio
from typing import List

import aiohttp
import re
from os.path import exists
from aiofiles import os
from aiofiles import open
from bs4 import BeautifulSoup

from utils import topic_regex, endpoint, thread_id_regex, script_val_regex, data_url_regex, post_id_regex, escape_symbol

loop = asyncio.new_event_loop()

pool = aiohttp.TCPConnector(loop=loop, ttl_dns_cache=60, force_close=True)


class Post:
    def __init__(self, name: str, create_date="", last_reply="", link=""):
        self.name = name
        self.create_date = create_date
        self.last_reply = last_reply
        self.link = link
        self.content = ""

    async def get_content(self):
        if not self.link.startswith(endpoint):
            return False
        async with aiohttp.ClientSession(connector=pool, connector_owner=False) as s:
            async with s.get(self.link) as resp:
                if resp.ok:
                    soup = BeautifulSoup(await resp.text(), "html.parser")
                    if post_content := soup.find("div", attrs={"class": "forum-content"}):
                        self.content = post_content.text
                        return True
        return False


class Thread:
    def __init__(self, name: str, topic_id: int, thread_id=0, last_update=""):
        self.name = name
        self.topic_id = topic_id
        self.id = thread_id
        self.last_update = last_update

    async def get_index(self):
        async with aiohttp.ClientSession(connector=pool, connector_owner=False) as s:
            async with s.get(endpoint + f"forum/{self.topic_id}/{self.id}/") as resp:
                if resp.ok:
                    soup = BeautifulSoup(await resp.text(), "html.parser")
                    script_content = soup.find("script", text=re.compile(script_val_regex))
                    if result := re.search(script_val_regex, script_content.string):
                        member_id, token = result.groups()
                    book_id = re.search(data_url_regex, soup.find("table", id="dataTable").get("data-url")).group(1)
            async with s.get(endpoint + f"forum/{self.topic_id}/{self.id}/forum_list_data.php", params={
                "token": token,
                "bid": book_id,
                "sort": "cdate",
                "order": "asc",
                "offset": "0",
                "limit": "18446744073709551615",  # SQL Max Limit
            }, cookies={"e_mem_id": member_id}) as resp:
                if resp.ok:
                    rows = []
                    for col in (await resp.json())['rows']:
                        a_elem = BeautifulSoup(col['subject'], "html.parser").a
                        post = Post(a_elem.text)
                        post_link = a_elem.get("href", "")
                        post.link = (endpoint + post_link[1:] if re.match(post_id_regex, a_elem.get("href", ""))
                                     else post_link)
                        post.last_reply = col['last_reply']
                        post.create_date = BeautifulSoup(col['cdate'], "html.parser").div.text
                        rows.append(post)
                return rows


class Board:
    class Topic:
        def __init__(self, name: str, topic_id=0, desc=""):
            self.name = name
            self.desc = desc
            self.id = topic_id
            self.thread = []

        async def get_threads(self):
            async with aiohttp.ClientSession(connector=pool, connector_owner=False) as s:
                async with s.get(endpoint + f"forum/{self.id}/") as resp:
                    if resp.ok:
                        soup = BeautifulSoup(await resp.text(), "html.parser")
                        detail = soup.find("table", attrs={"class": "table forum-board-detail"}).find("tbody")
                        threads = []
                        for thread in detail.find_all("tr"):
                            if a_elem := thread.find("a"):
                                thread_obj = Thread(a_elem.text, self.id)
                                if thread_id := re.search(thread_id_regex, a_elem.get("href", "")).group(1):
                                    thread_obj.id = int(thread_id)
                                last_update_soup = (detail.find_all("div", attrs={"class": "forum-desc"}))[1]
                                thread_obj.last_update = last_update_soup.text
                                threads.append(thread_obj)
                        return threads

    def __init__(self, name: str):
        self.name = name
        self.topics: List[Board.Topic] = []

    def add_topic(self, topic: "Board.Topic"):
        self.topics.append(topic)


async def get_boards():
    async with aiohttp.ClientSession(connector=pool, connector_owner=False) as s:
        async with s.get(endpoint + "forum/") as resp:
            if resp.ok:
                boards = []
                soup = BeautifulSoup(await resp.text(), "html.parser")
                for board in soup.find_all("table", attrs={"class": "table forum-board"}):
                    board_obj = Board(board.thead.th.text)
                    boards.append(board_obj)
                    for topic in board.tbody.find_all("tr"):
                        a_elem = topic.find("a")
                        topic_obj = Board.Topic(a_elem.text)
                        if topic_id := re.search(topic_regex, a_elem.get("href", "")).group(1):
                            topic_obj.id = int(topic_id)
                        if topic_desc := topic.find("div", attrs={"class": "forum-desc"}):
                            topic_obj.desc = topic_desc.text
                        board_obj.add_topic(topic_obj)
                return boards


async def save_topics(name: str, topic: Board.Topic):
    folder_sub_name = topic.name
    if topic.desc:
        folder_sub_name += " - " + topic.desc
    folder_sub_name = f"{name}/{escape_symbol(folder_sub_name)}"
    try:
        await os.mkdir(folder_sub_name)
    except FileExistsError:
        pass
    print(f"- Mkdir {folder_sub_name}")
    if threads := await topic.get_threads():
        await asyncio.gather(*(save_posts(folder_sub_name, thread) for thread in threads))


async def save_posts(name: str, thread: Thread):
    folder_sub_name = f"{name}/{escape_symbol(thread.name)}"
    try:
        await os.mkdir(folder_sub_name)
    except FileExistsError:
        pass
    print(f"- Mkdir {folder_sub_name}")
    if thread.last_update.strip():
        print("- Writing last update")
        async with open(f"{folder_sub_name}/LAST_UPDATE.txt", "w") as file:
            await file.write(thread.last_update)
    for pos, index in enumerate(await thread.get_index()):
        txt_name = escape_symbol(f"{pos}  {index.name}")
        async with open(f"{folder_sub_name}/{txt_name}.txt", "w") as file:
            print(f"- Write file {folder_sub_name}/{txt_name}.txt")
            if await index.get_content():
                await file.write("\n".join((
                    "========== INFO ==========",
                    f"Create Date: {index.create_date}",
                    f"Last Reply: {index.last_reply}",
                    "==========================",
                    ""
                )))
                if index.content:
                    await file.write(index.content)
                else:
                    await file.write("Content Empty!")
            else:
                await file.write(index.link)


async def main():
    if boards := await get_boards():
        for board in boards:
            board_name = "./data/" + escape_symbol(board.name)
            try:
                await os.mkdir(board_name)
            except FileExistsError:
                pass
            print(f"- Mkdir {board_name}")
            for topic in board.topics:
                await save_topics(board_name, topic)


if __name__ == '__main__':
    loop.run_until_complete(main())
