/*    According to this:
        http://stackoverflow.com/questions/3097332/jquery-drag-droppable-scope-issue
    and http://forum.jquery.com/topic/draggable-droppable-scope-bug
    
    */

angular.module('f3.draggable', [])
    .directive('ngShowFocused', ['$timeout', function($timeout) {
        return function($scope, element, attrs) {
            $scope.$watch(attrs.ngShow, function ngFocusPerhaps(value){
                if (value)
                    $timeout(function(){ element.focus(); });
            });
        };
    }])
    .directive('ngDraggable', ['$log', '$parse', function($log, $parse) {
    return {
      require: '?ngDroppable',
      restrict: 'A',
      // compile: function(tElement, tAttrs) { },
      link: function($scope, element, attrs) {
            var zIndex;
            var updateDraggable = function(newValue, oldValue) {
                var zIndex = 0;

            if (newValue) {
                // var dragSettings = scope.$eval(element.attr('jqyoui-draggable')) || {};
                var dsettings = {disabled: false, addClasses: false, helper: 'clone',
                                revert: 'invalid', scroll: true,
                                delay: 100, distance: 10};
                if (attrs.jqyouiOptions)
                    angular.extend(dsettings, $scope.$eval(attrs.jqyouiOptions))

                dsettings.start = function(event, ui) {
                    var dragModel = false;
                    if (attrs.ngDragModel)
                        dragModel = $scope.$eval(attrs.ngDragModel);
                    element.addClass('ui-beingdragged');
                    zIndex = $(this).css('z-index');
                    $(this).css('z-index', 99999);
                    $scope._dragItem = dragModel;
                    };

                dsettings.stop = function(event, ui) {
                    element.removeClass('ui-beingdragged');
                    $(this).css('z-index', zIndex);
                    $scope._dragItem = false;
                };
                /*
                dsettings.drag = function(event, ui) {
                    Do something while dragging
                    };*/

                element.draggable(dsettings);
            } else {
                element.draggable({disabled: true});
            }
        };
        $scope.$watch(function() { return $scope.$eval(attrs.ngDraggable); }, updateDraggable);
        updateDraggable();
      }
    };
  }])
.directive('ngDroppable', ['$log', '$parse', function($log, $parse) {
    return {
      restrict: 'A',
      priority: 1,
      compile: function(tElement, tAttrs) {
            var dropFn = function (event, ui) { $log.info("drop: " + ui.draggable); };

            if (tAttrs.ngOndrop)
                dropFn = $parse(tAttrs.ngOndrop);

            return { post: function($scope, element, attrs) {
                var updateDroppable = function(newValue, oldValue) {
                    if (newValue) {
                        var dsettings = {disabled: false, activeClass: "ui-state-highlight",
                                addClasses: false, hoverClass: "ui-drop-hover",
                                tolerance: "pointer"
                                };
                        if (attrs.jqyouiOptions)
                            angular.extend(dsettings, $scope.$eval(attrs.jqyouiOptions));
                        dsettings.drop = function(event, ui) {
                            var locals = { drop_event: event, drop_position: ui.position,
                                        drop_offset: ui.offset,
                                        dropElem: element, dragElem: angular.element(ui.draggable) };
                            locals.dragItem = locals.dragElem.scope()._dragItem;
                            if (dropFn($scope, locals)){
                                ui.helper.remove();
                                $scope.$apply();
                            }
                        };
                        var dscope = dsettings.scope;
                        delete dsettings.scope;
                        element.droppable(dsettings);
                        if (dscope)
                            element.setDroppableScope(dscope);
                    } else {
                        element.droppable({disabled: true});
                    }
                };
            
                $scope.$watch(function() { return $scope.$eval(attrs.ngDroppable); }, updateDroppable);
                updateDroppable();
                }
            };
            },
    };
}])
.directive('ngBlur', function() {
  return function( scope, elem, attrs ) {
    elem.bind('blur', function() {
      scope.$apply(attrs.ngBlur);
    });
  };
});


jQuery.fn.extend({
    setDroppableScope: function(scope) {
        return this.each(function() {
            var currentScope = $(this).droppable("option","scope");
            if (typeof currentScope == "object" && currentScope[0] == this) return true; //continue if this is not droppable

            //Remove from current scope and add to new scope
            var i, droppableArrayObject;
            for(i = 0; i < $.ui.ddmanager.droppables[currentScope].length; i++) {
                var ui_element = $.ui.ddmanager.droppables[currentScope][i].element[0];

                if (this == ui_element) {
                    //Remove from old scope position in jQuery's internal array
                    droppableArrayObject = $.ui.ddmanager.droppables[currentScope].splice(i,1)[0];
                    //Add to new scope
                    $.ui.ddmanager.droppables[scope] = $.ui.ddmanager.droppables[scope] || [];
                    $.ui.ddmanager.droppables[scope].push(droppableArrayObject);
                    //Update the original way via jQuery
                    $(this).droppable("option","scope",scope);
                    break;
                }
            }
        });
    }
});
//eof
