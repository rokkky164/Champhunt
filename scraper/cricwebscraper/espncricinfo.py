import re
from decimal import Decimal, DecimalException
from django.db import IntegrityError

from scraper.mixins import BaseScraperMixin
from .cricbuzz import CricBuzzScraper

from market.models import (
    PlayerStatsT20Intl,
    PlayerStatsT20,
    PlayerStatsODI,
    PlayerStatsTest,
)

stats_url = "https://hs-consumer-api.espncricinfo.com/v1/pages/player/stats/summary?playerId=5334&recordClassId=3&type=BATTING"


class EspnLiveScoreScraper(BaseScraperMixin):
    DOT_BALL = "•"
    WICKET = "W"
    DISMISSAL_TYPES = ["lbw", "c", "st", "hit wicket", "b"]
    EXTRAS = ["nb", "lb", "b", "w"]
    ODI = "ODI"
    TEST = "Test"
    T20Intl = "T20I"
    T20LEAGUE = "T20"

    def _parse_wicket_comment(self, wicket_comment_str):
        """
            # Tom Cooper c Maxwell b Couch 8 (3b 2x4 0x6) SR: 266.66
            # Roston Chase run out (Bess) 7 (33m 20b 0x4 0x6) SR: 35
            # Tim Southee b Avesh Khan 3 (7m 5b 0x4 0x6) SR: 60
        """
        fielder = None
        dismissal_type = None
        dismissed_batsman = None
        lp, rp = wicket_comment_str.split(" b ")
        for dismissal_type in self.DISMISSAL_TYPES:
            dismissal_type_elem = [i for i in lp.split(" ") if i == dismissal_type]
            if (
                len(dismissal_type_elem) == 1
                and dismissal_type_elem[0] == dismissal_type
            ):
                dismissed_batsman, fielder = lp.split(dismissal_type)
                return fielder, dismissal_type, dismissed_batsman
            elif len(dismissal_type_elem) == 0:
                dismissed_batsman = lp
                dismissal_type = "b"
                return fielder, dismissal_type, dismissed_batsman
        # separate handling for run out
        if len(wicket_comment_str.split(" b ")) and "run out" in wicket_comment_str:
            lp, rp = wicket_comment_str.split("run out")
            dismissed_batsman = lp.strip()
            dismissal_type = "run out"
            fielder = rp[rp.find("(") + 1 : rp.find(")")]
            return fielder, dismissal_type, dismissed_batsman

    def get_ball_by_ball_score(self, live_match_url):
        webcontent = self._get_soup(live_match_url)
        over = ""
        run = ""
        batsman = ""
        bowler = ""
        fielder = ""
        dismissal_type = ""
        dismissed_batsman = ""

        try:
            live_score_card = webcontent.find(class_="card content-block match-live")
            live_over_card = webcontent.find(
                "div", {"itemtype": "https://schema.org/LiveBlogPosting"}
            )
            start_time = live_over_card.find("meta", itemprop="coverageStartTime").get(
                "content"
            )
            end_time = live_over_card.find("meta", itemprop="coverageEndTime").get(
                "content"
            )
            match_headline = live_over_card.find("meta", itemprop="headline").get(
                "content"
            )
            match_description = live_over_card.find("meta", itemprop="description").get(
                "content"
            )

            latest_ball_elem = live_over_card.find("div", class_="match-comment")
            over = latest_ball_elem.find(class_="match-comment-over").get_text()
            run = latest_ball_elem.find(class_="match-comment-run-container").get_text()
            ball_by_ball_comment = latest_ball_elem.find(
                class_="match-comment-short-text"
            ).get_text()
            bowler, batsman = ball_by_ball_comment.split("to")
            bowler = bowler.strip()
            batsman = batsman.split(",")[0].strip()
            fielder = None
            dismissal_type = None
            dismissed_batsman = None
            # wicket: match-comment-run match-comment-run-wicket
            if run == self.DOT_BALL:
                run = 0
            elif run == self.WICKET:
                wicket_comment = latest_ball_elem.find(
                    class_="match-comment-wicket match-comment-wicket-no-icon"
                ).get_text()
                fielder, dismissal_type, dismissed_batsman = self._parse_wicket_comment(
                    wicket_comment
                )
                try:
                    # handle run for cases: runout after taking 1 or more run
                    run = int(
                        re.findall(
                            "\d+",
                            [i for i in ball_by_ball_comment.split(",") if "run" in i][
                                0
                            ].strip(),
                        )[0]
                    )
                except Exception as error:
                    print(error)
        except Exception as err:
            print(err)
        return {
            "over": over,
            "run": run,
            "batsman": batsman,
            "bowler": bowler,
            "fielder": fielder or "",
            "dismissal_type": dismissal_type or "",
            "dismissed_batsman": dismissed_batsman or "",
            "match_id": live_match_url.split("/")[-2],
        }

    def get_22_players_for_the_live_match(self, url):
        """
        return playerstats
        """
        player_xi_url = "/".join(
            [elem for elem in url.split("/")[:-1]] + ["match-playing-xi"]
        )
        soup = self._get_soup(player_xi_url)
        match_squad_soup = soup.find("table", class_="match-squad-grid")
        player_strs = [
            s.get_text(",").strip()
            for s in match_squad_soup.findAll("a", class_="player-name")
        ]
        player_strs = [
            i.replace("(c)", "").replace("†", "").strip() for i in player_strs
        ]
        players = PlayerStatsTest.objects.filter(name__in=player_strs)

        if len(players) == 22:
            return players
        raise Exception("Some players are missing from playerstats table!")

    def get_players(self):
        """
            get players of international and league matches from cricbuzz
            return: players: dict
        """
        cricbuzz = CricBuzzScraper()
        cric_types = [cricbuzz.INTERNATIONAL, cricbuzz.T20LEAGUE]
        players = {}
        for cric_type in cric_types:
            players.update(cricbuzz.get_players(cric_type))
        return players

    def _handle_decimal_exceptions(self, value):
        try:
            Decimal(value)
        except DecimalException:
            value = Decimal(0)
        return value

    def _handle_integer_exceptions(self, value):
        try:
            int(value)
        except ValueError:
            value = 0
        return value

    def populate_playerstats(self):
        """
            create playerstats tables with career averages 
            for respective formats: T20, ODI, Test
            return None
        """
        players = list(self.get_players().values())
        # breakdown to a single array of players
        players = [item for sublist in players for item in sublist]
        players = list(set(players))
        search_root_url = "https://search.espncricinfo.com"
        for player_name in players:
            print(player_name)
            try:
                webcontent = self._get_soup(
                    f"https://search.espncricinfo.com/ci/content/site/search.html?search={player_name}"
                )
                ply_count_text = webcontent.find(
                    "a", {"href": re.compile("type=player")}, class_=True
                ).get_text()
                total_players_count = int(re.findall("\d", ply_count_text)[0])
                if total_players_count == 1:
                    player_partial_link = (
                        webcontent.find(class_="name link-cta").find("a").get("href")
                    )
                    player_page = search_root_url + player_partial_link
                    espn_player_url = self._get_redirected_url(player_page)
                    headers, player_stats_data = self.parse_player_page(espn_player_url)
                    batting_stats_header = "Mat,Inns,NO,Runs"
                    total_rows = len(player_stats_data)

                    if batting_stats_header in headers[0]:
                        # ['Format', 'Mat', 'Inns', 'NO', 'Runs', 'HS', 'Ave', 'BF', 'SR', '100s', '50s', '4s', '6s', 'Ct', 'St']
                        batting_stats_rows = player_stats_data[: int(total_rows / 2)]
                        bowling_stats_rows = player_stats_data[int(total_rows / 2) :]
                    else:
                        # ['Format', 'Mat', 'Inns', 'Balls', 'Runs', 'Wkts', 'BBI', 'BBM', 'Ave', 'Econ', 'SR', '4w', '5w', '10w']
                        bowling_stats_rows = player_stats_data[: int(total_rows / 2)]
                        batting_stats_rows = player_stats_data[int(total_rows / 2) :]

                    player_stats_formatted_data = {}
                    for each_row in batting_stats_rows:
                        each_row_data = each_row.split(",")
                        match_format = each_row_data[0]
                        if match_format in [
                            self.ODI,
                            self.TEST,
                            self.T20Intl,
                            self.T20LEAGUE,
                        ]:
                            # validate decimal fields:
                            fields = {
                                "batting_average": each_row_data[6],
                                "batting_sr": each_row_data[8],
                            }
                            for field in fields:
                                fields[field] = self._handle_decimal_exceptions(
                                    fields[field]
                                )
                            # validate integer fields:
                            int_fields = {
                                "matches": each_row_data[1],
                                "batting_innings": each_row_data[2],
                                "notouts": each_row_data[3],
                                "runs": each_row_data[4],
                                "balls_faced": each_row_data[7],
                                "hundreds": each_row_data[9],
                                "fifties": each_row_data[10],
                                "fours": each_row_data[11],
                                "sixes": each_row_data[12],
                                "catches": each_row_data[13],
                                "stumpings": each_row_data[14],
                            }
                            for int_field in int_fields:
                                int_fields[int_field] = self._handle_integer_exceptions(
                                    int_fields[int_field]
                                )
                            try:
                                batting_avg = Decimal(each_row_data[6])
                            except DecimalException:
                                batting_avg = Decimal(0)
                            player_stats_formatted_data.update(
                                {
                                    "name": player_name,
                                    "matches": int_fields["matches"],
                                    "batting_innings": int_fields["batting_innings"],
                                    "notouts": int_fields["notouts"],
                                    "runs": int_fields["runs"],
                                    "highest": each_row_data[5],
                                    "batting_average": fields["batting_average"],
                                    "balls_faced": int_fields["balls_faced"],
                                    "batting_sr": fields["batting_sr"],
                                    "hundreds": int_fields["hundreds"],
                                    "fifties": int_fields["fifties"],
                                    "fours": int_fields["fours"],
                                    "sixes": int_fields["sixes"],
                                    "catches": int_fields["catches"],
                                    "stumpings": int_fields["stumpings"],
                                    "espn_link": espn_player_url,
                                }
                            )
                            try:
                                if match_format == self.T20LEAGUE:
                                    PlayerStatsT20.objects.get_or_create(
                                        **player_stats_formatted_data
                                    )
                                if match_format == self.T20Intl:
                                    PlayerStatsT20Intl.objects.get_or_create(
                                        **player_stats_formatted_data
                                    )
                                if match_format == self.ODI:
                                    PlayerStatsODI.objects.get_or_create(
                                        **player_stats_formatted_data
                                    )
                                if match_format == self.TEST:
                                    PlayerStatsTest.objects.get_or_create(
                                        **player_stats_formatted_data
                                    )
                            except IntegrityError:
                                print("failed to create table")
                                continue
                    for each_row in bowling_stats_rows:
                        each_row_data = each_row.split(",")
                        match_format = each_row_data[0]
                        if match_format in [
                            self.ODI,
                            self.TEST,
                            self.T20Intl,
                            self.T20LEAGUE,
                        ]:
                            # validate decimal fields:
                            fields = {
                                "bowling_average": each_row_data[8],
                                "economy": each_row_data[9],
                                "bowling_sr": each_row_data[10],
                            }
                            for field in fields:
                                fields[field] = self._handle_decimal_exceptions(
                                    fields[field]
                                )
                            # validate integer fields:
                            int_fields = {
                                "bowling_innings": each_row_data[2],
                                "balls_bowled": each_row_data[3],
                                "runs_conceded": each_row_data[4],
                                "wickets": each_row_data[5],
                                "fourfers": each_row_data[11],
                                "fifers": each_row_data[12],
                                "tenfers": each_row_data[13],
                            }
                            for int_field in int_fields:
                                int_fields[int_field] = self._handle_integer_exceptions(
                                    int_fields[int_field]
                                )
                            player_stats_formatted_data = {
                                "bowling_innings": int_fields["bowling_innings"],
                                "balls_bowled": int_fields["balls_bowled"],
                                "runs_conceded": int_fields["runs_conceded"],
                                "wickets": int_fields["wickets"],
                                "bbi": each_row_data[6],
                                "bbm": each_row_data[7],
                                "bowling_average": fields["bowling_average"],
                                "economy": fields["economy"],
                                "bowling_sr": fields["bowling_sr"],
                                "fourfers": int_fields["fourfers"],
                                "fifers": int_fields["fifers"],
                                "tenfers": int_fields["tenfers"],
                            }
                            if match_format == self.T20LEAGUE:
                                PlayerStatsT20.objects.update_or_create(
                                    name=player_name,
                                    defaults=player_stats_formatted_data,
                                )
                            if match_format == self.T20Intl:
                                PlayerStatsT20Intl.objects.update_or_create(
                                    name=player_name,
                                    defaults=player_stats_formatted_data,
                                )
                            if match_format == self.ODI:
                                PlayerStatsODI.objects.update_or_create(
                                    name=player_name,
                                    defaults=player_stats_formatted_data,
                                )
                            if match_format == self.TEST:
                                PlayerStatsTest.objects.update_or_create(
                                    name=player_name,
                                    defaults=player_stats_formatted_data,
                                )

                else:
                    print(
                        f"Multiple players found with this player name: {player_name}"
                    )
            except Exception as error:
                print(error)
                continue

    def parse_player_page(self, player_page):
        """
            parse player page of espncricinfo
            return player career averages: list
        """
        webcontent = self._get_soup(player_page)
        headers, player_stats_data = [], []
        for player_stats_content in webcontent.findAll(
            class_="card overflow-hidden mb-3"
        ):
            if (
                player_stats_content.find(
                    class_="benton-bold pl-3 pt-4 pb-3 m-0 player-card-header"
                )
                and player_stats_content.find(
                    class_="benton-bold pl-3 pt-4 pb-3 m-0 player-card-header"
                ).get_text()
                == "Career Averages"
            ):
                player_data = player_stats_content.find(
                    class_="more-content overflow-hidden"
                ).findAll("div", recursive=False)
                batting_stats_content, bowling_stats_content = None, None
                for player_stats in player_data:
                    headers += [
                        i.get_text(",")
                        for i in player_stats.find("table").find("thead").findAll("tr")
                    ]
                    player_stats_data += [
                        i.get_text(",")
                        for i in player_stats.find("table").find("tbody").findAll("tr")
                    ]
        return headers, player_stats_data
