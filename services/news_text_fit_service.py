from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True,slots=True)
class TextFitResult:
    fits:bool;recommended_font_size:float;estimated_lines:int;max_lines:int;message:str=''
    def to_dict(self):return {'fits':self.fits,'recommendedFontSize':self.recommended_font_size,'estimatedLines':self.estimated_lines,'maxLines':self.max_lines,'message':self.message}
class NewsTextFitService:
    """Deterministic readability helper. It never truncates or rewrites factual text."""
    def analyze(self,text:str,width_norm:float,height_norm:float,font_size:float,*,role:str='headline')->TextFitResult:
        max_lines={'headline':4,'lower_third':2,'quote':7,'number':3,'source':2}.get(role,5)
        chars=max(1,len((text or '').strip())); per_line=max(8,int(max(.08,width_norm)*42*(48/max(18,font_size))))
        lines=max(1,(chars+per_line-1)//per_line); size=float(font_size)
        while lines>max_lines and size>22:
            size=max(22,size-2);per_line=max(8,int(max(.08,width_norm)*42*(48/max(18,size))));lines=max(1,(chars+per_line-1)//per_line)
        fits=lines<=max_lines and height_norm>=min(.04,lines*.02)
        return TextFitResult(fits,size,lines,max_lines,'' if fits else 'Text may not fit this layout at a readable size.')
