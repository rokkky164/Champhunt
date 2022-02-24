
var inviteCnt = 0;

function replaceClass(html, prefix, cntVar) {
    inputs = html.find('input');
    selects = html.find('select');
    inputs.each(function (i, item) {
        item = $(item);
        name = item.attr('name');
        item.attr('name', prefix + cntVar + '-' + name);
    });
    selects.each(function (i, item) {
        item = $(item);
        name = item.attr('name');
        item.attr('name', prefix + cntVar + '-' + name);
    });
}

function setinviteForm() {
    var prefix = 'invite';
    setMultipleForm("#inviteTemplate", "#inviteOptions", prefix, inviteCnt);
    inviteCnt++;
}

function setMultipleForm(TemSelector, ContSelector, prefix, cntVar) {
    var html = $(TemSelector).html();
    html = $(html);
    replaceClass(html, prefix, cntVar);
    $(ContSelector).append(html);
    return html;
}

$(document).ready(function() {
    $(".send-invite").click(function(){
        $(":input[required]").each(function () {
        var inviteForm = $('#invite_friends_form');
        if (inviteForm[0].checkValidity()) 
          {                
            $(inviteForm).submit();              
          }
        else {
            $("#errors").empty();
            $("#errors").text("Email Field is mandatory");
            setTimeout(function() {
                $("#errors").empty();
                }, 10000);
            }
        });
    })

    $(document)
        .on('click', ".add-row", function (e) {
            setinviteForm();
        })
        .on('click', ".removeOne", function (e) {
            e.preventDefault();
            var oneItem = $(this).parents(".removeOneItem");
            if (oneItem.parent().find('.removeOneItem').length >= 1) {
                oneItem.remove();
            }
        })
});

