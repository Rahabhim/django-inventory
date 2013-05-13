var pendingRefreshTO;

function refreshStory(){
    console.log("Refresh story!");
    var div_story = $("#story");
    div_story.find("ul").empty();

    var has_add = false;
    $("#item_target ul li:not(.hint)").each(function() {
        var item_id = this.id.replace(/^item-/,'');
        var new_li = $("<li>").text($(this).text());
        new_li.append($("<input>", {type: "hidden", name: "parts_in", value: item_id}));
        $("#story_added ul").append(new_li);
        has_add = true;
    });

    if (has_add) {
        $("#story_noitems").hide();
        $("#story_added").show();
    }
    else
        $("#story_added").hide();
    
    // list the items removed
    var has_remove = false;
    $("#story_removed h5").hide();
    $("#story_removed ul").hide();
    $("#dests div.target ul li:not(.hint)").each(function() {
            var item_id = this.id.replace(/^item-/,'');
            var loc_id = $(this).parent().get(0).id.replace(/^outbin-/,'');
            // console.log("Removed " + item_id + " into " + loc_id);
            var new_li = $("<li>").text($(this).text());
            new_li.append($("<input>", {type: "hidden", name: "parts_out", value: loc_id+":" + item_id}));
            $("#story_removed #outstory-h-"+loc_id).show();
            $("#story_removed #outstory-"+loc_id).show().append(new_li);
            has_remove = true;
        });

    if (has_remove){
        $("#story_noitems").hide();
        $("#story_removed").show();
    }
    else
        $("#story_removed").hide();

    if ( has_add || has_remove)
        $("#dsubmit").show();
    else {
        $("#dsubmit").hide();
        $("#story_noitems").show();
    }
}

function receive_items(event, ui) {
    window.clearTimeout(pendingRefreshTO);
    $(this).find("li.hint").hide();
    if ($(ui.sender).find("li:not(.hint)").length == 0)
        $(ui.sender).find("li.hint").show();
    pendingRefreshTO = window.setTimeout(refreshStory, 500);
}

$(function() {
    $( "#sources" ).accordion({ collapsible: true, heightStyle: "content" });
    $( "#dests" ).accordion({ collapsible: true });

    /* Spare Parts to item incoming direction */
    $("#item_target ul").sortable({
                        connectWith: "#sources div.source ul", 
                        opacity: 0.8, 
                        cancel:"a,input,button,.hint",
                        placeholder: "ui-state-highlight",
                        receive: receive_items,
                        }).disableSelection();
    $("#sources div.source ul").sortable({
                        connectWith: "#item_target ul",
                        opacity: 0.8,
                        cancel:"a,input,button,.hint",
                        placeholder: "ui-state-highlight",
                        receive: receive_items,
                        } ).disableSelection();

    /* Item to outgoing direction */
    $("#parts_in_item ul").sortable({
                        connectWith: "#dests div.target ul", 
                        opacity: 0.8, 
                        cancel:"a,input,button,.hint",
                        placeholder: "ui-state-highlight",
                        receive: receive_items,
                        } ).disableSelection();
    $("#dests div.target ul").sortable({
                        connectWith: "#parts_in_item ul",
                        opacity: 0.8,
                        cancel:"a,input,button,.hint",
                        placeholder: "ui-state-highlight",
                        receive: receive_items,
                        } ).disableSelection();

    /* events: out(), receive() */
  });

function validateDate(dstr) {
  /* Validate that dstr is a valid date, in European dd/mm/YYYY or YYYY-mm-dd format
 */
    var m1 = date_fmt1.exec(dstr);
    if (m1){
        var dd = new Date(m1[3],m1[2]-1, m1[1]);
        if ((dd.getDate() == m1[1]) && (dd.getMonth() + 1 == m1[2]) && (dd.getFullYear() == m[3]))
            return true;
        else {
            console.log("Input date differs: " + dd.toDateString());
        }
        return false; // don't attempt fmt2
    }
    var m2 = date_fmt2.exec(dstr);
    if (m2){
        var dd = new Date(m1[1],m1[2]-1, m1[3]);
        if ((dd.getDate() == m1[3]) && (dd.getMonth() + 1 == m1[2]) && (dd.getFullYear() == m[1]))
            return true;
        else {
            console.log("Input date differs: " + dd.toDateString());
        }
    }
    return false;
}

function validateForm(form) {
    if (!validateDate(form.issue_date.value)){
        $("#date_invalid").show();
        return false;
    }
}
