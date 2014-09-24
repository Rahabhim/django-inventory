/* reports application w. Angular
 * 
 * Copyright (C) 2014 University of Athens pchristeas@noc.uoa.gr
 */

if (typeof String.prototype.startsWith != 'function') {
  String.prototype.startsWith = function (str){
    return this.slice(0, str.length) == str;
  };
}

    var reportsApp = angular.module('reportsApp', ['ui.bootstrap', 'f3.movable', 'f3.draggable'])
        .config(['$interpolateProvider', '$httpProvider', '$locationProvider',
                'datepickerConfig', 'datepickerPopupConfig', 'appCSRFtoken',
          function($interpolateProvider, $httpProvider, $locationProvider,
                    datepickerConfig, datepickerPopupConfig, appCSRFtoken) {
            $interpolateProvider.startSymbol('[[');
            $interpolateProvider.endSymbol(']]');
            $httpProvider.defaults.headers.post['X-CSRFToken'] = appCSRFtoken;
            $locationProvider.html5Mode(false);

            datepickerConfig.showWeeks = false;
            datepickerPopupConfig.showButtonBar = false;
        }]);
    reportsApp.controller('mainCtrl', ['$log', '$scope', '$location', '$http',
                        '$modal', '$filter', '$timeout', 'appSuperUser', 'appReportTypes',
        function($log, $scope, $location, $http, $modal, $filter, $timeout, appSuperUser, appReportTypes) {
            $scope.reportType = false;
            $scope.reportGroups = [];
            $scope.available_types = appReportTypes;
            $scope.show_warning = false;
            $scope.tabs = { 'type': true, 'params': false, 'format': false, 'preview': false, 'results': false };
            $scope.selectType = function(t, dblclick) {
                    if (! t.id)
                        return;
                    if ($scope.reportType && !dblclick){
                        $scope.show_warning = true;
                        $timeout(function() { $scope.show_warning = false;}, 5000);
                        return;
                    }
                    $scope.reportType = t;
                    $location.search('id'); // reset it
                    $scope.$root.can_delete = false;
                    $scope.reportGroups = [];
                    $timeout(function() { $scope.tabs.params = true; }, 1200);

                    if (!t.fields){
                        $log.debug("Must fetch grammar for", t.id);
                        $http.get('grammar/'+t.id).success(function(data) {
                                $log.debug("Grammar data:", data);
                                angular.extend(t, data);
                                if (t.show_detail === undefined)
                                    t.show_detail = true;
                            });
                        }
                };

            var date2iso = $filter('date2iso');
            var domainFns = {
                /* Domain functions return an expression part for some field
                
                  The expression part is like ['op', <rhs>]
                */
                'model' : function(rt) {
                        var dom = [];
                        angular.forEach(rt.fields, function(rt2, n2) {
                            var dfn = domainFns[rt2.widget];
                            if (dfn === undefined)
                                dfn = domainFns['model']
                            var dom2 = dfn(rt2, n2);
                            if (dom2 && dom2.length){
                                if (dom2[0] == '&') {
                                    angular.forEach(dom2[1], function(dom3) {
                                        if (angular.isArray(dom3) && dom3.length > 1)
                                            dom.push([n2,'in', dom3]);
                                        else
                                            dom.push([n2, '=',].concat(dom3));
                                        });
                                }
                                else if (dom2[0] == '&in') {
                                    angular.forEach(dom2[1], function(dom3) {
                                        if (dom3 && dom3.length)
                                            dom.push([n2, 'in', dom3]);
                                        });
                                }
                                else if (dom2[0] == '&*') {
                                    angular.forEach(dom2[1], function(dom3) {
                                        if (dom3) dom.push([n2, dom3[0], dom3[1]]);
                                        });
                                }
                                else
                                    dom.push([n2].concat(dom2)) ;
                                }
                            });
                        if ((dom.length == 1) && (dom[0][0] == '_'))
                            return [ '=', dom[0][2]];
                        if (dom.length)
                            return ['in', dom];
                        return false;
                    },
                'char': function(rt, name) {
                        if (rt.data)
                            return [rt.data_op || 'icontains', rt.data];
                    },
                'id': function(rt, name) {
                        if (rt.data)
                            $log.warning("Filter for id:", rt.data);
                    },
                'boolean': function(rt, name){
                        if (rt.data == 'true')
                            return [ '=', true];
                        else if (rt.data == 'false')
                            return ['=', false];
                    },
                'date': function(rt, name){
                        if(rt.data_op == 'between'){
                            return [ rt.data_op, [date2iso(rt.data[0]), date2iso(rt.data[1])]];
                        }
                        else if (rt.data_op && rt.data){
                            return [rt.data_op, date2iso(rt.data)];
                        }
                    },
                'lookup': function(rt, name) {
                        if (rt.data && rt.data_op == 'in'){
                            var vals = [];
                            angular.forEach(rt.data, function(d) {
                                if (d && d.pk)
                                    vals.push(parseInt(d.pk))
                            });
                            return [rt.data_op, vals];
                        }
                        else if (rt.data)
                            return [rt.data_op || '=', parseInt(rt.data.pk)];
                    },
                'selection': function(rt, name) {
                        if (rt.data)
                            return ['=', rt.data];
                    },
                'attribs': function(rt, name) {
                        if (!rt.data)
                            return;
                        $log.debug("Atribs=> dom:", rt);
                        var rval = [];
                        angular.forEach(rt.data, function(val) {
                                rval.push(val);
                            });
                        if (rval.length)
                            return ['&', rval];
                    },
                'attribs_multi': function(rt, name) {
                        if (!rt.data)
                            return;
                        var rval = [];
                        angular.forEach(rt.data, function(val) {
                                rval.push(val);
                            });
                        if (rval.length)
                            return ['&in', rval];
                    },
                'contains': function(rt, name) {
                        if (!rt.contains_data)
                            return;
                        var rdom = [];
                        angular.forEach(rt.contains_data, function(rt2) {
                            var dfn = domainFns[rt2.widget];
                            if (dfn === undefined)
                                dfn = domainFns['model']
                            var dom2 = dfn(rt2, name);
                            if (!(dom2 && dom2.length))
                                return;
                            if (dom2[0] == 'in' || dom2[0] == '='){
                                rdom.push(dom2[1]) ;
                            }
                            else if (dom2[0] == '&') {
                                angular.forEach(dom2[1], function(dom3) {
                                    rdom.push(dom3);
                                    });
                            }
                            else
                                $log.warn("Cannot use domain", dom2, "for", name);
                            });
                        return ['&', rdom];
                    },
                'isset': function(rt, name) {
                        if (rt.data){
                            if (rt.data == '0')
                                return ['=', false];
                            else
                                return ['=', true];
                        }
                    },
                'count': function(rt, name) {
                        if(rt.data && rt.data_op)
                            return [rt.data_op, rt.data];
                    },
                'attribs_count': function(rt, name) {
                        var ret = [];
                        angular.forEach(rt.data_op, function(op, key) {
                            if (rt.data[key])
                                ret.push([key, op, rt.data[key]]);
                            });
                        if (ret.length)
                            return ['in', ret];
                    },
                // Both "extra" fields don't limit the results, but
                // only add display fields.
                'extra_attrib': function (rt, name) { return []; },
                'extra_condition': function (rt, name) { return []; }
                };
            domainFns['model-product'] = domainFns['model'];
            domainFns['has_sth'] = domainFns['boolean'];
            $scope.getCurDomain = function(){
                if (!$scope.reportType)
                    return [];
                return domainFns['model']($scope.reportType);
                };
            $scope.getFieldDomain = function(field){
                var dfn = domainFns[field.widget];
                if (dfn)
                    return dfn(field);
            };
            /** Get field object by some dot-delimited path */
            $scope.fieldByPath = function(path, ffrom) {
                var ps = path.split('.');
                ps.reverse();
                var ret = ffrom || $scope.reportType;
                while(ps.length){
                    if (!ret.fields)
                        return;
                    ret = ret.fields[ps.pop()];
                    if (!ret) return;
                    }
                return ret;
                };

            /** Initialize formatting struct for field

                returns true if the struct was empty and had to be initialized
            */
            $scope.setFieldFmt = function(field) {
                if(!field.fmt){
                    field.fmt = {
                        title: field.name,
                        sequence: field.sequence,
                        order: false,
                        hide: false
                    };
                    return true;
                }
                else if (field.fmt.title === undefined)
                    field.fmt.title = field.name;
                return false;
                };

            var _getFieldData_one = function(field) {
                    var r = {};
                    if (field.data_op)
                        r['op'] = field.data_op;
                    if (field.data)
                        r['data'] = field.data;
                    if (field.fmt)
                        r['fmt'] = field.fmt;
                    if (field.fields)
                        r['fields'] = getFieldData(field.fields);
                    if (field.contains_data){
                        r['contains'] = [];
                        angular.forEach(field.contains_data, function(item){
                            r['contains'].push(_getFieldData_one(item));
                            });
                    }
                    if (field.path && field.path.startsWith('+')){
                        r['name'] = field.name;
                        r['full_name'] = field.full_name;
                        r['widget'] = field.widget;
                    }
                    return r;
                };
            var getFieldData = function(fields) {
                // extract the volatile field data from field.data
                var ret = {};
                angular.forEach(fields, function(field, key){
                    ret[key] = _getFieldData_one(field);
                    });
                return ret;
                };

            var _setFieldData_one = function(src, target){
                if (src.op)
                    target.data_op = src.op;
                if (src.data)
                    target.data = src.data;
                if (src.fmt)
                    target.fmt = src.fmt;
                if (src.fields)
                    setFieldData(src.fields, target.fields);
                if (src.contains){
                    target.contains_data = [];
                    angular.forEach(src.contains, function(item) {
                        var t_item = angular.copy(target.sub);
                        _setFieldData_one(item, t_item);
                        target.contains_data.push(t_item);
                        });
                    }
                };
            var setFieldData = function(fields, target){
                angular.forEach(fields, function(field, key){
                    if (target[key])
                        _setFieldData_one(field, target[key]);
                    else if (key.startsWith('+')){
                        var new_field = {name: field.name, full_name: field.full_name,
                                path: key, full_path: key,
                                widget: field.widget};
                        _setFieldData_one(field, new_field);
                        target[key] = new_field;
                        }
                    });
                };
            $scope.resetFieldData = function(field) {
                if (field.data_op)
                    field.data_op = undefined;
                field.data = undefined;
                if (field.fields)
                    angular.forEach(field.fields, $scope.resetFieldData);
                if (field.contains)
                    field.contains_data = [];
            };

            var _loadReport = function(rid) { 
                        $log.debug("Load report:", rid);
                        $http.get('back/load', {'params': {'id': rid}})
                            .success(function(data){
                                $log.debug("load data came:", data);
                                $scope.reportType = data.grammar;
                                var upd = {
                                        id: data.model,
                                        saved_id: data.id,
                                        public: data.public,
                                        title: data.title,
                                        notes: data.notes,
                                        show_detail: data.data.show_detail,
                                        limit: data.data.limit,
                                        preview_limit: data.data.preview_limit || 10
                                        };
                                if (upd.show_detail === undefined)
                                    upd.show_detail = true;
                                angular.extend($scope.reportType, upd);
                                $location.search('id', data.id);
                                $scope.reportGroups = data.data.groups || [];
                                $scope.fillFieldPaths();

                                setFieldData(data.data.fields, $scope.reportType.fields);
                                $scope.$root.needs_save = false;
                                $scope.$root.can_save = appSuperUser || !data.public;
                                $scope.$root.can_delete = true;
                                if ($scope.tabs.type){
                                    // switch tab to "params"
                                    $scope.tabs.type = false;
                                    $scope.tabs.params = true;
                                    }
                                })
                            .error(function(data, status, headers) {
                                    $log.debug("Load error:", data, status);
                                    $location.search('id');
                                    });
                    };

            $scope.$root.reportLoad = function() {
                var minst = $modal.open({
                    templateUrl: 'parts/file-load.html',
                    controller: ['reports', '$scope', function(reports, $scope) {
                            $scope.reports = reports;
                        }],
                    windowClass: 'load-dlg',
                    backdrop: 'static',
                    resolve: { 'reports': function() {
                        return $http.get('back/list')
                            .then(function(response){
                                if (response.status == 200)
                                    return response.data;
                                else{
                                    $log.error("list response:", response);
                                    throw Error(response.status);
                                    }
                                });
                            }
                        }});

                minst.result.then(_loadReport);
                };

            $scope.$root.reportSave = function() {
                var field_cols=[], groupped_fields={}, req_fields = [], order_by = [];
                _calc_result_fields($scope, req_fields, field_cols, groupped_fields, order_by);

                var stage2 = {'model': $scope.reportType.id,
                        'title': $scope.reportType.title || $scope.reportType.name,
                        'notes': $scope.reportType.notes,
                        'domain': $scope.getCurDomain(),
                        'fields': req_fields,
                        'show_detail': $scope.reportType.show_detail,
                        'group_by': $scope.reportGroups,
                        'limit': $scope.reportType.limit,
                        'field_cols': field_cols,
                        'groupped_fields': groupped_fields,
                        'order_by': order_by
                        };
                var minst = $modal.open({
                    templateUrl: 'parts/file-save.html',
                    controller: ['$scope', 'report', 'reportGroups', '$timeout',
                      function($scope, report, reportGroups, $timeout) {
                        $scope.has_btn = true;
                        $scope.message = '';
                        $scope.report = report;
                        $scope.reportGroups = reportGroups;
                        $scope.do_save = function() {
                            // serialize reportType + reportGroups into data for report
                            var ser = { 'title': $scope.report.title,
                                        'notes': $scope.report.notes,
                                        'model': $scope.report.id,
                                        'public': $scope.report.public || false,
                                        'data': {'groups': reportGroups,
                                                'fields': getFieldData($scope.report.fields),
                                                'show_detail': $scope.report.show_detail,
                                                'limit': $scope.report.limit,
                                                'preview_limit': $scope.report.preview_limit
                                                },
                                        'stage2': stage2
                                        };
                            if ($scope.report.saved_id)
                                ser['id'] = $scope.report.saved_id;
                            $scope.has_btn = false;
                            $http.post('back/save', ser)
                                .success(function(data) {
                                    $log.debug("Saved report:", data);
                                    $scope.message = 'OK';
                                    $scope.report.saved_id = data.id;
                                    $scope.$root.can_delete = true;
                                    $timeout($scope.$dismiss, 1000);
                                })
                                .error(function(data, status, headers) {
                                    $log.debug("Error:", data, status);
                                    if (status == 403)
                                        $scope.message = "Permission denied";
                                    else
                                        $scope.message = "Error: " + status;
                                    });
                            };
                        }],
                    windowClass: 'save-dlg',
                    backdrop: 'static',
                    resolve: { 'report': function() { return $scope.reportType; },
                                'reportGroups': function() { return $scope.reportGroups },
                        }});

                minst.result.then(function() { $log.debug("Modal closed!") });
                };
            $scope.$root.reportSaveCopy = function() {
                $scope.reportType.saved_id = undefined;
                if ($scope.reportType.title)
                    $scope.reportType.title += ' (copy)';
                return $scope.reportSave();
                };

            $scope.$root.reportDelete = function() {
                var minst = $modal.open({
                    templateUrl: 'parts/file-delete.html',
                    controller: ['report_id', '$scope', function(report_id, $scope) {
                            $scope.report_id = report_id;
                        }],
                    windowClass: 'delete-dlg',
                    backdrop: 'static',
                    resolve: { 'report_id': function() { return $scope.reportType.saved_id; }
                        }});

                minst.result.then(function(rid) {
                    if (rid)
                        $http.post('back/delete', {'id': rid, 'confirm': true})
                            .success(function() {
                                $scope.reportType = false;
                                $scope.reportGroups = false;
                                $scope.$root.can_delete = false;
                                $scope.$root.needs_save = false;
                                $scope.$root.can_save = true;
                                })
                            .error(function(data, status, headers) {
                                    $log.debug("Error:", data, status);
                                    });
                    });
                };
            $scope.$watch(function() { return $location.search().id; },
                function(report_id){
                    if ((!report_id) || (report_id === true))
                        return;
                    if (report_id == $scope.reportType.saved_id)
                        return;
                    _loadReport(report_id);
                });
            $scope.prepareResultsPost = angular.noop;
            
            var last_field_index = 0;
            var _fillFieldPaths = function(field, key){
                if (!field.full_path){
                    field.full_name = this.name_prefix + field.name;
                    field.full_path = this.fld_prefix + key;
                }
                if (field.fields)
                    angular.forEach(field.fields, _fillFieldPaths,
                            { name_prefix: field.full_name + ' / ',
                              fld_prefix: field.full_path+ '.'
                            });
                if (field.widget == 'contains')
                    angular.forEach(field.sub.fields, _fillFieldPaths,
                            { name_prefix: field.full_name + ' / ',
                              fld_prefix: field.full_path+ '.'
                            });
            };
            $scope.fillFieldPaths = function(){
                if (!$scope.reportType)
                    return;
                angular.forEach($scope.reportType.fields, _fillFieldPaths, {name_prefix: '', fld_prefix: ''});
            };
            $scope.add_extra_field = function(field){
                if (last_field_index == 0){
                    for(var key in $scope.reportType.fields)
                        if (key.startsWith('+')){
                            var idx = parseInt(key.split('_').pop());
                            if (idx >= last_field_index)
                                last_field_index = idx+1;
                        };
                }
                var newName = '+extra_' + last_field_index;
                last_field_index++;
                if ($scope.reportType.fields[newName])
                    throw Error('name conflict: ' + newName);
                field.path = field.full_path = newName;
                $scope.reportType.fields[newName] = field;
            };

        }]);

    reportsApp.controller('reportsTypeCtrl', ['$log', '$scope',function($log, $scope) {
            $log.debug("reportsTypeCtrl:", $scope);

            $scope.view_short = false;
            $scope.type_name = '?';
        }]);

    reportsApp.controller('paramsCtrl', ['$log', '$scope','$http', '$q', 'appWords',
        function($log, $scope, $http, $q, appWords) {
            $scope.field = false;
            $scope.$parent.$watch('reportType', function(rt){
                    $scope.field = rt;
                    if (rt)
                        $scope.$root.needs_save = true;
                    if (rt && !rt.saved_id)
                        $scope.$root.can_save = true;
                });

            var formatFns = {
                    'char': function(field) {
                        if (field.data)
                            return '"' +field.data.toString() + '"';
                        },
                    'boolean': function(field) {
                        if (field.data)
                            return appWords[field.data];
                        },
                    'id': function(field) {
                        // TODO
                        },
                    'has_sth': function(field) {
                        if (field.data)
                            return appWords[ 'has_' + field.data];
                        },
                    'date': function(field) {
                        if (field.data){
                            if (field.data_op == 'between')
                                return "@(" + field.data[0] + ", " + field.data[1] + ")";
                            else
                                return field.data_op + ' ' + field.data;
                            }
                        },
                    'model': function(field) {
                        var criteria = [];
                        angular.forEach(field.fields, function(fld, k) {
                            var c = $scope.formatParmsData(fld);
                            if (c)
                                criteria.push(fld.name +': ' + c);
                            });
                        if (criteria.length)
                            return '[' + criteria.join(', ') + ']';
                        },
                    'lookup': function(field) {
                        if (field.data && field.data_op == 'in'){
                            var vals = [];
                            angular.forEach(field.data, function(dt) {
                                if (dt && dt.pk)
                                vals.push(dt.repr);
                            });
                            return '[' + vals.join(' | ') + ']';
                        }
                        else if (field.data)
                            return field.data.repr;
                        },
                    'selection': function(field) {
                        if (field.data){
                            for(var i in field.selection)
                                if(field.selection[i][0] == field.data)
                                    return field.selection[i][1];
                            }
                        },
                    'attribs': function(field) {
                        var criteria = [];
                        angular.forEach(field.attribs, function(attr) {
                            var v = field.data[attr.aid];
                            if (!v)
                                return;
                            for(var i=0;i<attr.values.length; i++)
                                if (attr.values[i][0] == v)
                                    criteria.push(attr.name+'='+attr.values[i][1]);
                            });
                        if (criteria.length)
                            return criteria.join(',');
                        return "";
                        },
                    'attribs_multi': function(field) {
                        var criteria = [];
                        angular.forEach(field.attribs, function(attr) {
                            var varr = field.data[attr.aid];
                            if (!varr)
                                return;
                            var crit2 = [];
                            for(var o=0;o<varr.length;o++){
                                for(var i=0;i<attr.values.length; i++)
                                    if (attr.values[i][0] == varr[o])
                                        crit2.push(attr.values[i][1]);
                                }
                            if (crit2.length)
                                criteria.push(attr.name+'='+ crit2.join('/'))
                            });
                        if (criteria.length)
                            return criteria.join(',');
                        return "";
                        },
                    'contains': function(field) {
                            var criteria = [];
                            angular.forEach(field.contains_data, function(fld) {
                                var c = $scope.formatParmsData(fld);
                                if (c)
                                    criteria.push('+ ' + c);
                                });
                            if (criteria.length)
                                return criteria.join(', ');
                            return "";
                        },
                    'isset': function(field) {
                        if (field.data){
                            if (field.data == '0')
                                return "empty";
                            else
                                return "set";
                            }
                        return "";
                        },
                    'count': function(field) {
                        if (field.data && field.data_op)
                            return '' + field.data_op + field.data;
                        },
                    'attribs_count': function(field) {
                        var criteria = [];
                        angular.forEach(field.attribs, function(attr) {
                            var v = field.data[attr.aid];
                            var op = field.data_op[attr.aid];
                            if (!(v && op))
                                return;
                            criteria.push('SUM('+attr.name+') ' + op +' '+v);
                            });
                        if (criteria.length)
                            return criteria.join(',');
                        return "";
                        },
                    'extra_attrib': function(field) {
                        // it is only used for display
                        return field.fmt.title || "";
                        },
                    'extra_condition': function(field) {
                        // it is only used for display
                        return field.fmt.title || "";
                        }
                };
            formatFns['model-product'] = formatFns['model'];

            $scope.formatParmsData = function(field) {
                    var fn = formatFns[field.widget];
                    if (!fn)
                        $log.debug("No format function for", field.widget);
                    else
                        return fn(field);
                };

            $scope.addContains = function(field) {
                if (!field.contains_data)
                    field.contains_data = [];
                field.contains_data.push(angular.copy(field.sub));
                };
            $scope.removeContains = function(field, parent_field) {
                $log.debug("remove", field, "from", parent_field);
                var i = parent_field.contains_data.indexOf(field);
                if (i >= 0)
                    parent_field.contains_data.splice(i, 1);
                };

            $scope.getLookup = function(lookup, val) {
                return $http.get(lookup, {'params': {'term': val } })
                    .then(function(response) {
                        if (response.status == 200)
                            return response.data;
                        else
                            $log.error("lookup response:", response);
                            return [];
                        });
                };
            $scope.setItemContains = function() {}; // stub

            $scope.adapt_date = function(field){
                if (field.data_op == 'between' && !angular.isArray(field.data))
                    field.data = [field.data, ''];
                else if (field.data_op != 'between' && angular.isArray(field.data))
                    field.data = field.data[0];
                };

            $scope.selFieldMulti = function(field, di, index) {
                var sel = field.data[index];
                for(var i=0; i< field.data.length;)
                    if (field.data[i] && field.data[i].pk){
                        // count again, match by object identity
                        if (field.data[i] === sel)
                            di.i = i;
                        i++
                    }
                    else //remove empty entry
                        field.data.splice(i, 1);
                };
            $scope.addFieldMulti = function(field, di) {
                $log.debug("addFieldMulti", field);
                if (field.data_op != 'in' && field.data) {
                    var dd = field.data;
                    field.data = [];
                    field.data.push(dd);
                    field.data_op = 'in';
                    }
                else if (!field.data || ( di.i < field.data.length
                        && !(field.data[di.i] && field.data[di.i].pk)))
                    return; // don't allow adding a value, when current one is empty

                field.data.push({'value': "", 'repr': "", "pk": 0 });
                if (di)
                    di.i = field.data.length - 1;
                };
            $scope.rmFieldMulti = function(field, index, di) {
                if (field.data_op != 'in')
                    return;
                field.data.splice(index,1);
                if (field.data.length == 0) {
                    field.data_op = '=';
                    field.data = undefined;
                }
                else if (field.data.length == 1) {
                    field.data = field.data[0];
                    field.data_op = '=';
                }
                else if (di && di.i >= field.data.length)
                    di.i = field.data.length -1;
                };

            $scope.refreshCatData = function(cat_data, attr_field, setItemContains) {
                /** Called when a products-category value is changed
                    
                    Refreshes the grammar of attributes, calls setItemContains()
                    with allowed categories for child items
                */
                if (cat_data && cat_data.pk) {
                        // Avoid http get if we close/open the attributes node.
                        // But this will still need to be set at the beginning
                    if (attr_field.cat_pk == cat_data.pk)
                        return $q.reject('no change');

                    var old_data = attr_field.data;
                    return $http.get('./cat-grammar/'+cat_data.pk).then(function(response) {
                        if (response.status == 200){
                            var d = response.data;
                            if (attr_field && d.attributes && d.attributes.length){
                                attr_field.hide = false;
                                attr_field.attribs = d.attributes;
                                attr_field.data = {};
                                attr_field.cat_pk = cat_data.pk;
                                if (old_data)
                                    angular.forEach(d.attributes, function(attr){
                                        if (old_data[attr.aid])
                                            attr_field.data[attr.aid] = old_data[attr.aid];
                                        });
                            }
                            return d;
                        }
                        else
                            $log.warn("Bad http response:", response);
                        });
                } else {
                    /* no category selected, cleanup attributes and sibling "containing" */
                    if (attr_field){
                        attr_field.hide = true;
                        attr_field.data = false;
                        attr_field.cat_pk = false;
                        }
                    return $q.when(false);
                }
            };

            $scope.addAsField = function(field) {
                // Get domain, if domain then add
                var dom = $scope.getFieldDomain(field);
                if (!field.full_path)
                    throw Error("no full path for field");
                if (dom && (dom != [])){
                    dom.unshift(field.full_path);
                    var new_field = {name: field.name + ' ?',
                        full_name: field.full_name,
                        data: dom,
                        widget: 'extra_condition',
                        sequence: 100};
                    $scope.setFieldFmt(new_field);
                    var ft = $scope.formatParmsData(field);
                    if (ft)
                        new_field.fmt.title = ft;
                    $scope.$parent.add_extra_field(new_field);
                    $scope.resetFieldData(field);
                }
            };
            $scope.addAttribAsField = function(field, attr) {
                // direct add
                var new_field = {name: attr.name,
                        full_name: field.full_name + '/' + attr.name,
                        data: [field.full_path, attr.aid],
                        widget: 'extra_attrib',
                        sequence: 100};
                $scope.setFieldFmt(new_field);
                new_field.title = $scope.formatParmsData(field) || field.title;
                $scope.$parent.add_extra_field(new_field);
            };
        }]);

    reportsApp.controller('productParamsCtrl', ['$log', '$scope', function($log, $scope) {
            // $log.debug("productParamsCtrl:", $scope);

            $scope.$watch('field.fields.category.data', function(cat_data) {
                $scope.refreshCatData(cat_data, $scope.field.fields.attributes)
                    .then(function(data) {
                        if (data && (data.is_group || data.is_bundle))
                            $scope.$parent.setItemContains(data.may_contain);
                        else
                            $scope.setItemContains(false);
                    });
            });
        }]);
    reportsApp.controller('attribsCtrl', ['$log', '$scope', function($log, $scope) {
            $scope.cur_edit = -1;
            $scope.new_item = false;
            if (!angular.isArray($scope.$parent.field.data[$scope.$parent.attr.aid]))
                    $scope.$parent.field.data[$scope.$parent.attr.aid] = [];

            $scope.$parent.$watchCollection('field.data[attr.aid]', function(adata) {
                $scope.data = adata;
                if ($scope.cur_edit < 0) // shortcut, avoid processing twice
                    return;
                // triggered when selection changes, items are added or removed
                for(var i=0;i<adata.length;i++)
                    if (!adata[i])
                        adata.splice(i--,1); // cleanup empty values (in place)
                $scope.cur_edit = -1;
                });
            $scope.$watch('new_item', function() {
                    if (!$scope.new_item)
                        return;

                    $scope.data.push($scope.new_item);
                    $scope.new_item = false;
                    $scope.cur_edit = -1;
                });

            /** list the possible values /except/ for those in sibling array positions
            */
            $scope.remainingValues = function(data, index){
                var ret = [];
                angular.forEach($scope.attr.values, function(av){
                    if (angular.isArray(data)){
                        var idx = data.indexOf(av[0]);
                        if ((idx >= 0) && (idx != index))
                            return;
                        }
                    ret.push(av);
                    });
                return ret;
            }
            $scope.visibleName = function(value, options) {
                for(var i=0; i<options.length; i++)
                    if (options[i][0] == value)
                        return options[i][1];
                $log.warn("oops, no value", value, "in", options);
                return value; // fallback, return at least the numeric value
            };
            $scope.setCurEdit = function(idx){
                // ensure we are working on this particular scope
                $scope.cur_edit = idx;
            };
        }]);

    reportsApp.controller('attribsCountCtrl', ['$log', '$scope', function($log, $scope) {
            for(var s=$scope.$parent; s && s.field === $scope.field; s=s.$parent);
            $scope.attribs = [];
            if (!$scope.field.data)
                $scope.field.data = {};
            if (!$scope.field.data_op)
                $scope.field.data_op = {};
            var watch_expr = 'field.fields.'+$scope.field.sub_path +'.fields.'+$scope.field.cat_path + '.data';
            s.$watch(watch_expr, function(cat_data) {
                    var attr_field = s.field.fields[$scope.field.sub_path].fields[$scope.field.attribs_path];
                    s.refreshCatData(cat_data, attr_field)
                        .then(function(data) {
                            $scope.field.attribs = attr_field.attribs || [];
                        });
                });
            s.$watch('field.fields.'+$scope.field.sub_path +'.fields.'+$scope.field.attribs_path, function(){
                    $scope.field.attribs = s.field.fields[$scope.field.sub_path].fields[$scope.field.attribs_path].attribs || [];
                    });
            }]);

    reportsApp.controller('formattingCtrl', ['$log', '$scope',function($log, $scope) {
            $scope.fmtTable = false;
            var recalcFmtTable = function() {
                $scope.fmtTable = [];
                if (!$scope.reportType.fields)
                    return;
                angular.forEach($scope.reportType.fields, function(field, key) {
                        if ($scope.setFieldFmt(field)) {
                            if (field.fields && field.fields['name'])
                                field.fmt.display = 'name';
                        }
                        if ($scope.reportGroups.indexOf(field.full_path) == -1)
                            $scope.fmtTable.push(field);
                        if (field.fmt.sub_fields)
                            angular.forEach(field.fmt.sub_fields, function(sf_name) {
                                var field2 = $scope.fieldByPath(sf_name, field);
                                if (field2 && ($scope.reportGroups.indexOf(field2.full_path) == -1))
                                    $scope.fmtTable.push(field2);
                                });
                    });
                };
            var recalcFmtTable_full = function() {
                if (!$scope.reportType)
                    return;
                $scope.$parent.fillFieldPaths();
                recalcFmtTable();
                };
            $scope.$parent.$watchCollection('reportType.fields', recalcFmtTable_full);
            $scope.$parent.$watchCollection('reportGroups', recalcFmtTable);

            $scope.addGroup = function(dragItem) {
                    $log.debug("addGroup", dragItem, "to", $scope.reportGroups);
                    var grp_idx = $scope.reportGroups.indexOf(dragItem.full_path)
                    if (grp_idx >=0){
                        // move to bottom of groupping
                        $scope.reportGroups.splice(grp_idx, 1);
                    }
                    /* TODO: check that parents of this field are not already in groups */
                    $scope.reportGroups.push(dragItem.full_path);
                    return true;
                };
            $scope.get_fmt_fields = function(field) {
                    var ret = [];
                    if (field.fmt)
                        angular.forEach(field.fmt.sub_fields, function(sfn) {
                            ret.push($scope.fieldByPath(sfn, field));
                        });
                    ret.sort(function(a,b) {
                            return (a.fmt.sequence - b.fmt.sequence)
                            || (a.sequence - b.sequence);
                        });
                    return ret;
                };

            var _calc_qmd_from = function(field, mto, qmd) {
                    if (field.fmt) {
                        if (field.sequence >= mto)
                            qmd.push(field);
                        if (field.fmt.sub_fields)
                            angular.forEach(field.fmt.sub_fields, function(sf_name) {
                                var field2 = $scope.fieldByPath(sf_name, field);
                                if (field2)
                                    _calc_qmd_from(field2, mto, qmd);
                                });
                    }
                    else if (field.sequence >= mto) {
                        qmd.push(field);
                    }
                };

            var _arrange_fields = function(new_field, qmd, m_orig){
                var mfrom = m_orig, mto = m_orig+1;
                while(mfrom < mto){
                    for(var i=0; i< qmd.length; i++){
                        if (qmd[i] === undefined) continue;
                        var seq;
                        if (qmd[i].fmt)
                            seq = qmd[i].fmt.sequence;
                        else
                            seq = qmd[i].sequence;

                        if (seq == mfrom){
                            $scope.setFieldFmt(qmd[i]);
                            qmd[i].fmt.sequence = mto;
                            qmd[i] = undefined; // don't touch that again
                            mto ++;
                            break;
                        }
                    }
                    mfrom ++;
                }
                $scope.setFieldFmt(new_field);
                new_field.fmt.sequence = m_orig;
            };

            $scope.addToGroup = function(grp_field, dragItem, fld_after){
                if (!dragItem)
                    return;
                if (!dragItem.full_path.startsWith(grp_field.full_path+'.'))
                    return false;
                var rem_path = dragItem.full_path.slice(grp_field.full_path.length+1);
                $scope.setFieldFmt(grp_field);
                if (!grp_field.fmt.sub_fields)
                    grp_field.fmt.sub_fields = [];

                var m_orig = 1;
                var qmd = [];
                if (fld_after){
                    if (fld_after.fmt)
                        m_orig = fld_after.fmt.sequence;
                    else
                        m_orig = fld_after.sequence;
                    m_orig ++;
                }
                _calc_qmd_from(grp_field, m_orig, qmd);

                var i = grp_field.fmt.sub_fields.indexOf(rem_path);
                if (i == -1){
                    if (dragItem.fmt && dragItem.fmt.hide)
                        dragItem.fmt.hide = false;
                    grp_field.fmt.sub_fields.push(rem_path);
                    _arrange_fields(dragItem, qmd, m_orig);
                }
                else if (i > 0){
                    // move field before some others.
                    _arrange_fields(dragItem, qmd, m_orig);
                }
                else
                    return false;

                recalcFmtTable();
                return true;
            };

            $scope.addToField = function(dragItem, fld_after) {
                if (!dragItem)
                    return false;
                if (dragItem.full_path.indexOf('.') != -1)
                    // a sub_field can only be appended to its parent field
                    return $scope.addToGroup(fld_after, dragItem);

                if (dragItem.fmt && dragItem.fmt.hide)
                        dragItem.fmt.hide = false;

                var grp_idx = $scope.reportGroups.indexOf(dragItem.full_path);
                if (grp_idx != -1)
                    $scope.reportGroups.splice(grp_idx, 1);
                // now, rearrange sequence of fields
                var m_orig = 1;
                var qmd = [];
                if (fld_after){
                    if (fld_after.fmt)
                        m_orig = fld_after.fmt.sequence;
                    else
                        m_orig = fld_after.sequence;
                    m_orig ++;
                }
                angular.forEach($scope.reportType.fields, function(field) {
                    _calc_qmd_from(field, m_orig, qmd);
                    });
                _arrange_fields(dragItem, qmd, m_orig);
                recalcFmtTable();
                return true;
                };
        
            $scope.removeField = function(dragItem) {
                    if (!dragItem)
                        return;
                    var grp_idx = $scope.reportGroups.indexOf(dragItem.full_path);
                    if (grp_idx >= 0) {
                        $scope.reportGroups.splice(grp_idx, 1);
                    }
                    else if (dragItem.full_path.indexOf('.') >= 0){
                        // it must be a sub-field, find its parent and remove
                        // from there
                        var fp2 = dragItem.full_path.split('.');
                        var name_p = [];
                        while(fp2.length > 1) {
                            name_p.unshift(fp2.pop());
                            var parent = $scope.fieldByPath(fp2.join('.'));
                            if (! parent)
                                break;
                            if (!(parent.fmt && parent.fmt.sub_fields))
                                continue;
                            var fidx = parent.fmt.sub_fields.indexOf(name_p.join('.'));
                            if (fidx >= 0){
                                parent.fmt.sub_fields.splice(fidx, 1);
                                recalcFmtTable();
                                return true;
                                }
                        }
                        return false;
                    }
                    else if (dragItem.path && dragItem.path.startsWith('+')) {
                        delete $scope.reportType.fields[dragItem.path];
                    }
                    else {
                        // not groupped, just hide the field
                        $scope.setFieldFmt(dragItem);
                        dragItem.fmt.hide = true;
                    }
                    recalcFmtTable();
                    return true;
                };
        }]);

    var _calc_result_fields = function($scope,
                                req_fields, field_cols, groupped_fields, order_by ){
            var calc_get_fields = function(field, key) {
                if (field.hide || (field.widget == 'isset'))
                    return;
                var req2 = this.req;
                // ggroup is where the field shall be displayed,
                // may be empty for non-visible sub-fields
                var ggroup = this.ggroup;
                if (true){
                    // see if field logically belongs to any of the groups
                    for(var i in $scope.reportGroups)
                        if(field.full_path.startsWith($scope.reportGroups[i])){
                            if (field.full_path == $scope.reportGroups[i])
                                req2 = true;
                            if (!groupped_fields[i])
                                groupped_fields[i] = [];
                            ggroup = groupped_fields[i];
                            $scope.setFieldFmt(field);
                            break;
                        }
                }
                if (req2 && field.fmt){
                    var disp = field.full_path;
                    var order = undefined;
                    if (field.fmt.display)
                        disp += '.' + field.fmt.display;
                    if (!field.fmt.hide){
                        if (field.path && field.path.startsWith('+'))
                            req_fields.push([field.path, field.widget, field.data]);
                        else
                            req_fields.push(disp);
                    }
                    if (field.fmt.order){
                        if (field.fmt.order == '-')
                            order = '-' + disp;
                        else
                            order = disp;
                    }
                    if (ggroup && !field.fmt.hide)
                        ggroup.push({id: disp,
                            name: field.fmt.title || field.name,
                            widget: field.widget,
                            order: order,
                            group_mode: field.fmt.group_mode,
                            sequence: field.fmt.sequence || field.sequence});
                }

                if (field.fields)
                    angular.forEach(field.fields, function(field2, sf_name) {
                        var b = {req:false, ggroup: ggroup};
                        if (field.fmt && field.fmt.sub_fields
                                && (field.fmt.sub_fields.indexOf(sf_name) >=0))
                            b.req = true;
                        angular.bind(b, calc_get_fields)(field2, sf_name);
                        });
                };

            angular.forEach($scope.reportType.fields, calc_get_fields,
                            {req: true, ggroup: field_cols});

            field_cols.sort(function(a, b) { return a.sequence - b.sequence; });
            for (var i in $scope.reportGroups){
                var grp_order = [];
                angular.forEach(groupped_fields[i], function(field) {
                    if (field.order)
                        grp_order.push(field);
                    });
                if (grp_order.length){
                    grp_order.sort(function(a, b) { return a.sequence - b.sequence; });
                    angular.forEach(grp_order, function(g) { order_by.push(g.order);});
                }
            }
            angular.forEach(field_cols, function(field) {
                    if (field.order)
                        order_by.push(field.order);
                    });
        };

    reportsApp.controller('previewCtrl', ['$log', '$scope', '$http', '$timeout', '$sce',
        function($log, $scope, $http, $timeout, $sce) {
            $scope.wait_results = true;
            $scope.result_status = 0;
            $scope.result_alert = false;
            $scope.cur_domain = '?';
            $scope.results = false;

            var fetchResults = function(show) {
                $scope.wait_results = true;
                $scope.result_status = 0;
                $scope.result_alert = false;
                $scope.results = false;
                $scope.field_cols = [];
                $scope.groupped_fields = {};
                $scope.order_by = [];
                $scope.group_level = 0;
                $scope.rowsFilter = function() { return true; };

                if (!(show && $scope.reportType)){
                    return;
                }

                $scope.cur_domain = $scope.$parent.getCurDomain();
                var req_fields = [];
                _calc_result_fields($scope,
                                req_fields, $scope.field_cols, $scope.groupped_fields,
                                $scope.order_by);


                $http.post('./results-preview/' + $scope.reportType.id,
                        {'model': $scope.reportType.id,
                        'domain': $scope.cur_domain,
                        'fields': req_fields,
                        'show_detail': $scope.reportType.show_detail,
                        'group_by': $scope.reportGroups,
                        'order_by': $scope.order_by,
                        'limit': $scope.reportType.preview_limit || 10
                        }
                    )
                    .success(function(data) {
                        // $log.debug("Preview data came:", data);
                        $scope.wait_results = false;
                        if (data.count !== undefined){
                            $scope.results = [{'group_level': 0, _count: data.count},
                                        {'group_level': 1, 'group_by': false,
                                        'values': data.results }];
                        } else {
                            $scope.results = data;
                        }
                        //  $log.debug("Results:", $scope.results);
                    })
                    .error(function(data, status, headers) {
                        $scope.wait_results = false;
                        $scope.result_status = status;
                        $scope.result_alert = $sce.trustAsHtml(data);
                        });
                };
            $scope.$parent.$watch('tabs.preview', fetchResults);
        }]);

    reportsApp.controller('previewGroupedCtl', ['$scope', '$log', '$filter', 'appWords',
        function($scope, $log, $filter, appWords) {
            // Must be kept minimal, we will have many instances of this ctrl.
            $scope.group_level = $scope.$parent.group_level + 1;
            $scope.cur_results = $scope.$parent.results[$scope.group_level];
            var right_cols = false;
            if ($scope.cur_results && $scope.cur_results.group_by){
                var field = $scope.fieldByPath($scope.reportGroups[$scope.$parent.group_level]);
                if (field)
                    $scope.group_mode = field.fmt.group_mode || 'row';
                else
                    $scope.group_mode = 'table';
            }
            else
                $scope.group_mode = false;

            if ($scope.$parent.cur_group){
                var group_filter = {};
            
                angular.forEach($scope.$parent.cur_results.group_by, function(group_by){
                        group_filter[group_by] = $scope.$parent.cur_group[group_by];
                    });
                // $log.debug("group_filter:", group_filter);

                $scope.rowsFilter = function(row) {
                    for(var k in group_filter){
                        if(row[k] != group_filter[k])
                            return false;
                    }
                    return true;
                };
            }

            if ($scope.group_mode == 'left_col'){
                var ret = [];
                var seqSortFilter = $filter('seqSort');
                for(var i=$scope.group_level; i<= $scope.$parent.results.length;i++) {
                    var cur_results = $scope.$parent.results[i+1];
                    if (cur_results && cur_results.group_by) {
                        var field = $scope.fieldByPath($scope.reportGroups[i]);
                        if (field && field.fmt){
                            if (field.fmt.group_mode == 'table'){
                                angular.forEach(seqSortFilter($scope.groupped_fields[i]),
                                  function(fc) {
                                    if (fc.display_name === undefined){
                                        if (fc.name == '-')
                                            fc.display_name = '';
                                        else
                                            fc.display_name = fc.name;
                                    }
                                    ret.push(fc);
                                    });
                                ret.push({ 'id': '_count', 'display_name': appWords['count']});
                            }
                            else if (field.fmt.group_mode == 'left_col'){
                                var fc = $scope.groupped_fields[i][0];
                                if (fc.display_name === undefined){
                                    if (fc.name == '-')
                                        fc.display_name = '';
                                    else
                                        fc.display_name = fc.name;
                                }
                                ret.push(fc);
                                continue;
                            }
                            else {
                                // row mode, insert an empty cell
                                ret.push({'id': '_results'});
                            }
                        }
                        // everything else (row, no fmt) shall not render fields
                        break;
                    }
                    else if (cur_results) {
                        //detailed results
                        angular.forEach($scope.field_cols, function(fc) {
                            if (fc.display_name === undefined){
                                if (fc.name == '-')
                                    fc.display_name = '';
                                else
                                    fc.display_name = fc.name;
                            }
                            ret.push(fc);
                        });
                    }
                }
                $log.debug("getRightColumns:", ret);
                $scope.right_cols = ret;
            } else
                $scope.right_cols = [];
        }]);

    reportsApp.controller('resultCtrl', ['$log', '$scope','$timeout', function($log, $scope, $timeout) {
            /* results_form is a regular html element (NOT angular form), which
                we update in a traditional JS way and then trigger its "submit"
            */
            var num_submit = 0;
            $scope.rfpost_json = '';

            var _update_actionStrings = function() {
                angular.forEach($(".result-types form"), function(form) {
                    var i = form.action.lastIndexOf('?');
                    if (i >0) {
                        form.action = form.action.substr(0, i);
                    }
                    form.action += '?';
                    if ($scope.reportType && $scope.reportType.saved_id)
                        form.action += 'id=' + $scope.reportType.saved_id + '&';
                    form.action += 'n=' + num_submit.toString();
                    });
            };

            $scope.$parent.prepareResultsPost = function() {
                if (!$scope.reportType)
                    return;
                var field_cols=[], groupped_fields={}, req_fields = [], order_by = [];
                _calc_result_fields($scope, req_fields, field_cols, groupped_fields, order_by);

                var data = {'model': $scope.reportType.id,
                        'title': $scope.reportType.title || $scope.reportType.name,
                        'notes': $scope.reportType.notes,
                        'domain': $scope.$parent.getCurDomain(),
                        'fields': req_fields,
                        'show_detail': $scope.reportType.show_detail,
                        'group_by': $scope.reportGroups,
                        'order_by': order_by,
                        'limit': $scope.reportType.limit,
                        'field_cols': field_cols,
                        'groupped_fields': groupped_fields
                        }
                $scope.rfpost_json = angular.toJson(data);
                _update_actionStrings();
                return true;
                };
            $scope.countSubmit = function() {
                num_submit++;
                _update_actionStrings();
            };
        }]);

    /* We need an explicit sort filter, because our input is an object, rather than
        an array. Then, we hard-code the 'sequence' criterion
    */
    reportsApp.filter('seqSort', ['$log', function($log) {
        return function(input, full_hide){
            if (!input)
                return [];

            var ret = [];
            angular.forEach(input, function(f) {
                if (f.hide)
                    return;
                if (full_hide && f.fmt && f.fmt.hide)
                    return;
                ret.push(f);
                });
            ret.sort(function(a, b) {
                if ((a.fmt !== undefined) && (b.fmt !== undefined))
                    return (a.fmt.sequence - b.fmt.sequence);
                return a.sequence - b.sequence 
                });
            return ret;
        }
    }]);

    reportsApp.filter('hiddenOnly', function() {
        return function(input, full_hide){
            if (!input)
                return [];
            var ret = [];
            angular.forEach(input, function(f) {
                if (f.hide || (f.fmt && f.fmt.hide))
                    ret.push(f);
                });
            return ret;
            }
        });

    reportsApp.filter('seqCount', ['$log', function($log) {
        return function(input, more){
            if (!input)
                return [];

            var ret = 0;
            angular.forEach(input, function(f) {
                if (f.hide)
                    return;
                ret ++;
                });
            if (more)
                ret += more;
            return ret;
        }
    }]);

    reportsApp.filter('fmtBool', ['appWords', function(appWords) {
        return function(value){
            return appWords[value];
        };
    }]);
    reportsApp.filter('fmtHasSth', ['appWords', function(appWords) {
        return function(value){
            return appWords['has_' + value];
        };
    }]);

    reportsApp.filter('fmtAutoField', [ 'appWords', '$filter', '$sce', function(appWords, $filter, $sce) {
        var dateFilter = $filter('date');
        return function(data, field){
            var value = data[field.id];
            if (field.id[0] == '+')
                value = data[field.id.substr(1)];
            if (field.widget == 'boolean')
                return appWords[value];
            else if (field.widget == 'has_sth')
                return appWords['has_' + value];
            else if (field.widget == 'date')
                return dateFilter(value, 'dd/MM/yyyy');
            /*else if (field.widget == 'id'){
                return $sce.trustAsHtml(data);
            }*/
            else if (field.widget == 'extra_condition'){
                return appWords[value];
            }
            else if (field.widget == 'extra_attrib') {
                return value;
            }
            else
                return value;
        };
    }]);

    reportsApp.filter('date2iso', ['$filter', function($filter) {
        var dateFilter = $filter('date');
        return function(d) {
            if (angular.isDate(d))
                // an ISO string would convert the date to UTC, and could show a different
                // day than current locale. We ignore the locale and send the date as-is
                return dateFilter(d, 'yyyy-MM-dd');
            else
                return d;
            };
        }]);

/* eof */
