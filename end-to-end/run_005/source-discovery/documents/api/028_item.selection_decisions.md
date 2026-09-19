# Source-discovery selection decisions

This is the normalized content in its original document order with a source-discovery semantic overlay. The labels are annotations; the content beneath them remains the normalized source structure.

- **Green — SELECTED:** relevant, current material eligible for extraction.
- **Orange — SELECTED WITH UNCERTAINTY:** possibly relevant, time-bounded, or temporally unknown material that remains eligible for extraction.
- **Gray — HISTORICAL:** retained for audit but excluded from current terms.
- **Blue — FUTURE:** retained for audit but excluded from current terms.
- **White — NOT SELECTED / UNASSESSED:** unchanged content without an accepted current extraction decision.

---

## https://ameriabank.am/Portals/_default/skins/polo/ContentThemes/InspiroSlider/item.html?cdv=517

Source: <https://ameriabank.am/Portals/_default/skins/polo/ContentThemes/InspiroSlider/item.html?cdv=517>

<div style="border-left:5px solid #d0d5dd;background:#ffffff;padding:0.55em 0.8em;margin:1.2em 0 0.65em 0;"><strong>NOT SELECTED</strong> &nbsp; <code>api:18:cbf6f7c352ff</code><br><small>other · irrelevant · unknown · rule</small><br><small>Payload is a reusable HTML presentation template, not product data.</small></div>

<div style="border-left:5px solid #98a2b3;background:#ffffff;padding:0.55em 0.8em;margin:1.2em 0 0.65em 0;"><strong>UNASSESSED</strong> &nbsp; <code>api:18:cbf6f7c352ff:block:0</code><br><small>No source-discovery assessment was produced.</small></div>

&lt;div class=&quot;mng-item-{{:itemId}}&quot; style=&quot;display: table; width: 100%; height: 100%; {{if videoPath1 || videoYouTubeID}} background-image:url({{:~utils.getModuleImageUrl(image.resized)}});{{/if}}&quot;&gt;  
{{if videoPath1}}  
&lt;div class=&quot;slide {{:backgrOverlayType}}&quot; data-vide-bg=&quot;{{:~utils.getModuleImageUrl(videoPath1)}}&quot;&gt;  
{{else videoYouTubeID}}  
&lt;div class=&quot;slide youtube-background {{:backgrOverlayType}}&quot; data-youtube-autoplay=&quot;true&quot; data-youtube-mute=&quot;true&quot; data-youtube-url=&quot;http://youtu.be/{{:videoYouTubeID}}&quot;&gt;  
{{else}}  
&lt;div class=&quot;slide {{:backgrOverlayType}} background-image {{:~themeSettings.backgroundImageSetting}}&quot; style=&quot;background-image:url({{:~utils.getModuleImageUrl(image.resized)}});&quot;&gt;  
{{/if}}  
{{if backgrOverlayType == &quot;custom-overlay&quot;}}  
&lt;div class=&quot;custom-overlay&quot; style=&quot;background-color: {{:customOverlayColor}}; opacity: {{:customOverlayOpacity}};&quot;&gt;&lt;/div&gt;  
{{/if}}  
&lt;div class=&quot;container{{:contentWidth}}&quot;&gt;  
&lt;div class=&quot;{{:contentAlign}} slide-captions {{:contentColor}}&quot;&gt;  
{{if smallTitle}}  
&lt;span class=&quot;strong&quot; data-caption-animation=&quot;zoom-out&quot;&gt;  
&lt;a href=&quot;#&quot; class=&quot;business&quot;&gt;&lt;span&gt;{{&gt;smallTitle}}&lt;/span&gt;&lt;/a&gt;  
&lt;/span&gt;  
{{/if}}  
&lt;{{:headingLevel}}&gt;{{:title}}&lt;/{{:headingLevel}}&gt;  
&lt;p class=&quot;lead&quot;&gt;{{:description}}&lt;/p&gt;  
{{if buttonText1}}  
{{if buttonTypeStyle1 !== &#x27;btn-play&#x27;}}  
&lt;a {{if buttonLinkType1 == &quot;lightbox_link_type&quot;}} data-lightbox=&#x27;iframe&#x27; {{/if}}  
{{if buttonLinkType1 == &quot;new_window_link_type&quot;}} target=&#x27;_blank&#x27; {{/if}}  
href=&quot;{{:buttonURL1}}&quot;  
class=&quot;btn {{:buttonTypeStyle1}} {{:buttonIconHolder1}}&quot;&gt;  
{{if buttonIconHolder1 == &#x27;btn-icon-left&#x27;}}  
&lt;span class=&#x27;btn-label&#x27;&gt;&lt;i class=&#x27;{{:iconButton1}}&#x27;&gt;&lt;/i&gt;&lt;/span&gt;  
{{:buttonText1}}  
{{else}}  
{{:buttonText1}}  
{{if buttonIconHolder1 != &#x27;btn-icon-holder-off&#x27;}}&lt;span class=&#x27;btn-label&#x27;&gt;&lt;i class=&#x27;{{:iconButton1}}&#x27;&gt;&lt;/i&gt;&lt;/span&gt;{{/if}}  
{{/if}}  
&lt;/a&gt;  
{{else}}  
&lt;a href=&quot;{{:buttonURL1}}&quot; data-lightbox=&quot;iframe&quot; class=&quot;play-button&quot;&gt;&lt;i class=&quot;fa fa-play&quot;&gt;&lt;/i&gt;&lt;/a&gt;  
{{/if}}  
{{/if}}  
{{if buttonText2}}  
{{if buttonTypeStyle2 !== &#x27;btn-play&#x27;}}  
&lt;a {{if buttonLinkType2 == &quot;lightbox_link_type&quot;}} data-lightbox=&#x27;iframe&#x27; {{/if}}  
{{if buttonLinkType2 == &quot;new_window_link_type&quot;}} target=&#x27;_blank&#x27; {{/if}}  
href=&quot;{{:buttonURL2}}&quot;  
class=&quot;btn {{:buttonTypeStyle2}} {{:buttonIconHolder2}}&quot;&gt;  
{{if buttonIconHolder2 == &#x27;btn-icon-left&#x27;}}  
&lt;span class=&#x27;btn-label&#x27;&gt;&lt;i class=&#x27;{{:iconButton2}}&#x27;&gt;&lt;/i&gt;&lt;/span&gt;  
{{:buttonText2}}  
{{else}}  
{{:buttonText2}}  
{{if buttonIconHolder2 != &#x27;btn-icon-holder-off&#x27;}}&lt;span class=&#x27;btn-label&#x27;&gt;&lt;i class=&#x27;{{:iconButton2}}&#x27;&gt;&lt;/i&gt;&lt;/span&gt;{{/if}}  
{{/if}}  
&lt;/a&gt;  
{{else}}  
&lt;a href=&quot;{{:buttonURL2}}&quot; data-lightbox=&quot;iframe&quot; class=&quot;play-button&quot;&gt;&lt;i class=&quot;fa fa-play&quot;&gt;&lt;/i&gt;&lt;/a&gt;  
{{/if}}  
{{/if}}  
&lt;/div&gt;  
&lt;/div&gt;  
&lt;/div&gt;  
&lt;/div&gt;
