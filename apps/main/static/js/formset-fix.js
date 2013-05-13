/* Fix for formsets

  Taken from: https://bitbucket.org/etienned/django-autocomplete/changeset/0ec7260445d8
*/

/* define the 'console', because IE doesn't! */
if (!window.console)  console = {log: function() {}};

// Activate autocomplete on dynamically added row in inlines in admin.
$(window).load(function() {
    // Get all the inlines
    $('.formset .table').each(function() {
        var inlineGroup = $(this);
        var acWidgets = [];
        
        // For each inlines check for autocomplete input in the empty form
        inlineGroup.find('.form-row .ui-autocomplete-input').each(function() {
            var ac = $(this);
            // Copy the script tag and restore the pre-autocomplete state
            var ac_id = ac.attr('id').replace(/_text$/,'');
            var script = ac.nextAll('script').clone();
            script.text(script.text().replace(ac_id, ac_id.replace('0', '__prefix__')));
            acWidgets.push(script);
        });
        if (acWidgets.length > 0) {
            inlineGroup.find('.dynamic-form-add .add-row').attr('href', '#').click(function() {
                var formset_id = inlineGroup.parents('.formset').attr('id');
                // Find the current id #
                var num = $('#id_' + formset_id.replace(/group$/, 'TOTAL_FORMS')).val() - 1;
                $.each(acWidgets, function() {
                    // Clone the script tag, add the id # and append the tag
                    var widget = $(this).clone();
                    
                    widget.text(widget.text().replace(/__prefix__/, num));
                    console.log('widget:', this.text());
                    inlineGroup.append(widget);
                });
            });
        }
    });
});
