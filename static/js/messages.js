(function () {
    "use strict";
    $(document).ready(function () {
        var messages = JSON.parse(
            $("meta[name=application-messages]").attr("content")
        );

        var timeout = 0;
        // messages.forEach(function (message) {
        //     setTimeout(function () {
        //         $.toast({
        //             title: message.level_tag.toUpperCase(),
        //             content: message.message,
        //             type: message.level_tag,
        //             delay: 10000,

        //             pause_on_hover: false,
        //         });
        //     }, timeout);
        //     timeout = timeout + 1500;
        // });
    });
})();