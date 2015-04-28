
angular.module('f3.movable', [ 'ui.bootstrap'])
    .directive( 'moveHook', ['$window', '$compile', '$document', '$position', function ( $window, $compile, $document, $position) {
      return {
        restrict: 'A',
        scope: true,
        link: function link ( scope, element, attrs ) {
            if (! element.attr('id'))
                throw Error("moveHook cannot work without 'id' attribute on element");

            scope.xoffset = parseInt(attrs['moveHookXoffset'] || 0);
            scope.yoffset = parseInt(attrs['moveHookYoffset'] || 0);

            var get_parent_align ;
            var pos_align_mode;
            var receive_data_name = attrs['ngClickReceive'];
            scope._move_close_hook = false;

            /* retrieve the absolute offset for this element, once */
            element.css( {position:'absolute', left: 0, top: 0});
            var init_pos = $position.offset(element);

            if ('leftOf' in attrs){
                get_parent_align = function(){
                var other_elem = angular.element('#' + attrs.leftOf);
                if (! other_elem)
                    throw Error("Object not found at left-of: #"+attrs.leftOf);
                var other_pos = $position.offset(other_elem);
                return {
                        left: other_pos.left + other_pos.width + scope.xoffset - init_pos.left,
                        top: other_pos.top + scope.yoffset - init_pos.top};
                };
                pos_align_mode = 'horizontal';
            }
            else if ('under' in attrs){
                get_parent_align = function(){
                var other_elem = angular.element('#' + attrs.under);
                if (! other_elem)
                    throw Error("Object not found at under: #"+attrs.under);
                var other_pos = $position.offset(other_elem);
                return {
                        left: other_pos.left + scope.xoffset - init_pos.left,
                        top: other_pos.top + other_pos.height + scope.yoffset - init_pos.top};
                };
                pos_align_mode = 'vertical';
            }
            /* TODO: other position modes */
            else
                throw Error("Invalid or unset position for moveHookId");

            scope._alignTo = function(other_element, data, _move_close_hook) {
                var ncss = get_parent_align();
                var other_pos = $position.offset(other_element);
                if (pos_align_mode == 'horizontal')
                    ncss.top = other_pos.top + scope.yoffset - init_pos.top;
                else if (pos_align_mode == 'vertical')
                    ncss.left = other_pos.left + scope.xoffset - init_pos.left;
                if (receive_data_name)
                    scope[receive_data_name] = data;
                element.css(ncss);
                element.show();
                scope._move_close_hook = _move_close_hook;
            };

            /* align to parent, now */
            element.css(get_parent_align());
            element.hide();

            scope.close = function(){
                element.hide();
                if (this._move_close_hook)
                    this._move_close_hook();
            };
        }
    };
    }])
.directive( 'ngClickAlign', ['$window', '$compile', '$document', '$position', '$parse', function ( $window, $compile, $document, $position, $parse) {
      return {
        restrict: 'A',
        scope: true,
        link: function link ( scope, element, attrs ) {
            var move_id = '#' + attrs['ngClickAlign'];
            var send_data_name = attrs['ngClickSend'];
            var _move_close_hook = false;
            if ('ngMoveClose' in attrs){
                var fn = $parse(attrs['ngMoveClose']);
                _move_close_hook = function() { fn(scope) };
            }
            element.bind('click', function(event) {
                scope.$apply(function() {
                    var move_elem = angular.element(move_id);
                    var data = undefined;
                    if (send_data_name)
                        data = scope.$eval(send_data_name);
                    move_elem.scope()._alignTo(element, data, _move_close_hook);
                    });
                });
            },
        };
    }]);

// eof