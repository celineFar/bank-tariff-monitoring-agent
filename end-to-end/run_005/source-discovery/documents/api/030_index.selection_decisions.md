# Source-discovery selection decisions

This is the normalized content in its original document order with a source-discovery semantic overlay. The labels are annotations; the content beneath them remains the normalized source structure.

- **Green — SELECTED:** relevant, current material eligible for extraction.
- **Orange — SELECTED WITH UNCERTAINTY:** possibly relevant, time-bounded, or temporally unknown material that remains eligible for extraction.
- **Gray — HISTORICAL:** retained for audit but excluded from current terms.
- **Blue — FUTURE:** retained for audit but excluded from current terms.
- **White — NOT SELECTED / UNASSESSED:** unchanged content without an accepted current extraction decision.

---

## https://ameriabank.am/Portals/_default/skins/polo/ContentThemes/Tabs/index.html?cdv=517

Source: <https://ameriabank.am/Portals/_default/skins/polo/ContentThemes/Tabs/index.html?cdv=517>

<div style="border-left:5px solid #d0d5dd;background:#ffffff;padding:0.55em 0.8em;margin:1.2em 0 0.65em 0;"><strong>NOT SELECTED</strong> &nbsp; <code>api:20:f52ad4869f3e</code><br><small>other · irrelevant · unknown · rule</small><br><small>Payload is a reusable HTML presentation template, not product data.</small></div>

<div style="border-left:5px solid #98a2b3;background:#ffffff;padding:0.55em 0.8em;margin:1.2em 0 0.65em 0;"><strong>UNASSESSED</strong> &nbsp; <code>api:20:f52ad4869f3e:block:0</code><br><small>No source-discovery assessment was produced.</small></div>

&lt;style type=&quot;text/css&quot;&gt;  
.tabs{{:~moduleId}} + .wsc_module_actions_panel {z-index: 10;}  
.tabs{{:~moduleId}} .tabs-content&gt;.tab-pane:not(.active),  
.edit .wsc_cm_module_container .tabs{{:~moduleId}} .tabs-content&gt;.tab-pane:not(.active) { display: none !important;}  
&lt;/style&gt;  
{{wscSlidesContainer}}  
&lt;div class=&quot;tabs {{&gt;~themeSettings.alignment}} {{&gt;~themeSettings.style}} tabs{{:~moduleId}} {{&gt;~themeSettings.topBottom}} {{&gt;~themeSettings.verticalTabs}}&quot;&gt;  
&lt;ul class=&quot;tabs-navigation&quot;&gt;  
{^{for slides}}  
&lt;li class=&quot;{{if ~themeSettings.activeTab == #index + 1}}active{{/if}} {{:~utils.replaceCommaToSpace(visibility)}}&quot;&gt;  
&lt;a href=&quot;#Tab{{:#index + 1}}_{{:~moduleId}}&quot;&gt;  
{{if titleIcon}}&lt;i class=&quot;{{:titleIcon}}&quot;&gt;&lt;/i&gt;{{/if}}  
{{:caption}}  
&lt;/a&gt;  
&lt;/li&gt;  
{{/for}}  
&lt;/ul&gt;  
&lt;div class=&quot;tabs-content&quot;&gt;  
{^{for slides}}  
{{wscSlide type=&#x27;Tabs&#x27; tag=&#x27;div&#x27; id=&#x27;Tab&#x27; + (#index + 1) + &#x27;_&#x27; + ~moduleId className=~themeSettings.activeTab == #index + 1 ? &#x27;tab-pane active&#x27; : &#x27;tab-pane&#x27; /}}  
{{/for}}  
&lt;/div&gt;  
&lt;/div&gt;  
{{/wscSlidesContainer}}
