const wsSchemaPlayerDetails = window.location.protocol === "http:" ? "ws://" : "wss://";
const userSocket = new WebSocket(
    wsSchemaPlayerDetails +
    window.location.host +
    '/ws/user/' +
    userID +
    '/'
);

userSocket.onmessage = function(e) {
    var data = JSON.parse(e.data);
    var data  = JSON.parse(data)
    var textContent = "Cash available: &#8377; {cashAvailable}".replace(
    	"{cashAvailable}", data.cash_available_for_user);
    $('.cash-avl').html(textContent);
}


function transactShares(orderMode, quantity, cmp, totalAmt) {
    $.ajax({
        type: "POST",
        url: "/market/api/transact-shares/",
        data: {
            "quantity": quantity,
            "cmp": cmp,
            "totalAmt": totalAmt,
            "order_mode": orderMode,
            "company_id": company_id
        },
        success: function(data) {
            if (orderMode == 'buy') {
                $('#orderbookPlayerDetailsBuy').addClass('d-none');
            } else {
                $('#orderbookPlayerDetailsSell').addClass('d-none');
            }
            var messages = JSON.parse(
                $("meta[name=application-messages]").attr("content")
            );
            var timeout = 0;
            messages.forEach(function(eachMsg) {
                setTimeout(function() {
                    toastr[eachMsg.tags](eachMsg.message)
                }, timeout);
                timeout = timeout + 5000;
            });
            $.ajax({
                url: "/market/update-user-cash/"
            })

        },
        error: function(data) {

        }
    });

}


$(document).ready(function() {
    $('.buy-player-details').on('click', function() {
        $('#orderbookPlayerDetailsBuy').removeClass('d-none');
        $('#orderbookPlayerDetailsSell').addClass('d-none');
    })

    $('.sell-player-details').on('click', function() {
        $('#orderbookPlayerDetailsSell').removeClass('d-none');
        $('#orderbookPlayerDetailsBuy').addClass('d-none');

    })

    $(".stockQuantity").on('change', function() {
        var totalAmt = $(this).val() * latestCmp;
        $(".totalAmount").text("Total Amount: {totalAmt}".replace("{totalAmt}", totalAmt));
        $(".totalAmount").removeClass('d-none');
    })

    $(".close").on('click', function() {
        $("#orderbookPlayerDetailsBuy").addClass("d-none");
        $("#orderbookPlayerDetailsSell").addClass("d-none");
    })

    $(".transact-buy-player-details").on('click', function() {
        var quantity = $("#buystockQuantity").val();
        var cmp = $("#buyLatestCMP").attr('value');
        var totalAmt = quantity * cmp;
        transactShares('buy', quantity, cmp, totalAmt);
    })

    $(".transact-sell-player-details").on('click', function() {
        var quantity = $("#sellstockQuantity").val();
        var cmp = $("#sellLatestCMP").attr('value');
        var totalAmt = quantity * cmp;
        transactShares('sell', quantity, cmp, totalAmt);
    })

});