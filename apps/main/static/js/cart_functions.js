/* functions for the carts */

function add_cart_click(anchor, form_id, cart_url) {
    var $form = $('#' + form_id)[0];
    $form.action = cart_url;
    $form.submit();
}

/* eof */