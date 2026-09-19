# Source-discovery selection decisions

This is the normalized content in its original document order with a source-discovery semantic overlay. The labels are annotations; the content beneath them remains the normalized source structure.

- **Green — SELECTED:** relevant, current material eligible for extraction.
- **Orange — SELECTED WITH UNCERTAINTY:** possibly relevant, time-bounded, or temporally unknown material that remains eligible for extraction.
- **Gray — HISTORICAL:** retained for audit but excluded from current terms.
- **Blue — FUTURE:** retained for audit but excluded from current terms.
- **White — NOT SELECTED / UNASSESSED:** unchanged content without an accepted current extraction decision.

---

## https://ameriabank.am/DesktopModules/WebSitesCreative/MyContentManager/UI/templates.view.html?cdv=517

Source: <https://ameriabank.am/DesktopModules/WebSitesCreative/MyContentManager/UI/templates.view.html?cdv=517>

<div style="border-left:5px solid #d0d5dd;background:#ffffff;padding:0.55em 0.8em;margin:1.2em 0 0.65em 0;"><strong>NOT SELECTED</strong> &nbsp; <code>api:6:aa4e18dabff0</code><br><small>other · irrelevant · unknown · rule</small><br><small>Payload is a reusable HTML presentation template, not product data.</small></div>

<div style="border-left:5px solid #98a2b3;background:#ffffff;padding:0.55em 0.8em;margin:1.2em 0 0.65em 0;"><strong>UNASSESSED</strong> &nbsp; <code>api:6:aa4e18dabff0:block:0</code><br><small>No source-discovery assessment was produced.</small></div>

&lt;script id=&quot;wscMCMModule&quot; type=&quot;text/x-jsrender&quot;&gt;{{if !slides.length}}  
{{if ~isEditMode}}  
{{if ~initError}}  
Failed to load module. Server response: &lt;strong class=&#x27;error&#x27;&gt;{{:~initError}}&lt;/strong&gt;  
{{else}}  
&lt;a data-link=&quot;{on click ~moduleActions.onAddContentClick}&quot;&gt;Add content&lt;/a&gt; to the module  
{{/if}}  
{{/if}}  
{{else}}  
{{include tmpl=~template /}}  
{{/if}}  
{{if ~isEditMode}}  
{{include tmpl=&quot;wscMCMModuleActionPanel&quot; /}}  
{{/if}}&lt;/script&gt;  
&lt;script id=&quot;wscMCMTags&quot; type=&quot;text/x-jsrender&quot;&gt;&lt;div class=&quot;wsc_controls&quot;&gt;  
&lt;ul class=&quot;wsc_tags&quot;&gt;  
{{for tags}}  
&lt;li&gt;  
&lt;a&gt;{{:name}}&lt;/a&gt;  
&lt;span&gt;({{:count}})&lt;/span&gt;  
&lt;/li&gt;  
{{/for}}  
&lt;/ul&gt;  
&lt;/div&gt;  
&lt;/script&gt;
