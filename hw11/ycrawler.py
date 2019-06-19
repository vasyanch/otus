import asyncio
import aiohttp
import aiofiles
import logging
import os
import requests
from bs4 import BeautifulSoup
from collections import namedtuple
from optparse import OptionParser

News = namedtuple('news', 'title url url_comments')
Paths = namedtuple('paths', 'news comments')
File_for_download = namedtuple('file', 'url path')

URL = 'https://news.ycombinator.com/'
MAX_RETRIES = 3


class Cache(list):
    def __init__(self, maxsize=0, *args, **kwargs):
        super(Cache, self).__init__(*args, **kwargs)
        self.maxsize = maxsize

    def append(self, *args, **kwargs):
        if self.maxsize:
            if self.__len__() < self.maxsize:
                super(Cache, self).append(*args, **kwargs)
            else:
                self.pop(0)
                super(Cache, self).append(*args, **kwargs)
        else:
            super(Cache, self).append(*args, **kwargs)

    def in_cache(self, items):
        """
        :param items: collections of item
        :return: list of items not in self
        """
        ans = []
        for i in items:
            if i in self:
                continue
            else:
                ans.append(i)
        return ans


async def get_page(url, session):
    retry = 0
    while True:
        try:
            response = await session.get(url)
            text = await response.read()
            return text
        except aiohttp.InvalidURL:
            logging.error('ERROR! Error in func get_page, url: {}\nInvalidURL!'.format(url))
            return
        except aiohttp.ClientError:
            if retry < MAX_RETRIES:
                retry += 1
                continue
            else:
                logging.exception('ERROR! Error in func get_page, url: {}'.format(url))
                return


async def save_text(text, path_file):
    async with aiofiles.open(path_file, 'wb') as file:
        await file.write(text)


async def download_page(url, path_file, session):
    text = await get_page(url, session)
    if not text:
        return
    try:
        await save_text(text, path_file)
    except Exception:
        logging.exception('ERROR! Error in func save_text, url: {}'.format(url))
    else:
        logging.info('Download is completed, page {}'.format(url))


def get_list_news_link(url):
    news_list = []
    url_comment_start = 'item?id='
    try:
        response = requests.get(url)
    except requests.exceptions.RequestException:
        logging.exception('ERROR! Error in func get_list_news_link, url {}'.format(url))
        return
    soup = BeautifulSoup(response.text, 'html.parser')
    news_links = soup.find_all(class_='athing')
    for i in news_links:
        id_news = i.get('id')
        single_news = i.find(class_='storylink')
        news_list.append(News(single_news.contents[0],
                              single_news.get('href'),
                              '{0}{1}'.format(url_comment_start, id_news)))
    return news_list


def get_list_comments_link(url):
    try:
        response = requests.get(url)
    except requests.exceptions.RequestException:
        logging.exception('ERROR! Error in func get_list_comments_link, url'.format(url))
        return
    soup = BeautifulSoup(response.text, 'html.parser')
    comments = soup.find_all(class_='comment')
    ans = []
    for comment in comments:
        reply = comment.find(class_='reply')
        reply.extract()
        list_links = comment.find_all('a', href=True)
        list_clear_links = [link.get('href') for link in list_links]
        ans.extend(list_clear_links)
    return ans


def check_new_links(cache, list_news):
    ans = []
    for n in list_news:
        if n in cache:
            continue
        ans.append(n)
    return ans


def get_paths(root_dir, title):
    title = title.split('?')[0]
    title = title.replace('/', '_')
    news_path = os.path.join(root_dir, title)
    os.mkdir(news_path)
    comment_path = os.path.join(news_path, 'comments')
    os.mkdir(comment_path)
    return Paths(news_path, comment_path)


async def main(directory, interval):
    num_loop = 0
    cache = Cache(maxsize=150)
    while True:
        num_loop += 1
        logging.info('Loop {}'.format(num_loop))
        list_news = get_list_news_link(URL)
        list_news = cache.in_cache(list_news)
        if not list_news:
            await asyncio.sleep(interval)
            continue
        [cache.append(new_link) for new_link in list_news]
        raw_tasks = []
        for one_news in list_news:
            paths = get_paths(directory, one_news.title)
            raw_tasks.append(File_for_download(one_news.url, os.path.join(paths.news, one_news.title)))
            list_links_from_comments = get_list_comments_link(os.path.join(URL, one_news.url_comments))
            for link in list_links_from_comments:
                file_name = link[8:].replace('/', '_')
                file_name = file_name.split('?')[0]
                raw_tasks.append(File_for_download(link, os.path.join(paths.comments, file_name)))
        timeout = aiohttp.ClientTimeout(total=interval)
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=30), timeout=timeout) as session:
            tasks = [asyncio.create_task(download_page(file.url, file.path, session)) for file in raw_tasks]
            await asyncio.sleep(interval)
            await asyncio.wait(tasks)


try:
    logging.basicConfig(format='[%(asctime)s] %(levelname).1s %(message)s', level='INFO', filename=None)
    options = OptionParser()
    options.add_option('-d', '--dir', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'content'))
    options.add_option('-i', '--interval', default=60)
    (opt, arg) = options.parse_args()
    if not os.path.exists(opt.dir):
        os.makedirs(opt.dir)
    asyncio.run(main(opt.dir, opt.interval))
except KeyboardInterrupt:
    logging.error('Ycrawler is terminated! Downloaded pages in {}'.format(opt.dir))
