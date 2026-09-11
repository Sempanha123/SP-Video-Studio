from __future__ import annotations
from collections import Counter
from pathlib import Path
from domain.template import Template


class TemplatePreviewService:
    def preview(self,item:Template)->dict[str,object]:
        components=Counter(x.type_code for x in item.components if x.enabled)
        required=[p for p in item.placeholders if p.required]
        speakers=[p for p in item.placeholders if p.type_code=="speaker"]
        media=[p for p in item.placeholders if p.type_code in {"media","video","image","audio","logo"}]
        preview=""
        if item.preview_image:
            candidate=Path(item.preview_image)
            if not candidate.is_absolute() and item.manifest_path: candidate=Path(item.manifest_path).parent/candidate
            try:
                if candidate.is_file(): preview=candidate.resolve().as_uri()
            except OSError: preview=""
        return {"id":item.id,"name":item.name,"description":item.description,"workflow":item.workflow,"templateType":item.type_code,"category":item.category,"previewImage":preview,"aspects":list(item.supported_aspect_ratios),"languages":list(item.supported_languages),"features":list(item.required_features),"tags":list(item.tags),"componentCounts":dict(components),"requiredPlaceholders":[p.to_dict() for p in required],"speakerRoles":[p.role or p.label for p in speakers],"mediaPlaceholders":[p.to_dict() for p in media],"builtin":item.builtin,"version":item.version}
