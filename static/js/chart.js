function callJsonApi(series, graphUrl) {
    $.getJSON(graphUrl, function(data) {
        series.setData(data);
    });
}

function openTab(event, tabname) {
    var i, tabcontent, tablinks;

    // Get all elements with class="tabcontent" and hide them
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }

    // Get all elements with class="tablinks" and remove the class "active"
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }

    // Show the current tab, and add an "active" class to the button that opened the tab
    document.getElementById(tabname).style.display = "block";
    event.currentTarget.className += " active";
}

function createChart(chart_type, graphUrl) {
    // var existingSeries = chart.pw.entries().next().value;
    // if (existingSeries) {
    //     chart.removeSeries(existingSeries[0]);
    // }
    if (chart_type == 'candlestick') {
        const candleSeries = chart.addCandlestickSeries({
            upColor: '#008000',
            downColor: '#af111c',
            borderVisible: false,
            wickVisible: true,
            borderColor: '#000000',
            wickColor: '#000000',
            borderUpColor: '#008000',
            borderDownColor: '#af111c',
            wickUpColor: "#008000",
            wickDownColor: "#af111c",
        });

        callJsonApi(candleSeries, graphUrl);
        return candleSeries;

    } else if (chart_type == 'line') {
        const lineSeries = chart.addAreaSeries({
            topColor: '#4A3C7A',
            bottomColor: '#4A3C7A',
            lineColor: '#9BCBF0',
            lineStyle: 0,
            lineWidth: 3,
            crosshairMarkerVisible: true,
            crosshairMarkerRadius: 6,
            crosshairMarkerBorderColor: '#ffffff',
            crosshairMarkerdColor: '#2296f3',
            lineType: 0,
            lastPriceAnimation: LightweightCharts.LastPriceAnimationMode.Continuous,
            priceLineWidth: 2,
            baseLineWidth: 4
        });
        callJsonApi(lineSeries, graphUrl);
        return lineSeries;

    }

}

function updateChart(series) {
    const ws_schema = window.location.protocol === "http:" ? "ws://" : "wss://";
    const chartSocket = new WebSocket(
        ws_schema +
        window.location.host +
        '/ws/realtime-cmp/'

    );
    chartSocket.onmessage = function(e) {
        var data = JSON.parse(e.data);
        var chartData = {
            'time': data.timestamp,
            'value': data.cmp
        };
        series.update(chartData);
    }

}

const chartContainer = document.getElementById('stock_chart');

const chart = LightweightCharts.createChart(chartContainer, {
    width: 1100,
    height: 700,
    layout: {
        backgroundColor: '#2F2356',
        textColor: '#EB92F9'
    },
});

new ResizeObserver(entries => {
    if (entries.length === 0 || entries[0].target !== chartContainer) { return; }
      const newRect = entries[0].contentRect;
      chart.applyOptions({ height: newRect.height, width: newRect.width });
    }).observe(chartContainer);

chart.applyOptions({
    timeScale: {
        rightOffset: 5,
        barSpacing: 25,
        fixLeftEdge: false,
        lockVisibleTimeRangeOnResize: false,
        rightBarStaysOnScroll: false,
        borderVisible: true,
        borderColor: '#fff000',
        visible: true,
        timeVisible: true,
        secondsVisible: true,
        tickMarkFormatter: (time, tickMarkType, locale) => {
            var dateObj = new Date(time * 1000);
            var options = {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            };
            return dateObj.toLocaleDateString('en-US', options);
        },
    },
    crosshair: {
        vertLine: {
            color: '#707070',
            width: 0.5,
            style: 1,
            visible: true,
            labelVisible: true,
        },
        horzLine: {
            color: '#707070',
            width: 0.5,
            style: 0,
            visible: true,
            labelVisible: true,
        },
        mode: 0,
    },
});


$(document).ready(function() {
    var chartUrl = '/market/company-cmp-record/chart_type/company_id/';
    var chartType = $("#chart_type").val();
    var stock = $("#stock").val();
    var url = chartUrl.replace('chart_type', chartType).replace('company_id', stock);
    var series = createChart(chartType, url);
    var chartUrl = '/market/company-cmp-record/chart_type/company_id/';
    var chartType = $("#id_chart_type").val();
    var stock = $("#id_stock").val();
    var url = chartUrl.replace('chart_type', chartType).replace('company_id', stock);
    var series = createChart(chartType, url);
    updateChart(series);
    $(".footer-custom").addClass('d-none');
});