from itertools import cycle
from rest_framework.response import Response

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated


class BaseChartViewMixin:
    COLOR_BLUE = "#1859da"
    COLOR_INDIGO = "#2220a2"
    COLOR_PURPLE = "#69067d"
    COLOR_PINK = "#f826a0"
    COLOR_RED = "#cc0c0c"
    COLOR_ORANGE = "#f8510a"
    COLOR_YELLOW = "#ee9c20"
    COLOR_GREEN = "#1c6a53"
    COLOR_TEAL = "#166963"
    COLOR_CYAN = "#1aa6b8"
    COLOR_DARK = "#081931"

    COLOR_PRIMARY = COLOR_INDIGO
    COLOR_SECONDARY = COLOR_INDIGO
    COLOR_SUCCESS = COLOR_GREEN
    COLOR_INFO = COLOR_CYAN
    COLOR_WARNING = COLOR_ORANGE
    COLOR_DANGER = COLOR_RED
    COLOR_BLACK = "#000000"
    GOOGLE_CHART_COLORS = (
        "#3366cc",
        "#dc3912",
        "#ff9900",
        "#109618",
        "#990099",
        "#0099c6",
        "#dd4477",
        "#66aa00",
        "#b82e2e",
        "#316395",
        "#994499",
        "#22aa99",
        "#aaaa11",
        "#6633cc",
        "#e67300",
        "#8b0707",
        "#651067",
        "#329262",
        "#5574a6",
        "#3b3eac",
        "#b77322",
        "#16d620",
        "#b91383",
        "#f4359e",
        "#9c5935",
        "#a9c413",
        "#2a778d",
        "#668d1c",
        "#bea413",
        "#0c5922",
        "#743411",
    )

    permission_classes = [IsAuthenticated]
    chart_type = "line"
    extra_chart_data = {}
    chart_options = {}
    chart_title = None
    colors = (
        COLOR_INDIGO,
        COLOR_ORANGE,
        COLOR_GREEN,
        COLOR_PURPLE,
        COLOR_DARK,
        COLOR_BLUE,
        COLOR_PINK,
        COLOR_TEAL,
        COLOR_YELLOW,
        COLOR_RED,
        COLOR_CYAN,
        COLOR_BLACK,
    ) + GOOGLE_CHART_COLORS

    def get_chart_type(self):
        return self.chart_type

    def get_chart_title(self):
        return self.chart_title

    def get_datasets(self, chart_type):
        return []

    def get_labels(self, datasets):
        return []

    def get_extra_chart_data(self):
        return self.extra_chart_data

    def get_extra_chart_options(self, data):
        return dict()

    def get_colors(self):
        return cycle(self.colors)

    def get_chart_options(self, data, **overrideoptions):
        options = {
            "responsive": True,
            "maintainAspectRatio": True,
            "aspectRatio": 1.75,
        }
        chart_title = self.get_chart_title()
        if chart_title:
            options.update({"title": {"display": True, "text": chart_title}})
        return {
            **options,
            **self.chart_options,
            **self.get_extra_chart_options(data),
            **overrideoptions,
        }

    def get_datasets_and_labels(self, chart_type):
        datasets = self.get_datasets(chart_type)
        return datasets, self.get_labels(datasets)

    def get_chart_data(self, chart_type):
        datasets, labels = self.get_datasets_and_labels(chart_type)
        return {
            "datasets": datasets,
            "labels": labels,
            **self.get_extra_chart_data(),
        }


class BaseChartAPIView(BaseChartViewMixin, APIView):
    def get(self, request, *args, **kwargs):
        chart_type = self.get_chart_type()
        data = self.get_chart_data(chart_type)
        options = self.get_chart_options(data)
        return Response({"type": chart_type, "data": data, "options": options,})
