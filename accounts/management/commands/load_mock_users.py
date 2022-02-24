import names
import random
import string

from random import randint

from django.core.management import BaseCommand
from django.db import IntegrityError

from accounts.models import User, UserProfile


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.loadup_users()
        self.loadup_profiles()

    def loadup_users(self):
        email_domains = [
            "gmail.com",
            "hotmail.com",
            "rediffmail.com",
            "yahoo.com",
            "outlook.com",
        ]
        users = []
        for iterator in range(1000000):
            first_name, last_name = names.get_full_name().split(" ")
            usernames = [
                first_name
                + "".join(random.choice(string.ascii_letters) for x in range(5))
                + str(randint(100, 10000)),
                last_name
                + "".join(random.choice(string.ascii_letters) for x in range(5))
                + str(randint(10000, 100000)),
            ]
            emails = [
                f"{last_name}.{first_name}@" + random.choice(email_domains),
                f"{first_name}.{last_name}@" + random.choice(email_domains),
            ]
            user_data = {
                "username": random.choice(usernames),
                "email": random.choice(emails),
                "full_name": f"{first_name} {last_name}",
                "is_active": True,
            }
            print(iterator)
            print(user_data)
            try:
                User.objects.create(**user_data)
            except IntegrityError:
                print("IntegrityError")
                continue

            # users.append(User(**user_data))
            # if len(users) >= 100:
            #     print ("************************")
            #     print (len(users))
            #     try:
            #         User.objects.bulk_create(users)
            #         users = []
            #     except IntegrityError:
            #         print ('IntegrityError')
            #         users = []
            #         continue

    def loadup_profiles(self):
        users = User.objects.all()
        user_ids = User.objects.values_list("id", flat=True)
        profile_users = UserProfile.objects.values_list("user_id", flat=True)

        non_profile_user_ids = list(set(user_ids) - set(profile_users))

        non_existing_profile_users = User.objects.filter(id__in=non_profile_user_ids)
        profiles = []
        for user in non_existing_profile_users:
            profiles.append(
                {
                    "user_id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                }
            )
        UserProfile.objects.bulk_create(profiles)
