from django.urls import re_path

from . import consumers


rest_api_urlpatterns = [
    re_path(r"ws/api/submit-pitch/$", consumers.PitchPostConsumer.as_asgi()),
    re_path(
        r"ws/api/comment-pitch/(?P<pitch_id>\w+)/$",
        consumers.PitchCommentConsumer.as_asgi(),
    ),
    re_path(
        r"ws/api/score-pitch/(?P<pitch_id>\w+)/$",
        consumers.PitchScoreConsumer.as_asgi(),
    ),
]
