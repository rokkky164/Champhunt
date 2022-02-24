import names

from random import choice

from django.core.management import BaseCommand

from accounts.models import PotentialUser

from campaign import WaitListCampaign, WAITLIST_CAMPAIGN


class Command(BaseCommand):
    """
        Random function to choose a random amount between rs 3 and rs 30
        to give a user who joins the waitlist queue
    """

    def handle(self, *args, **options):
        self.test_waitlist_campaign()

    def test_waitlist_campaign(self):
        email_domains = [
            "gmail.com",
            "hotmail.com",
            "rediffmail.com",
            "yahoo.com",
            "outlook.com",
        ]
        for iterator in range(20000):
            first_name, last_name = names.get_full_name().split(" ")
            emails = [
                f"{last_name}.{first_name}@" + choice(email_domains),
                f"{first_name}.{last_name}@" + choice(email_domains),
            ]
            waitlist_cls = WaitListCampaign()
            waitlist_amount = waitlist_cls.generate_reward_amount()
            if waitlist_amount:
                potential_user_data = {
                    "email": choice(emails),
                    "source": WAITLIST_CAMPAIGN,
                    "waitlist_amount": waitlist_amount,
                }
                print(iterator)
                print(potential_user_data)

                try:
                    PotentialUser.objects.create(**potential_user_data)
                except IntegrityError:
                    print("IntegrityError")
                    continue
