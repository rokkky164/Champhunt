import json
import requests

from django.conf import settings


SPORTSMONK_BALLBYBALL_URL = f"https://cricket.sportmonks.com/api/v2.0/livescores?api_token={settings.SPORTSMONK_API_TOKEN}&include=balls"


class SportsMonk(object):
    def _get_ballbyball_content(self):
        sportsmonkresponse = requests.get(SPORTSMONK_BALLBYBALL_URL).content
        sportsmonkresponse = json.loads(sportsmonkresponse)
        return sportsmonkresponse
