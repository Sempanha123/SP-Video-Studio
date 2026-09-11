from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True,slots=True)
class NewsVisualIssue:
    severity:str;code:str;message:str
    def to_dict(self):return {'severity':self.severity,'code':self.code,'message':self.message}

def _rgb(color:str):
    s=(color or '').lstrip('#');s=s[:6]
    if len(s)!=6:return (255,255,255)
    try:return tuple(int(s[i:i+2],16) for i in (0,2,4))
    except ValueError:return (255,255,255)
def _lum(c):
    vals=[]
    for x in c:
        v=x/255;vals.append(v/12.92 if v<=.03928 else ((v+.055)/1.055)**2.4)
    return .2126*vals[0]+.7152*vals[1]+.0722*vals[2]
def contrast_ratio(a:str,b:str)->float:
    l1,l2=_lum(_rgb(a)),_lum(_rgb(b));hi,lo=max(l1,l2),min(l1,l2);return (hi+.05)/(lo+.05)
class NewsVisualValidationService:
    def validate_theme(self,theme)->list[NewsVisualIssue]:
        issues=[]
        if contrast_ratio(theme.text_primary,theme.background_color)<4.5:issues.append(NewsVisualIssue('warning','poor_contrast','Primary text contrast is low.'))
        if not theme.font_heading.strip() or not theme.font_body.strip():issues.append(NewsVisualIssue('error','missing_font','A heading/body font is required.'))
        return issues
    def validate_overlay(self,overlay,*,scene_duration_ms:int,element=None,claim=None)->list[NewsVisualIssue]:
        issues=[]
        if overlay.x<0 or overlay.y<0 or overlay.x+overlay.width>1.0001 or overlay.y+overlay.height>1.0001:issues.append(NewsVisualIssue('error','outside_canvas','Graphic extends outside the scene canvas.'))
        if overlay.x<.035 or overlay.y<.035 or overlay.x+overlay.width>.965 or overlay.y+overlay.height>.965:issues.append(NewsVisualIssue('warning','unsafe_position','Graphic is close to the recommended safe-area edge.'))
        text=(overlay.text or '')+' '+(overlay.secondary_text or '')
        cap=max(24,int(overlay.width*overlay.height*420))
        if len(text.strip())>cap:issues.append(NewsVisualIssue('warning','text_overflow','This graphic contains more text than the selected layout comfortably supports.'))
        if element and element.claim_id and claim:
            if claim.status_code=='rejected':issues.append(NewsVisualIssue('error','rejected_claim','This visual is linked to a rejected claim.'))
            elif claim.status_code in {'unsupported','conflicting'}:issues.append(NewsVisualIssue('warning','claim_not_approved','This visual is linked to a claim that is no longer approved.'))
        return issues
    def validate_project(self,project_id:str,elements:list,overlay_lookup,claim_lookup)->dict:
        ready=warnings=errors=0
        for e in elements:
            o=overlay_lookup(e.scene_overlay_id);c=claim_lookup(e.claim_id) if e.claim_id else None
            issues=self.validate_overlay(o,scene_duration_ms=0,element=e,claim=c) if o else [NewsVisualIssue('error','missing_overlay','News graphic overlay is missing.')]
            if any(x.severity=='error' for x in issues):errors+=1
            elif issues:warnings+=1
            else:ready+=1
        return {'ready':ready,'warnings':warnings,'errors':errors,'total':len(elements)}
