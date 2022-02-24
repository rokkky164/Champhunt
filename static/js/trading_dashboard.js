function jsonify(strArray) {
    strArray = strArray.replace(/'/g, '"');
    strArray = JSON.parse(strArray);
    return strArray
}

function toasterOptions() {
    toastr.options = {
        "closeButton": false,
        "debug": false,
        "newestOnTop": false,
        "progressBar": true,
        "positionClass": "toast-top-center",
        "preventDuplicates": true,
        "onclick": null,
        "showDuration": "100",
        "hideDuration": "1000",
        "timeOut": "5000",
        "extendedTimeOut": "1000",
        "showEasing": "swing",
        "hideEasing": "linear",
        "showMethod": "show",
        "hideMethod": "hide"
    };
};

function callWatchlistAPI() {
    var currentWatch = $("#stocks_watchlist").val();
    // call ajax to popualte watch list stocks
    var url = "/market/watchlist/id/";
    url = url.replace("id", currentWatch);
    $.getJSON(url, function(data) {
        // empty the content
        $("#stocks_watchlist_dropdown").html('');
        for (i = 0; i < data.stocks.length; i++) {
            var watchlistHtmlContent = "<a class='watchlistPlayer'" +
                "data-company='{companyID}'" +
                "href='/market/player-detail/{companyID}/'>" +
                "<div class='row watchlist-tab'>" +
                "<div class='col-lg-5 stock_name'>" +
                "<b>{name_and_code}</b>" +
                "</div>" +
                "<div class='col-lg-6' stock_price>" +
                "<b style='float: right'>{cmp}</b>" +
                "</div></div><hr/></a>"
            watchlistHtmlContent = watchlistHtmlContent.replace(
                '{name_and_code}', data.stocks[i].name + '-' + data.stocks[i].code).replace(
                '{cmp}', data.stocks[i].cmp).replaceAll(
                '{companyID}', data.stocks[i].id);
            // append the html content
            $("#stocks_watchlist_dropdown").append(watchlistHtmlContent);
        }
    });
}

function saveWatchlist() {

    var watchName = $("#watch_name").val();
    $.ajax({
        type: "POST",
        url: "/market/watchlist/",
        data: {
            "watch_name": watchName
        },
        success: function(data) {
            $("#createWatchList").modal('hide');
            var messages = JSON.parse(
                $("meta[name=application-messages]").attr("content")
            );
            var timeout = 1110;
            messages.forEach(function(eachMsg) {
                setTimeout(function() {
                    toastr[eachMsg.tags](eachMsg.message)
                }, timeout);
                timeout = timeout + 5000;
            });

        }
    });
}

$(document).ready(function() {
    // populate watchlist dropdown
    var select = document.getElementById("stocks_watchlist");
    var watchLists = jsonify(watchlists);
    for (var i = 0; i < watchLists.length; i++) {
        var opt = watchLists[i];
        var el = document.createElement("option");
        el.textContent = opt.watch_name;
        el.value = opt.id;
        select.appendChild(el);
    }

    // click on watchlist
    callWatchlistAPI();
    $("#stocks_watchlist").on('change', function() {
        callWatchlistAPI();
    })

    $(".create-watchlist").on('click', function() {
        $("#createWatchList").modal('show');
    })

    $(".save_watchlist").on('click', function() {
        saveWatchlist();
    })
    // on clicks
    $(document)
        // buy order review btn for order modal popup
        .on("click", ".buy_order_review", function(event) {
            var companyID = $("#companyID").val();
            var quantity = $("#id_quantity").val();
            var executionPrice = $("#id_execution_price").val();
            $.ajax({
                type: "GET",
                url: "/market/create-order/",
                data: {
                    'company_id': companyID,
                    'quantity': quantity,
                    'execution_price': executionPrice
                },
                success: function(responseHtml) {
                    var orderHtmlData = $(responseHtml).find('#OrderPlacingModalContent').html();
                    $("#createOrderModal").find('.modal-content').html(orderHtmlData);
                }
            });

        })

        // place order btn for order modal popup
        .on("click", ".buy_order", function(event) {
            var orderBookForm = $('#orderBookForm');
            var companyID = $("#companyID").val();
            var quantity = $("#id_quantity").val();
            var executionPrice = $("#id_execution_price").val();
            $.ajax({
                type: "POST",
                url: "/market/create-order/",
                data: {
                    "company_id": companyID,
                    "num_stocks": quantity,
                    "execution_price": executionPrice
                },
                complete: function(data) {

                    $("#createOrderModal").modal('hide');
                    var messages = JSON.parse(
                        $("meta[name=application-messages]").attr("content")
                    );
                    var timeout = 1110;
                    messages.forEach(function(eachMsg) {
                        setTimeout(function() {
                            toastr[eachMsg.tags](eachMsg.message)
                        }, timeout);
                        timeout = timeout + 5000;
                    });

                }
            });
        })
        // open order popup 
        .on("click", ".openOrderModal", function() {
            var companyID = $(this).attr('data-company');
            $.ajax({
                type: "GET",
                url: "/market/create-order/",
                data: {
                    'company_id': companyID
                },
                success: function(responseData) {
                    var orderHtmlData = $(responseData).find('.modal-content').html();
                    $("#createOrderModal").find('.modal-content').html(orderHtmlData);
                    $("#createOrderModal").modal('show');
                }
            })
        })

});