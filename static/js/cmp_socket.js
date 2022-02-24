const ws_schema = window.location.protocol === "http:" ? "ws://" : "wss://";

const socket = new WebSocket(
    ws_schema +
    window.location.host +
    '/ws/realtime-cmp/'

);
socket.onmessage = function(e) {
    var data = JSON.parse(e.data);
    var playerElems = document.getElementsByClassName("watchlistPlayer");
    [].slice.call(playerElems).forEach(function(eachPlayer) {
        if (eachPlayer.getAttribute('data-company') == data['company_id']) {
            //TODO: will break for different structure
            if (eachPlayer.firstElementChild.lastElementChild.hasAttribute('stock_price')) {
                var ep = eachPlayer.firstElementChild.lastElementChild;
                ep.firstElementChild.innerText = data['cmp'];

            }
        }

    });
    if (window.location.href.includes('player-detail')) {
        var cmpText = 'Current Market Price: {latest_cmp}'.replace(
            '{latest_cmp}', data.cmp);
        var cmpUpdatedTime = 'Last Updated: {updated_time}'.replace(
            '{updated_time}', new Date(data.timestamp * 1000).toLocaleString('en-US'));
        $(".cmp-player-detail").text(cmpText);
        $(".player-last-updated").text(cmpUpdatedTime);
    }

}