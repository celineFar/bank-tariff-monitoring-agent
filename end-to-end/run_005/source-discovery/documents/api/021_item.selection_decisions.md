# Source-discovery selection decisions

This is the normalized content in its original document order with a source-discovery semantic overlay. The labels are annotations; the content beneath them remains the normalized source structure.

- **Green — SELECTED:** relevant, current material eligible for extraction.
- **Orange — SELECTED WITH UNCERTAINTY:** possibly relevant, time-bounded, or temporally unknown material that remains eligible for extraction.
- **Gray — HISTORICAL:** retained for audit but excluded from current terms.
- **Blue — FUTURE:** retained for audit but excluded from current terms.
- **White — NOT SELECTED / UNASSESSED:** unchanged content without an accepted current extraction decision.

---

## https://ameriabank.am/Portals/_default/skins/polo/ContentThemes/Title/item.html?cdv=517

Source: <https://ameriabank.am/Portals/_default/skins/polo/ContentThemes/Title/item.html?cdv=517>

<div style="border-left:5px solid #d0d5dd;background:#ffffff;padding:0.55em 0.8em;margin:1.2em 0 0.65em 0;"><strong>NOT SELECTED</strong> &nbsp; <code>api:11:216b29b08e48</code><br><small>other · irrelevant · unknown · rule</small><br><small>Payload is a reusable HTML presentation template, not product data.</small></div>

<div style="border-left:5px solid #98a2b3;background:#ffffff;padding:0.55em 0.8em;margin:1.2em 0 0.65em 0;"><strong>UNASSESSED</strong> &nbsp; <code>api:11:216b29b08e48:block:0</code><br><small>No source-discovery assessment was produced.</small></div>

{{:~registerFont(titleFontFamily)}}  
&lt;div class=&quot;wrapping-box&quot; {{wscAnimation: #data}} style=&quot;{{wscSlideStyle: #data}}&quot;&gt;  
&lt;{{:headingLevel}} class=&quot;{{:titleColorType}} {{:titleAlignment}}&quot;  
style=&quot;font-style: {{:titleFontStyle}}; font-weight: {{:titleFontWeight}};  
{{:titleTextTransform}};  
text-decoration: {{:titleTextDecoration}} {{:titleDecorationLine}} {{:titleDecorationColor}};  
letter-spacing: {{:titleLetterSpacing}};  
{{if titleColorType == &quot;emt-custom-color&quot;}}color: {{:titleCustomColor}};{{/if}}  
{{if titleFontFamily != &quot;default&quot;}}font-family: {{wscFontName:titleFontFamily}};{{/if}}  
{{if titleFontSize != &quot;default&quot;}}font-size: {{:titleFontSize}};{{/if}}  
{{if titleLineHeight != &quot;default&quot;}}line-height: {{:titleLineHeight}};{{/if}}  
{{if titleShadowStyle == &#x27;on&#x27;}}text-shadow: {{:titleHShadow}}px {{:titleVShadow}}px {{:titleBlurRadius}}px {{:titleShadowColor}};{{/if}}  
&quot;&gt;  
{{:title}}  
&lt;/{{:headingLevel}}&gt;  
&lt;/div&gt;  
{{if ~isEditMode }}  
{{include tmpl=&quot;wscMCMSlideActionPanel&quot; ~noDrag=true /}}  
{{/if}}
