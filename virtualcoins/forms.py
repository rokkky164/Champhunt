from django import forms


class LoadUpVirtualCurrencyForm(forms.Form):
    virtual_coins = forms.IntegerField()
    amount = forms.FloatField()
    bonus_code = forms.CharField(required=False)
    payment_brand = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
