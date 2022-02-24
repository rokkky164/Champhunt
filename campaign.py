from random import randint, choice

from accounts.models import PotentialUser

MAX_WAITLIST_USERS = 10000

TOTAL_BUDGET = 50000

REWARD_AMOUNT = range(3, 31)

WAITLIST_CAMPAIGN = 'Waitlist Campaign'

FIRST_RANGE_COUNT_LIMIT = 9000
SECOND_RANGE_COUNT_LIMIT = 750
THIRD_RANGE_COUNT_LIMIT = 250


class WaitListCampaign(object):
    """
        Distribute waitlist campaign amount among 10k users ranging
        from Rs 3 to Rs 30
        3, 5 => 9000
        6, 20 => 750
        21, 30 => 250
    """
    @staticmethod
    def _get_total_waitlist_campaigners():
        return PotentialUser.objects.filter(source=WAITLIST_CAMPAIGN)

    def generate_reward_amount(self):
        try:
            waitlist_campaigners = self._get_total_waitlist_campaigners()
            if waitlist_campaigners.count() >= MAX_WAITLIST_USERS:
                raise Exception("Waitlist Campaign is over.")
            amount_list = [
                [i for i in range(3, 6)],
                [i for i in range(6, 21)],
                [i for i in range(21, 31)]
            ]

            random_range = choice(amount_list)
            range_count_limit_mapping = {
                0: FIRST_RANGE_COUNT_LIMIT,
                1: SECOND_RANGE_COUNT_LIMIT,
                2: THIRD_RANGE_COUNT_LIMIT 
            }
            range_count = waitlist_campaigners.filter(waitlist_amount__in=random_range).count()
            range_limit = range_count_limit_mapping[amount_list.index(random_range)]
            amount = choice(random_range)
            if range_count >= range_limit:
                print ("limit over for this range\n" + ", ".join([str(i) for i in random_range]))
                return self.generate_reward_amount()
            else:
                return amount
        except RecursionError:
            return 3


"""

from campaign import WaitListCampaign

wc = WaitListCampaign()

wc.generate_reward_amount()


"""