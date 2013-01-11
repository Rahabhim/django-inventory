// Puts the included jQuery into our own namespace
// but only do that if core Django hasn't already initialized jQuery

if (typeof django != "object" || typeof django.jQuery != "function") {
    var django = {
        "jQuery": jQuery
    };
    console.log("Aliased 1st instance of jQuery");
    
}

