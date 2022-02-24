$(document).ready(function() {
    var marketButton = $('.market-button');
    var marketButtonLink = marketButton.attr('href');
    marketButton.click(function(event) {
        event.preventDefault();
        marketButton.addClass('disabled');
        marketButton.html(
            "<i class='fas fa-spinner fa-spin'></i> " + 'Entering' + '...'
        );
        setTimeout(function() {
            window.location.href = marketButtonLink;
        }, 100);
    });
    // messages will be disappeared after 10s
    setTimeout(function(){
        if ($('#django-message').length > 0) {
            $('#django-message').remove();
        }
    }, 10000) 

    //
    var searchPlayersBtn = $("#playerQuery");
    searchPlayersBtn.click(function(event) {
        event.preventDefault();
        
        var playerSearchUrl = '/market/api/get-companies/';

        $.getJSON(playerSearchUrl, function (data) {
            // empty the content
            var $select = $("#playerOptions");
            $select.empty();
            $.each(data.companies, function (index, item) {
                $('<option />', {
                    value: item.id,
                    text: item.name + '- ' + item.code + item.cmp,
                    id: item.id
                }).appendTo($select)
                $select.removeClass('d-none');
            });
        });
    });

});