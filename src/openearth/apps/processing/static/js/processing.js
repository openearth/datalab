if (!$) {
    $ = django.jQuery;
}

$('button').on('click', function (event) {

    var job, env;
    var action = $(event.target).data('action');

    if (action == 'start_job' || action == 'stop_job') {
        job = $(event.target).data('job-id');
        env = $(event.target).data('env-id');

        var url = '/environment/' + env + '/job/' + job + "/?action=" + action

        $.get(url, function (data, status) {
            if (status == 'success') {
                var next_action = data['action'] || null;
                if (next_action) {
                    $(event.target).data("action", next_action);
                    $(event.target).text(data["action_text"]);
                }
            }
        });
    }
});

$('.cb_scrolldown').on('click',function(e){
    var checkit = this.checked;
    $('.cb_scrolldown').each(function(){
        this.checked = checkit;
    });
});
$('#terminal').on('newmsg',function() {
    if($('#cb_scrolldown_first:checked').val()?true:false){
        $('html, body').animate({'scrollTop':$('html').height()},0);
    }
});

(function poll(){
   var action = $('#preform-job-action');
   var job = action.data('job-id');
   var env = action.data('env-id');
   var url = '/environment/' + env + '/job/' + job + "/?action=check_status";

   setTimeout(function(){
      $.ajax({ url: url, success: function(data){
        //Update status
        $('#job-status-field').text(data['status']);
        //Setup the next poll recursively
        if (data['status_value'] < 100){
            poll();
        }
      }, dataType: "json"});
  }, 15000);
})();

$(function () {

    if (typeof String.prototype.startsWith != 'function') {
        String.prototype.startsWith = function (str) {
            return this.slice(0, str.length) == str;
        };
    }

    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != "") {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function updateProgressBar(percent, message, id, type) {
        var bar_id = "__" + id || 'progress-bar';
        var type = "progress-bar-" + type || "";

        var bar = $('#progress-bar');

        if (id !== 'progress-bar'){
            var tbl_row = bar.closest('tr');

            var $clone = tbl_row.clone();
            $clone.find("#progress-bar").attr("id", bar_id);
            $clone.find("#progress-bar-message").attr("id", bar_id + "-message");
            tbl_row.parent().append($clone);
            bar = $('#' + bar_id);
        }
        bar.addClass(type);
        bar.closest('tr').show();
        bar.css("width", percent + '%');
        bar.attr("aria-valuenow", percent);
        bar.text(percent + '%');
        $("#" + bar_id + '-message').text(message);
    }

    function colorString(string) {
        var matches;
        if (string.startsWith("[E")) {
            return '<span class="text-danger">' + string + '</span>';
        } else if (string.startsWith("[D")) {
            return '<span class="text-muted">' + string + '</span>';
        } else if (string.startsWith("[I")) {

            var parts = string.split(' : ');
            if(parts[parts.length-1].startsWith("[#")){
                matches = parts[parts.length-1].match('\\[# ([0-9.]{1,4})%[\\s]?([\\w]+)*[\\s]?([\\w]+)* #\\][\\s]?([\\w\\s.]+)');
            }
            if (matches){
                updateProgressBar(matches[1], matches[4], matches[2], matches[3]);
            }else{
                return '<span class="text-info">' + string + '</span>';
            }
        } else if (string.startsWith("[W")) {
            return '<span class="text-warning">' + string + '</span>';
        } else {
            return string + '<br />';
        }
    }

    var csrftoken = getCookie('csrftoken');

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    $.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    var action = $('#terminal');
    var ws_url = action.data("ws-url");
    var ws_type = action.data("ws-type") || 'subscribe-user';
    var ws = new WebSocket(ws_url + '?' + ws_type);
    ws.onopen = function () {
        console.log("websocket connected");
        $('#terminal').append(colorString('[Info] Websocket connected. Listening for messages...') + '<br/>');
    };
    ws.onmessage = function (e) {
        var terminal = $('#terminal');
        var string = colorString(e.data.replace(new RegExp('\r?\n','g'), ''));
        if (string){
            terminal.append( string + '<br/>');
            terminal.trigger("newmsg");
        }
    };

    ws.onerror = function (e) {
        console.error(e);
        $('#terminal').append(colorString('[Error]' + e) + '<br/>');
    };
    ws.onclose = function (e) {
        console.log("connection closed");
        $('#terminal').append(colorString('[Error] Websocket connection closed.') + '<br/>');
    };

    window.onbeforeunload = function() {
        ws.close()
    };

});
