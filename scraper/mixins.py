import re
import requests

from threading import Thread

from retrying import retry

from bs4 import BeautifulSoup


class BaseScraperMixin(object):
    @retry(wait_random_min=1000, wait_random_max=10000)
    def _get_soup(self, url):
        print("------------------------------------")
        print("sending-- ------requests")
        return BeautifulSoup(requests.get(url).content)

    def _get_redirected_url(self, url):
        response = requests.get(url)
        if response.history:
            return response.url
        else:
            return url


class BallbyBallThread(Thread):
    def __init__(self, event):
        Thread.__init__(self)
        self.stopped = event

    def run(self):
        while not self.stopped.wait(0.5):
            print("my thread")
            # call a function
