import re

from decimal import Decimal

from django.db import IntegrityError

from market.models import *
from scraper.cricwebscraper.espncricinfo import EspnLiveScoreScraper


class PlayerValuationScoring(object):
    valuation_calc = 0
    cric_type_to_model_mapping = {
        "T20": PlayerStatsT20,
        "T20Intl": PlayerStatsT20Intl,
        "ODI": PlayerStatsODI,
        "TEST": PlayerStatsTest,
    }
    EXTRAS = ["nb", "lb", "b", "w"]

    def get_players(self, cric_type):
        return self.cric_type_to_model_mapping[cric_type].objects.all()

    def calculate_initial_price(self, player):
        bowl_avg_runs = 24  # self._get_bbi_avg(cric_type)
        # bbi calculation
        if player.bbi in ["-", "0"]:
            bbiwickets = 0
            bbiruns = 24  # > pick a random reasonable no instead of bbi avg
        else:
            bbiwickets, bbiruns = player.bbi.split("/")
            bbiwickets = int(bbiwickets)
            bbiruns = int(bbiruns)
        # highest runs calculation
        if player.highest in ["0*", "0", "-"]:
            is_notout = 0
            highest_runs = 0
        else:
            if player.highest.endswith("*"):
                is_notout = 1
                highest_runs = int(re.findall("\d+", player.highest)[0])
            else:
                is_notout = 0
                highest_runs = int(player.highest)
        # 24 > random reasonable bowling sr
        # 50 > random reasonable bowling avg
        # 10 > random reasonable rpo
        bowling_sr = Decimal(24.00) if player.bowling_sr == 0.00 else player.bowling_sr
        bowling_average = (
            Decimal(50.00) if player.bowling_average == 0.00 else player.bowling_average
        )
        rpo = Decimal(10.00) if player.economy == 0.00 else player.economy
        bowling_ratio = (
            Decimal(player.bowling_innings / player.matches)
            if player.matches > 0
            else Decimal(1.00)
        )
        valuation_calc = (
            player.matches * 5
            + player.batting_innings * 5
            + player.notouts * 10
            + player.runs * 5
            + highest_runs * 10
            + is_notout * 10
            + player.batting_average * 50
            + player.balls_faced * 2
            + player.batting_sr * 50
            + player.hundreds * 300
            + player.fifties * 100
            + player.fours * 5
            + player.sixes * 15
            + player.catches * 10
            + player.stumpings * 10
            + player.bowling_innings * 5
            + player.balls_bowled * 5
            + player.wickets * 100
            + bbiwickets * 200
            + (24 - bbiruns) * 10
            + (Decimal(50) - bowling_average) * bowling_ratio * 50
            + (Decimal(10) - rpo) * bowling_ratio * 500
            + ((Decimal(24) - bowling_sr) * bowling_ratio * 100)
            + (player.fourfers * 100)
            + (player.fifers * 200)
            + (player.tenfers * 500)
        )
        system_valuation = valuation_calc * 100
        player_initial_price = system_valuation / 100000
        return round(player_initial_price, 2)

    def populate_company(self, player):
        company_codes = Company.objects.values_list("code", flat=True)
        try:
            c, d = player.name.split(" ")
            code = c[:2] + d[:3]
        except (IndexError, ValueError):
            c, d = "", ""
            code = player.name[:5]
        if code in company_codes:
            code = c[:3] + d[:3]
        company_data = {
            "code": code,
            "name": player.name,
            "cmp": self.calculate_initial_price(player),
        }
        try:
            return Company.objects.create(**company_data)
        except IntegrityError:
            raise Exception(f"Company exists with this player {player.name}")

    def _get_bbi_avg(self, cric_type):
        bbis = self.cric_type_to_model_mapping[cric_type].objects.values_list(
            "bbi", flat=True
        )
        bbi_avg = 0
        total_eligible_player_for_bbi_avg = 0
        for bbi in bbis:
            try:
                bbi_avg += int(bbi.split("/")[1])
                total_eligible_player_for_bbi_avg += 1
            except IndexError:
                continue
        return bbi_avg / total_eligible_player_for_bbi_avg

    @staticmethod
    def _sort_by_dict_values(dictionary):
        return {k: v for k, v in sorted(dictionary.items(), key=lambda item: item[1])}

    @staticmethod
    def _sort_by_dict_keys(dictionary):
        return {k: v for k, v in sorted(dictionary.items(), key=lambda item: item[0])}

    def create_22_match_entries(self, companies, match_format, url):
        """
         create 22 player entries in match table
         return matches: Match
      """
        match_id = url.split("/")[-2]
        match_objects = []
        for company in companies:
            match_data = {
                "match_format": match_format,
                "player": company,
                "match_id": match_id,
            }
            match_objects.append(Match(**match_data))
        return Match.objects.bulk_create(match_objects)

    def _parse_runs_str(self, ball_by_ball_json_data):
        """
            return runs, extras
        """
        # https://www.espncricinfo.com/series/pakistan-tour-of-west-indies-2021-1263146/west-indies-vs-pakistan-1st-test-1263169/ball-by-ball-commentary
        runs = ball_by_ball_json_data["run"]
        dismissal_type = ball_by_ball_json_data["dismissal_type"]
        try:
            if dismissal_type == "run out" and runs != "W":
                # rare case scenario of more than 1 run and getting run out
                return runs, ""
            return int(runs), ""
        except ValueError:
            if dismissal_type == "run out":
                return runs, ""
            for extra in self.EXTRAS:
                if runs.find(extra) == 1:
                    return re.findall("\d+", runs)[0], extra
        return runs, ""

    def ball_by_ball_update_score(self, live_match_url):
        """
        {'over': '47.1',
           'run': '2',
           'batsman': 'Pant',
           'bowler': 'Rabada',
           'fielder': '',
           'dismissal_type': '',
           'dismissed_batsman': ''
        }
        """
        ball_by_ball_json_data = EspnLiveScoreScraper().get_ball_by_ball_score(
            live_match_url
        )
        runs, extra = self._parse_runs_str(ball_by_ball_json_data)
        fielder_match = None
        dismissed_batsman_match = None
        try:
            batsman = Company.objects.get(
                name__contains=ball_by_ball_json_data["batsman"]
            )
            batsman_match = Match.objects.get(
                player=batsman, match_id=ball_by_ball_json_data["match_id"]
            )
            if runs != "W":
                if runs == 4:
                    batsman_match.fours += 1
                elif runs == 6:
                    batsman_match.sixes += 1
                batsman_match.runs += runs
                batsman_match.balls_faced += 1
                batsman_match.save()
        except Company.DoesNotExist:
            raise Exception(
                f"Company does not exist with this {ball_by_ball_json_data['batsman']}"
            )
        try:
            bowler = Company.objects.get(
                name__contains=ball_by_ball_json_data["bowler"]
            )
            bowler_match = Match.objects.get(
                player=bowler, match_id=ball_by_ball_json_data["match_id"]
            )

            bowler_match.balls_bowled += 1

            if runs == "W" and dismissal_type != "run out":
                bowler_match.wickets += 1
            elif runs != "W":
                bowler_match.runs_conceded += runs

            bowler_match.save()
        except Company.DoesNotExist:
            raise Exception(
                f"Company does not exist with this {ball_by_ball_json_data['bowler']}"
            )
        if ball_by_ball_json_data["fielder"]:
            try:
                fielder = Company.objects.get(
                    name__contains=ball_by_ball_json_data["fielder"]
                )
                fielder_match = Match.objects.get(
                    player=fielder, match_id=ball_by_ball_json_data["match_id"]
                )
                if dismissal_type == "run out":
                    fielder_match.runouts += 1
                elif dismissal_type == "c":
                    fielder_match.catches += 1
                elif dismissal_type == "st":
                    fielder_match.stumpings += 1
                fielder_match.save()
            except Company.DoesNotExist:
                raise Exception(
                    f"Company does not exist with this {ball_by_ball_json_data['fielder']}"
                )
        if ball_by_ball_json_data["dismissed_batsman"]:
            try:
                dismissed_batsman = Company.objects.get(
                    name__contains=ball_by_ball_json_data["dismissed_batsman"]
                )
                dismissed_batsman_match = Match.objects.get(
                    player=dismissed_batsman,
                    match_id=ball_by_ball_json_data["match_id"],
                )
                dismissed_batsman_match.dismissed += 1
                dismissed_batsman_match.save()
            except Company.DoesNotExist:
                raise Exception(
                    f"Company does not exist with this {ball_by_ball_json_data['dismissed_batsman']}"
                )
    def update_valuations(self, match):
        # TODO: the whole update scoring
        cmp_calculation = (
            match.runs * 5
            + match.balls_faced * 2
            + match.fours * 5
            + match.sixes * 15
            + match.catches * 10
            + match.stumpings * 10
            + match.balls_bowled * 5
            + match.wickets * 100
            + match.runouts * 10
            + cfbattingsr * 50
            + (10 - cfeconomy) * 500
            + fifties * 100
            + hundreds * 300
            + fourfers * 100
            + fifers * 200
        )

        cmp_calculation = cmp_calculation * 1.25 # This makes current form 10% more valid than normal stats
        cmp_calculation = cmp_calculation - (match.dismissed * 100)

        #newcmp = (company.cmp + company.curform)/100000;

"""
from scoring import PlayerValuationScoring

from market.models import *

pv=PlayerValuationScoring()

ips = {}
players = PlayerStatsT20.objects.all()
for player in players:
   ips.update({player.name: pv.calculate_initial_price(player)})

"""

"""
create companies
In [4]: from market.models import *
   ...: 
   ...: from scraper.cricwebscraper.espncricinfo import EspnLiveScoreScraper
   ...: 
   ...: from scoring import PlayerValuationScoring
   ...: 
   ...: pv=PlayerValuationScoring()
   ...: 
   ...: 
   ...: players = PlayerStatsTest.objects.all()
   ...: 
   ...: for player in players:
   ...:      PlayerValuationScoring().populate_company(player)

"""

"""
create match entries
from scraper.cricwebscraper.espncricinfo import EspnLiveScoreScraper
from scoring import PlayerValuationScoring
from market.models import *

live_match_url = 'https://www.espncricinfo.com/series/india-in-south-africa-2021-22-1277060/south-africa-vs-india-1st-test-1277079/live-cricket-score'
players = EspnLiveScoreScraper().get_22_players_for_the_live_match(live_match_url)
companies = Company.objects.filter(name__in=[p.name for p in players])
match_format = 'Test'
PlayerValuationScoring().create_22_match_entries(companies, match_format, live_match_url)
"""
