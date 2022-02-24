import re

from django.db import IntegrityError

from scraper.mixins import BaseScraperMixin

from accounts.models import UserProfile
from rest_api.models import Pitch, VISIBLE_TO_CHOICES


class CricBuzzScraper(BaseScraperMixin):
    INTERNATIONAL = "international"
    DOMESTIC = "domestic"
    T20LEAGUE = "league"
    WOMEN = "women"
    ROOT_URL = "https://www.cricbuzz.com"

    def get_upcoming_matches(self, cric_type):
        url = f"https://www.cricbuzz.com/cricket-schedule/upcoming-series/{cric_type}"
        soup = self._get_soup(url)
        match, stadium, date, time = "", "", "", ""
        upcoming_matches = {}
        if cric_type == self.INTERNATIONAL:
            elem_list = soup.find("div", {"id": "international-list"})
        elif cric_type == self.DOMESTIC:
            elem_list = soup.find("div", {"id": "domestic-list"})
        elif cric_type == self.T20LEAGUE:
            elem_list = soup.find("div", {"id": "league-list"})
        elif cric_type == self.WOMEN:
            elem_list = soup.find("div", {"id": "women-list"})
        matches_tags = elem_list.findAll(
            "div", {"class": "cb-col-100 cb-col"}, recursive=False
        )
        for match_tag in matches_tags:
            matches = match_tag.findAll("div", {"class": "cb-col-100 cb-col"})
            date = match_tag.find(class_="cb-lv-grn-strip text-bold").get_text()
            upcoming_matches[date] = []
            for match_elem in matches:
                match = (
                    match_elem.find(class_="cb-col-67 cb-col")
                    .find(
                        class_="cb-ovr-flo cb-col-60 cb-col cb-mtchs-dy-vnu cb-adjst-lst"
                    )
                    .find("a")
                    .get_text()
                    .split(", ")[0]
                )
                time = match_elem.find(class_="schedule-date").get("timestamp")
                stadium = (
                    match_elem.find(class_="cb-font-12 text-gray cb-ovr-flo")
                    .get_text()
                    .strip()
                )
                upcoming_matches[date].append(
                    {"match": match, "stadium": stadium, "date": date, "time": time,}
                )

        return upcoming_matches

    def get_ball_by_ball_score(self, live_match_url):
        return {}

    def get_playerstats_urls(self):
        return

    def populate_playerstats(self):
        return

    def get_players(self, cric_type):
        players = {}
        players_url = f"https://www.cricbuzz.com/cricket-team/{cric_type}"
        soup = self._get_soup(players_url)
        team_links_space = soup.find(class_="cb-col cb-col-67 cb-nws-lft-col")

        team_links = team_links_space.findAll(
            "a", class_="cb-teams-flag-img", href=re.compile("cricket-team")
        )
        for team_link in team_links:
            team_soup = self._get_soup(
                self.ROOT_URL + team_link.get("href") + "/players"
            )

            players[team_link.get("title")] = [
                p.get_text().strip()
                for p in team_soup.findAll(class_="cb-col cb-col-73")
            ]
            print(players)
        return players

    def get_cricket_news_articles(self):
        """
            fill pitch table with articles
            this is for simulation purpose
        """
        from random import choice

        for cric_article_id in range(103433, 120490):
            page_no = choice(range(1, 10))
            cricket_news_url = f"https://www.cricbuzz.com/cricket-news/api-paginate/news-list/all/{cric_article_id}/{page_no}"
            # https://www.cricbuzz.com/cricket-news/api-paginate/news-list/all/120470/3

            webcontent = self._get_soup(cricket_news_url)
            get_articles = webcontent.findAll(
                class_="cb-col cb-col-100 cb-lst-itm cb-pos-rel cb-lst-itm-lg"
            )
            user_profiles = list(UserProfile.objects.filter()[20000:50000])
            pitches = []
            for article in get_articles:
                try:
                    image = (
                        article.find(
                            "meta", {"content": re.compile("img"), "itemprop": "url"}
                        )
                        .get("content")
                        .replace("https:", "")
                    )
                    message = article.find("a", href=True).get("title")
                    url_link = self.ROOT_URL + article.find("a", href=True).get("href")
                    pitches.append(
                        Pitch(
                            **{
                                "message": message,
                                "visible_to": VISIBLE_TO_CHOICES[1][1],
                                "image": self.ROOT_URL + image,
                                "url_link": url_link,
                                "userprofile": choice(user_profiles),
                            }
                        )
                    )
                    print("******************************************************")
                    print(cric_article_id)
                    print(page_no)
                    print(pitches)

                except Exception as error:
                    print(error)
                    continue
            try:
                Pitch.objects.bulk_create(pitches)
            except IntegrityError:
                continue


"""
from scraper.cricwebscraper.cricbuzz import CricBuzzScraper
cricbuzz = CricBuzzScraper()
cricbuzz.get_cricket_news_articles()
"""
