import random
import json

from os import listdir
from os.path import isfile, join
from time import sleep

from django.utils import timezone
from django.core.management import BaseCommand
from django.db import IntegrityError
from django.core.exceptions import MultipleObjectsReturned
from dateutil.relativedelta import relativedelta
from django.db.models import Q


from accounts.models import User

from market.models import Company, CompanyCMPRecord, CMP_CHANGE_REASONS, BallbyBall

# len(set([re.sub(r"\s+", "", i, flags=re.UNICODE) for i in Company.objects.values_list('code', flat=True)]))
class Command(BaseCommand):
    companies = Company.objects.all()

    def handle(self, *args, **options):
        self.create_ballbyballs()
        # self.call_update_valuations()

    def mapping_company(self, company_name):
        last_name = company_name.split(" ")[-1]
        try:
            company = Company.objects.get(name__iregex=last_name)
        except Company.DoesNotExist:
            raise Exception(f"No company found: {company_name}")
        except MultipleObjectsReturned:
            same_surname_companies = Company.objects.filter(name__iregex=last_name)
            try:
                company = same_surname_companies.get(
                    Q(name__startswith=company_name[0].upper())
                    | Q(name__startswith=company_name[:2].upper())
                    | Q(name__startswith=company_name[:3].upper())
                    | Q(name__startswith=company_name[:4].upper())
                )
            except MultipleObjectsReturned:
                raise Exception(
                    f"company exists with same first letter and surname: {company_name}"
                )
        return company

    def _get_all_files(self):
        mypath = "/home/lenovo/Downloads/ipl2021json/"
        jsonfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
        jsonfiles = [mypath + filename for filename in jsonfiles]
        return jsonfiles

    def create_ballbyballs(self):
        jsonfiles = self._get_all_files()
        for json_file in jsonfiles[5:]:
            json_file = open(json_file, "rb")
            content = json.loads(json_file.read())
            match_date = content["meta"]["created"]
            match_info = content["info"]
            match_id = "-".join([str(i) for i in content["info"]["event"].values()])
            innings_data = content["innings"]
            print(match_id)
            if not BallbyBall.objects.filter(match_id=match_id).exists():
                innings_no = 0
                for innings in innings_data:
                    innings_no += 1
                    for over in innings["overs"]:
                        over_no = over["over"] + 1
                        delivery_no = 0
                        for delivery in over["deliveries"]:
                            delivery_no += 1
                            batsman = delivery["batter"]
                            try:
                                batsmanco = self.mapping_company(batsman)
                            except Exception as e:
                                print(e)
                                continue
                            bowler = delivery["bowler"]
                            try:
                                bowlerco = self.mapping_company(bowler)
                            except Exception as e:
                                print(e)
                                continue
                            runs_batsman = delivery["runs"]["batter"]
                            runs_extra = delivery["runs"]["extras"]
                            if delivery.get("extras"):
                                extra_type = list(delivery["extras"].keys())[0]
                            else:
                                extra_type = None
                            if delivery.get("wickets"):
                                wicket_data = delivery["wickets"]
                                dismissal_type = wicket_data[0]["kind"]
                                try:
                                    dismissed_batsman = self.mapping_company(
                                        wicket_data[0]["player_out"]
                                    )
                                except Exception as e:
                                    print(e)
                                    continue

                                if wicket_data[0].get("fielders"):
                                    fielder = self.mapping_company(
                                        wicket_data[0]["fielders"][0]["name"]
                                    )
                                else:
                                    fielder = None
                            else:
                                dismissal_type = None
                                dismissed_batsman = None
                                fielder = None
                            ball_by_ball_data = {
                                "match_id": match_id,
                                "innings_no": innings_no,
                                "over_no": over_no,
                                "delivery_no": delivery_no,
                                "batsman": batsmanco,
                                "bowler": bowlerco,
                                "runs_batsman": runs_batsman,
                                "runs_extra": runs_extra,
                                "extra_type": extra_type,
                                "dismissal_type": dismissal_type,
                                "dismissed_batsman": dismissed_batsman,
                                "fielder": fielder,
                            }
                            print(ball_by_ball_data)
                            try:
                                ball = BallbyBall.objects.create(**ball_by_ball_data)
                                print("ball_id")
                                print(ball.id)
                            except IntegrityError:
                                print("IntegrityError")
                                continue


def company_to_playerstat(company_name):
    from django.core.exceptions import MultipleObjectsReturned

    last_name = company_name.split(" ")[-1]
    try:
        playerstat = PlayerStats.objects.get(name__iregex=last_name)
    except PlayerStats.DoesNotExist:
        raise Exception(f"No company found: {company_name}")
    except MultipleObjectsReturned:
        same_surname_companies = PlayerStats.objects.filter(name__iregex=last_name)
        try:
            playerstat = PlayerStats.objects.filter(name__iregex=last_name).get(
                name__startswith=company_name[:4]
            )
        except MultipleObjectsReturned:
            try:
                playerstat = PlayerStats.objects.filter(name__iregex=last_name).get(
                    name__startswith=company_name[0]
                )
            except MultipleObjectsReturned:
                raise Exception(
                    f"company exists with same first letter and surname: {company_name}"
                )
    playerstat.company = Company.objects.get(name=company_name)
    playerstat.save()
    return playerstat


def restchanges(company_name):
    last_name = company_name.split(" ")[-1]
    playerstat = PlayerStats.objects.filter(name__iregex=last_name).filter(
        name__startswith=company_name[0]
    )
    if playerstat.count() == 1:
        company = Company.objects.get(name=company_name)
        playerstat[0].company = company
        playerstat[0].save()
        return playerstat
    print(company_name)


def call_update_valuations_sql():
    import psycopg2
    from market.models import BallbyBall, Match, PlayerStats, Company
    from django.db.models import Max, Min
    from django.db import transaction

    match_list = []
    for matchno in range(1, 57):
        match_list.append(f"Indian Premier League-{matchno}")
    match_list.append("Indian Premier League-Qualifier 1")
    match_list.append("Indian Premier League-Qualifier 2")
    match_list.append("Indian Premier League-Eliminator")
    match_list.append("Indian Premier League-Final")
    # 60 * 240 * 2 * 20 * 6

    conn = psycopg2.connect(
        database="wallstreet",
        user="postgres",
        password="Champ2424",
        host="wallstreet.ciqodeqxwwle.us-west-1.rds.amazonaws.com",
        port="5432",
    )

    for match in match_list[2:]:
        # Shorlisting data for one match
        print(match)
        match_data = BallbyBall.objects.filter(match_id=match)
        print(match_data.count())
        # Add all players that have played a particular match to market_match
        for data in match_data:
            fielder = None
            dismissed_batsman = None
            try:
                print(data.id)
                batsman = PlayerStats.objects.get(id=data.batsman.id)
                bowler = PlayerStats.objects.get(id=data.bowler.id)
                if fielder:
                    fielder = PlayerStats.objects.get(id=data.fielder.id)
                if dismissed_batsman:
                    dismissed_batsman = PlayerStats.objects.get(
                        id=data.dismissed_batsman.id
                    )
            except Exception as err:
                print(err)
                continue
            _ = Match.objects.get_or_create(
                match_id=match, player=batsman, name=data.batsman.name
            )
            _ = Match.objects.get_or_create(
                match_id=match, player=bowler, name=data.bowler.name
            )
            if fielder:
                _ = Match.objects.get_or_create(
                    match_id=match, player=fielder, name=data.fielder.name
                )
            if dismissed_batsman:
                _ = Match.objects.get_or_create(
                    match_id=match,
                    player=dismissed_batsman,
                    name=data.dismissed_batsman.name,
                )
        # After this loop, we should have entries for all players in a particular match in market_match
        for innings in range(1, 3):
            for over in range(1, 21):
                print(over)
                over_balls = match_data.filter(innings_no=innings, over_no=over)
                # Looping over the id columns in one over because delivery_no is incorrectly populated for some matches
                for ball_id in range(
                    over_balls.aggregate(Min("id"))["id__min"],
                    over_balls.aggregate(Max("id"))["id__max"] + 1,
                ):
                    ball = BallbyBall.objects.get(id=ball_id)
                    runs_batsman = ball.runs_batsman
                    runs_extra = ball.runs_extra
                    fielder = None
                    dismissed_batsman = None
                    try:
                        batsman = PlayerStats.objects.get(id=ball.batsman.id)
                        bowler = PlayerStats.objects.get(id=ball.bowler.id)
                        if ball.fielder_id:
                            fielder = PlayerStats.objects.get(id=ball.fielder.id)
                        if ball.dismissed_batsman_id:
                            dismissed_batsman = PlayerStats.objects.get(
                                id=ball.dismissed_batsman.id
                            )
                    except:
                        continue
                    # Fetching table rows for all players involved in a ball
                    batsman, _ = Match.objects.get_or_create(player_id=batsman)
                    bowler, _ = Match.objects.get_or_create(player_id=bowler)
                    if fielder:
                        fielder, _ = Match.objects.get_or_create(player_id=fielder)
                    if dismissed_batsman:
                        dismissed_batsman, _ = Match.objects.get_or_create(
                            player_id=dismissed_batsman
                        )

                    batsman.runs = batsman.runs + int(runs_batsman)
                    bowler.runs_conceded = bowler.runs_conceded + int(runs_batsman)
                    if int(runs_batsman) == 4:
                        batsman.fours = batsman.fours + 1
                    elif int(runs_batsman) == 6:
                        batsman.sixes = batsman.sixes + 1
                    if int(runs_extra) == 0:
                        bowler.balls_bowled = bowler.balls_bowled + 1
                        batsman.balls_faced = batsman.balls_faced + 1
                    else:
                        if ball.extra_type == "wides" or ball.extra_type == "noballs":
                            bowler.runs_conceded = bowler.runs_conceded + int(
                                runs_extra
                            )
                        elif ball.extra_type == "byes" or ball.extra_type == "legbyes":
                            bowler.balls_bowled = bowler.balls_bowled + 1

                    if ball.dismissal_type == "caught":
                        if dismissed_batsman:
                            dismissed_batsman.dismissed = 1
                        fielder.catches += 1
                        bowler.wickets += 1

                    elif ball.dismissal_type == "caught and bowled":
                        if dismissed_batsman:
                            dismissed_batsman.dismissed = 1
                        bowler.wickets += 1
                        bowler.catches += 1

                    elif ball.dismissal_type == "bowled" or "lbw" or "hit wicket":
                        if dismissed_batsman:
                            dismissed_batsman.dismissed = 1
                        bowler.wickets += 1

                    elif ball.dismissal_type == "run out":
                        if dismissed_batsman:
                            dismissed_batsman.dismissed = 1
                        # fielder.runouts = fielder.runouts + 1

                    elif ball.dismissal_type == "stumped":
                        dismissed_batsman.dismissed = 1
                        fielder.stumpings += 1
                        bowler.wickets += 1

                    batsman.save()
                    bowler.save()
                    if fielder:
                        fielder.save()
                    if dismissed_batsman:
                        dismissed_batsman.save()
                    try:
                        cursor = conn.cursor()
                        sql = (
                            "call update_valuations_new("
                            + str(batsman.player_id)
                            + ");"
                        )
                        cursor.execute(sql)
                        sql = (
                            "call update_valuations_new(" + str(bowler.player_id) + ");"
                        )
                        cursor.execute(sql)
                        if fielder:
                            sql = (
                                "call update_valuations_new("
                                + str(fielder.player_id)
                                + ");"
                            )
                            cursor.execute(sql)
                        if (
                            dismissed_batsman
                            and dismissed_batsman.player_id != batsman.player_id
                        ):
                            # If dismissed_batsman is batsman, no need to call it twice
                            sql = (
                                "call update_valuations_new("
                                + str(dismissed_batsman.player_id)
                                + ");"
                            )
                            cursor.execute(sql)
                    except Exception as e:
                        print(e)
                        print("rolling back--")
                        cursor.execute("rollback")
                        continue
                    conn.commit()
                    cursor.close()
    conn.close()
