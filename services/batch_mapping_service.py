from __future__ import annotations
import re,unicodedata
from datetime import date
from pathlib import Path,PurePath
from typing import Any,Mapping
from domain.batch_errors import BatchMappingError
from domain.batch_mapping import BatchMapping,BatchMappingKind,BatchTransform
from domain.template_placeholder import resolve_placeholders

_RESERVED={"CON","PRN","AUX","NUL",*(f"COM{i}" for i in range(1,10)),*(f"LPT{i}" for i in range(1,10))}
_BAD=re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_filename(value:str,default:str='output')->str:
    text=unicodedata.normalize('NFKC',str(value or '')).strip().replace('..',' ')
    text=_BAD.sub(' ',text);text=re.sub(r'\s+',' ',text).strip(' .')
    stem=Path(text).stem if text else ''
    suffix=Path(text).suffix if text else ''
    if not stem:stem=default
    if stem.upper() in _RESERVED:stem=f'_{stem}'
    return (stem[:120].rstrip(' .') or default)+(suffix[:12] if suffix else '')


def safe_relative_output(pattern:str,resolutions:Mapping[str,Any],extension:str='.mp4')->str:
    rendered=str(resolve_placeholders(pattern,resolutions,preserve_unresolved=False) or '')
    rendered=rendered.replace('\\','/')
    parts=[]
    for raw in rendered.split('/'):
        raw=raw.strip()
        if not raw or raw in {'.','..'}:continue
        parts.append(safe_filename(raw,'output'))
    if not parts:parts=['output']
    rel=Path(*parts)
    name=rel.name
    if extension and Path(name).suffix.lower()!=extension.lower():name=safe_filename(Path(name).stem,'output')+extension
    rel=rel.with_name(name)
    if rel.is_absolute() or '..' in rel.parts:raise BatchMappingError('Output path escaped the Batch output directory.')
    return rel.as_posix()


class BatchMappingService:
    SYSTEM_VALUES={'row_number','batch_name','current_date','project_name'}
    def resolve(self,row:Mapping[str,Any],mappings:list[BatchMapping],*,row_index:int,batch_name:str,project_name:str='',context:Mapping[str,Any]|None=None)->dict[str,Any]:
        ctx=dict(context or {});result:dict[str,Any]={}
        for mapping in mappings:
            mapping.validate();kind=mapping.kind_code
            if kind in {BatchMappingKind.COLUMN.value,BatchMappingKind.ASSET_COLUMN.value,BatchMappingKind.VOICE_COLUMN.value}:value=row.get(mapping.source,mapping.default_value)
            elif kind in {BatchMappingKind.CONSTANT.value,BatchMappingKind.ASSET_FIXED.value,BatchMappingKind.VOICE_FIXED.value}:value=mapping.value
            elif kind==BatchMappingKind.SYSTEM.value:value=self._system(mapping.source,row_index,batch_name,project_name)
            elif kind==BatchMappingKind.DEFAULT.value:value=mapping.default_value
            elif kind==BatchMappingKind.EMPTY.value:value=''
            elif kind==BatchMappingKind.GENERATED_FILENAME.value:
                values={**dict(row),**ctx,**result,'row_number':row_index+1,'batch_name':batch_name,'project_name':project_name};value=safe_relative_output(str(mapping.value or '{{row_number}}'),values)
            elif kind==BatchMappingKind.ASSET_COLLECTION.value:value=mapping.value
            elif kind==BatchMappingKind.VOICE_LANGUAGE.value:
                choices=mapping.value if isinstance(mapping.value,dict) else {}
                language=str(ctx.get('language') or result.get('language') or row.get('language') or '')
                value=choices.get(language,choices.get('default',mapping.default_value))
            elif kind==BatchMappingKind.VOICE_ROLE.value:
                choices=mapping.value if isinstance(mapping.value,dict) else {}
                role=str(mapping.source or mapping.metadata.get('role') or ctx.get('speaker_role') or '')
                value=choices.get(role,choices.get('default',mapping.default_value))
            else:raise BatchMappingError(f'Unsupported mapping kind: {kind}')
            value=self.apply_transforms(value,mapping.transforms)
            if value in (None,'') and mapping.default_value not in (None,''):value=mapping.default_value
            if mapping.required and value in (None,''):raise BatchMappingError(f'Required mapping is empty: {mapping.target}')
            result[mapping.target]=value
        return result
    def preview(self,rows:list[Mapping[str,Any]],mappings:list[BatchMapping],**kwargs)->list[dict[str,Any]]:
        return [self.resolve(row,mappings,row_index=i,**kwargs) for i,row in enumerate(rows[:5])]
    def apply_transforms(self,value:Any,transforms:list[dict[str,Any]])->Any:
        if not transforms:return value
        text='' if value is None else str(value)
        for spec in transforms:
            kind=str(spec.get('type') or '')
            if kind==BatchTransform.TRIM.value:text=text.strip()
            elif kind==BatchTransform.UPPERCASE.value:text=text.upper()
            elif kind==BatchTransform.LOWERCASE.value:text=text.lower()
            elif kind==BatchTransform.PREFIX.value:text=str(spec.get('value') or '')+text
            elif kind==BatchTransform.SUFFIX.value:text=text+str(spec.get('value') or '')
            else:raise BatchMappingError(f'Unsafe or unsupported transform: {kind}')
        return text
    def _system(self,key:str,row_index:int,batch_name:str,project_name:str)->Any:
        if key not in self.SYSTEM_VALUES:raise BatchMappingError(f'Unknown system mapping: {key}')
        return {'row_number':row_index+1,'batch_name':batch_name,'current_date':date.today().isoformat(),'project_name':project_name}.get(key,'')
