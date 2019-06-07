import asyncio
import aiohttp
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


def save_text(text, path_file):
    with open(path_file, 'wb') as file:
        file.write(text)


async def download_page(url, path_file, session):
    text = await get_page(url, session)
    if not text:
        return
    try:
        save_text(text, path_file)
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
    title = title.replace('/', '_')
    news_path = os.path.join(root_dir, title)
    os.mkdir(news_path)
    comment_path = os.path.join(news_path, 'comments')
    os.mkdir(comment_path)
    return Paths(news_path, comment_path)


async def main(directory, interval):
    num_loop = 1
    cache = set()
    logging.info('Loop {}'.format(num_loop))
    while True:
        list_news = get_list_news_link(URL)
        list_news = check_new_links(cache, list_news)
        if list_news:
            [cache.add(n) for n in list_news]
            raw_tasks = []
            for one_news in list_news:
                paths = get_paths(directory, one_news.title)
                raw_tasks.append(File_for_download(one_news.url, os.path.join(paths.news, one_news.title)))
                list_links_from_comments = get_list_comments_link(os.path.join(URL, one_news.url_comments))
                for link in list_links_from_comments:
                    file_name = link[8:].replace('/', '_')
                    raw_tasks.append(File_for_download(link, os.path.join(paths.comments, file_name)))
            async with aiohttp.ClientSession() as session:
                tasks = [asyncio.create_task(download_page(file.url, file.path, session)) for file in raw_tasks]
                await asyncio.wait(tasks)

        num_loop += 1
        await asyncio.sleep(interval)


try:
    logging.basicConfig(format='[%(asctime)s] %(levelname).1s %(message)s', level='INFO', filename=None)
    options = OptionParser()
    options.add_option('-d', '--dir', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'content'))
    options.add_option('-i', '--interval', default=20)
    (opt, args) = options.parse_args()
    if not os.path.exists(opt.dir):
        os.makedirs(opt.dir)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(opt.dir, opt.interval))
    loop.close()
except KeyboardInterrupt:
    logging.error('Ycrawler is terminated! Downloaded pages in {}'.format(opt.dir))
