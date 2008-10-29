// Copyright (c) 2007-2008 gocept gmbh & co. kg
// See also LICENSE.txt
// $Id$

function setCookie(name, value, expires, path, domain, secure) {   
  var val = escape(value);
  cookie = name + "=" + val +
    ((expires) ? "; expires=" + expires.toGMTString() : "") +
    ((path) ? "; path=" + path : "") +
    ((domain) ? "; domain=" + domain : "") +
    ((secure) ? "; secure" : "");
  document.cookie = cookie;
}

function getCookie(name) {
  var dc = document.cookie;
  var prefix = name + "=";
  var begin = dc.indexOf("; " + prefix);
  if (begin == -1) {
    begin = dc.indexOf(prefix);
    if (begin != 0) return null;
  } else {
    begin += 2;
  }
  var end = document.cookie.indexOf(";", begin);
  if (end == -1) {
    end = dc.length;
  }
  return unescape(dc.substring(begin + prefix.length, end));
}


zeit.cms.PanelHandler = Class.extend({

    construct: function(base_url) {
        this.url = base_url + '/panel_handlers';
    },

    registerPanelHandlers: function() {
        var panels = getElementsByTagAndClassName('div', 'panel');
        this.resizePanels(panels);
        this.registerFoldHandlers(panels);
        connect('sidebar', 'panel-content-changed', this, 'resizeAllPanels');
        addElementClass('sidebar', 'sized');
    },

    resizeAllPanels: function() {
        signal('sidebar', 'zeit.cms.RememberScrollStateEvent');
        var panels = getElementsByTagAndClassName('div', 'panel');
        // Reset
        forEach(panels, function(panel) {
            var content_element = getFirstElementByTagAndClassName(
                'div', 'PanelContent', panel);
            setStyle(content_element, {'height': ''});
        });
        this.resizePanels(panels);
        signal('sidebar', 'zeit.cms.RestoreScrollStateEvent');
    },

    resizePanels: function(panels) {
        var max_height = $('sidebar').clientHeight;
        var fixed_space = 0;
        var flex_sum = 0;

        // Compute flex_sum and fixed_space
        forEach(panels, function(panel) {
            var content_element = getFirstElementByTagAndClassName(
                'div', 'PanelContent', panel);
            // XXX: getAttributeNS doesn't work :(
            var flex = panel.getAttribute('panel:flex');
            var fixed;
            if (flex) {
                panel._flex = new Number(flex);
                flex_sum += panel._flex;
                fixed = panel.clientHeight - content_element.clientHeight;
            } else {
                // A non flexible panel will not be shrunk
                fixed = panel.clientHeight;
            }
            log(panel.id, 'fixed =', fixed, 'flex =', flex);
            fixed_space += fixed;
        });

        // Fix up flex / fixed_space for not making panels larger than they'd
        // need to be
        var continue_ = true;
        while (continue_) {
            continue_ = false;
            log("Max height", max_height);
            log("Fixed space", fixed_space);
            var available_space = max_height - fixed_space;
            var space_per_flex = available_space / flex_sum;
            log("space per flex", space_per_flex);

            forEach(panels, function(panel) {
                var content_element = getFirstElementByTagAndClassName(
                    'div', 'PanelContent', panel);
                if (panel._flex) {
                    var new_height = panel._flex * space_per_flex;
                    if (new_height >= content_element.clientHeight) {
                        flex_sum -= panel._flex;
                        fixed_space += content_element.clientHeight;
                        panel._flex = null;
                        continue_ = true;
                        throw MochiKit.Iter.StopIteration;
                    }
                }
            });
        }

        // Finally set the sizes
        forEach(panels, function(panel) {
            var content_element = getFirstElementByTagAndClassName(
                'div', 'PanelContent', panel);
            if (panel._flex) {
                // compute padding and remove px from padding;
                // NOTE: this is quite expensive, maybe we can work around
                // calling getStyle somehow?
                var padding_top = getStyle(
                    content_element, 'padding-top').slice(0, -2);
                var padding_bottom = getStyle(
                    content_element, 'padding-bottom').slice(0, -2);
                var padding = (
                    new Number(padding_top) + new Number(padding_bottom));

                var height = panel._flex * space_per_flex - padding;
                log("Sizing", panel.id, "at", height, "flex =", panel._flex);
                setStyle(content_element, {'height': height + 'px'});
            }
        });
    },

    registerFoldHandlers: function(panels) {
        var handler = this;
        forEach(panels, function(panel) {
            var foldmarker = panel.getElementsByTagName('h1')[0];
            connect(foldmarker, "onclick", function(event) {
                if (event.target() != foldmarker) return;
                var new_state;
                if (hasElementClass(panel, 'folded')) {
                    removeElementClass(panel, 'folded');
                    addElementClass(panel, 'unfolded');
                } else {
                    removeElementClass(panel, 'unfolded');
                    addElementClass(panel, 'folded');
                }
                handler.resizeAllPanels();
                handler.storeState(panel.id);
            });
            var content_element = getFirstElementByTagAndClassName(
                'div', 'PanelContent', panel);
            var scroll_state = new zeit.cms.ScrollStateRestorer(
                content_element);
            scroll_state.connectWindowHandlers();
            connect(
                'sidebar', 'zeit.cms.RememberScrollStateEvent',
                scroll_state, 'rememberScrollState');
            connect(
                'sidebar', 'zeit.cms.RestoreScrollStateEvent',
                scroll_state, 'restoreScrollState');


        });

    },

    storeState: function(panel_id) {
        doSimpleXMLHttpRequest(this.url, {toggle_folding: panel_id});
    },

});



// Handler to close and open the sidebar making more space for the actual
// content area.

function SidebarDragger(base_url) {
    this.url = base_url + '/@@sidebar_toggle_folding';
    this.observe_ids = new Array('sidebar', 'sidebar-dragger', 
        'visualContentSeparator', 'visualContentWrapper', 'header');
}

SidebarDragger.prototype = {

    classes: ['sidebar-folded', 'sidebar-expanded'],
    
    toggle: function(event) {
        var dragger = this;
        var d = doSimpleXMLHttpRequest(this.url);
        d.addCallback(function(result) {
            var css_class = result.responseText;
            dragger.setClass(css_class);
        });
    },

    setClass: function(css_class) {
        var dragger = this;
        forEach(this.observe_ids,
            function(element_id) {
              forEach(dragger.classes, function(cls) {
                  var element = getElement(element_id);
                  removeElementClass(element, cls);
                  });
        var element = getElement(element_id);
        addElementClass(element, css_class);
        });
    },
}


zeit.cms.ScrollStateRestorer = Class.extend({

    construct: function(content_element) {
        this.content_element = $(content_element);
    },

    connectWindowHandlers: function() {
        var othis = this;
        this.restoreScrollState();
        connect(window, 'onunload', function(event) {
            othis.rememberScrollState();
        });
        connect(this.content_element, 'initialload', function(event) {
            if (event.src() == othis.content_element) {
                othis.restoreScrollState();
            }
        });
    },

    rememberScrollState: function(content_element) {
        var position = this.content_element.scrollTop;
        var id = this.content_element.id;
        if (!id) {
            return;
        }
        setCookie(id, position.toString(), null, '/');
     },

    restoreScrollState: function() {
        var id = this.content_element.id;
        if (!id) {
            return;
        }
        var position = getCookie(id);
        this.content_element.scrollTop = position;
    },

});
