from __future__ import annotations
import os,shutil
from dataclasses import dataclass,field
from pathlib import Path
from typing import Any,Mapping
from domain.batch_errors import BatchAssetMissing,BatchLanguageUnsupported,BatchMappingError,BatchVoiceMissing
from domain.batch_input import BatchRowValidity
from domain.batch_mapping import BatchMapping,BatchMappingKind
from domain.template_placeholder import TemplatePlaceholderType
from services.batch_mapping_service import BatchMappingService,safe_relative_output

@dataclass(slots=True)
class BatchDryRunItem:
    row_index:int; item_key:str; validity:str=BatchRowValidity.VALID.value; errors:list[dict[str,str]]=field(default_factory=list); warnings:list[str]=field(default_factory=list); resolved:dict[str,Any]=field(default_factory=dict); output_relative:str=""; estimated_bytes:int=0
    def add_error(self,code:str,message:str):self.errors.append({'code':code,'message':message});self.validity=BatchRowValidity.INVALID.value
    def add_warning(self,message:str):
        self.warnings.append(message)
        if self.validity==BatchRowValidity.VALID.value:self.validity=BatchRowValidity.WARNING.value
    def to_dict(self):return {'rowIndex':self.row_index,'itemKey':self.item_key,'validity':self.validity,'errors':list(self.errors),'warnings':list(self.warnings),'resolved':dict(self.resolved),'outputRelative':self.output_relative,'estimatedBytes':self.estimated_bytes}

@dataclass(slots=True)
class BatchDryRunSummary:
    items:list[BatchDryRunItem]; estimated_bytes:int; free_bytes:int; disk_ok:bool
    @property
    def total(self):return len(self.items)
    @property
    def ready(self):return sum(1 for x in self.items if x.validity==BatchRowValidity.VALID.value)
    @property
    def warnings(self):return sum(1 for x in self.items if x.validity==BatchRowValidity.WARNING.value)
    @property
    def invalid(self):return sum(1 for x in self.items if x.validity==BatchRowValidity.INVALID.value)
    def to_dict(self):return {'total':self.total,'ready':self.ready,'warnings':self.warnings,'invalid':self.invalid,'estimatedBytes':self.estimated_bytes,'freeBytes':self.free_bytes,'diskOk':self.disk_ok,'items':[x.to_dict() for x in self.items]}

class BatchValidationService:
    GENERAL_TARGETS={'title','headline','hook','body','text','script','approved_script','translated_script','translated_body','translated_text','translation_reviewed','reviewed_translation_id','language','source_language','voice','voice_id','platform','aspect_ratio','output_name','subtitle_preset','reporter_name','guest_name','narrator_name','reporter_text','guest_text','narrator_text','reporter_outro','reporter_voice','guest_voice','narrator_voice','source_attribution','claim_id','claims','approved_news_project_id','transcript_id','translation_id'}
    MEDIA_TYPES={TemplatePlaceholderType.MEDIA.value,TemplatePlaceholderType.VIDEO.value,TemplatePlaceholderType.IMAGE.value,TemplatePlaceholderType.AUDIO.value,TemplatePlaceholderType.LOGO.value}
    def __init__(self,mapping_service:BatchMappingService,variant_service,*,language_service=None,asset_service=None,voice_resolver=None,export_estimator=None):
        self.mapping=mapping_service;self.variants=variant_service;self.languages=language_service;self.assets=asset_service;self.voice_resolver=voice_resolver;self.export_estimator=export_estimator
    def dry_run(self,*,batch_name:str,template,rows:list[Mapping[str,Any]],mappings:list[BatchMapping],variant_config,output_root:str|Path,settings:Mapping[str,Any]|None=None)->BatchDryRunSummary:
        settings=dict(settings or {});expanded=self.variants.expand(rows,variant_config);root=Path(output_root).expanduser().resolve();root.mkdir(parents=True,exist_ok=True);used_paths:set[str]=set();results=[]
        by_target={m.target:m for m in mappings}
        placeholder_ids={p.id for p in getattr(template,'placeholders',[])}
        unknown_targets=sorted(set(by_target)-placeholder_ids-self.GENERAL_TARGETS)
        for entry in expanded:
            i=entry['rowIndex'];variant=entry['variant'];item=BatchDryRunItem(i,entry['itemKey'])
            try:
                resolved=self.mapping.resolve(entry['input'],mappings,row_index=i,batch_name=batch_name,project_name=f'{batch_name} {i+1}',context=variant)
            except Exception as exc:
                item.add_error('mapping_error',str(exc));resolved={}
            # Variant dimensions override only when explicitly configured.
            for key,value in variant.items():
                if value not in ('',None):resolved[key]=value
            item.resolved=resolved
            for target in unknown_targets:item.add_error('unknown_placeholder',f'Mapping target is not a template placeholder or supported Batch field: {target}')
            self._validate_template(item,template,resolved,by_target,entry,variant_config,settings)
            pattern=str(settings.get('output_pattern') or '{{language}}/{{output_name}}.mp4')
            values={**entry['input'],**resolved,'row_number':i+1,'output_name':resolved.get('output_name') or entry['itemKey'],'language':resolved.get('language') or variant.get('language') or 'und'}
            try:
                rel=safe_relative_output(pattern,values);target=(root/rel).resolve()
                if target!=root and root not in target.parents:raise BatchMappingError('Output path escaped Batch root.')
                policy=str(settings.get('collision_policy') or 'keep_both')
                duplicate=rel.casefold() in used_paths
                if duplicate and policy=='keep_both':
                    rel=self._unique_relative(rel,used_paths,root);target=(root/rel).resolve();item.add_warning('Duplicate output name was made unique by Keep Both.')
                elif duplicate:
                    item.add_error('output_collision','Two Batch items resolve to the same output path; use Keep Both or change the naming pattern.')
                if target.exists():
                    if policy=='fail':item.add_error('output_collision','Output already exists.')
                    elif policy=='replace':item.add_warning('Existing output will be replaced only after a successful new export.')
                    elif policy=='keep_both':
                        rel=self._unique_relative(rel,used_paths,root);target=(root/rel).resolve();item.add_warning('Existing output name was made unique by Keep Both.')
                item.output_relative=rel;used_paths.add(rel.casefold())
            except Exception as exc:item.add_error('unsafe_output_path',str(exc))
            item.estimated_bytes=self._estimate(item,template,settings);results.append(item)
        estimated=sum(x.estimated_bytes for x in results)
        try:free=shutil.disk_usage(root).free
        except OSError:free=0
        reserve=max(int(settings.get('disk_reserve_bytes') or 512*1024*1024),int(estimated*0.1));disk_ok=free==0 or free>=estimated+reserve
        if not disk_ok:
            for item in results:
                if item.validity!=BatchRowValidity.INVALID.value:item.add_warning('Estimated free disk space may be insufficient for this Batch.')
        return BatchDryRunSummary(results,estimated,free,disk_ok)
    def _validate_template(self,item,template,resolved,by_target,entry,variant_config,settings):
        language=str(resolved.get('language') or entry['variant'].get('language') or entry['input'].get('language') or variant_config.source_language or 'en')
        resolved['language']=language
        try:
            if self.languages:self.languages.get(language)
        except Exception:item.add_error('invalid_language',f'Unknown language: {language}')
        if getattr(template,'supported_languages',()) and language not in template.supported_languages:item.add_error('template_language',f'Template does not support {language}.')
        aspect=str(resolved.get('aspect_ratio') or entry['variant'].get('aspect_ratio') or '')
        if aspect and getattr(template,'supported_aspect_ratios',()) and aspect not in template.supported_aspect_ratios:item.add_error('template_aspect',f'Template does not support {aspect}.')
        for ph in getattr(template,'placeholders',[]):
            value=resolved.get(ph.id,ph.default_value)
            if ph.required and value in ('',None):item.add_error('required_placeholder',f'Required placeholder is empty: {ph.label}')
            if ph.type_code in self.MEDIA_TYPES and value not in ('',None) and self.assets:
                try:
                    mapping=by_target.get(ph.id)
                    if mapping and mapping.kind_code==BatchMappingKind.ASSET_COLLECTION.value:
                        cfg=mapping.value if isinstance(mapping.value,dict) else {'collectionId':mapping.value};asset=self.assets.choose(str(cfg.get('collectionId') or ''),strategy=str(cfg.get('strategy') or 'round_robin'),row_index=entry['rowIndex'],item_key=entry['itemKey'],seed=int(cfg.get('seed',variant_config.seed) or 0))
                    else:asset=self.assets.resolve_value(value)
                    resolved[ph.id]=asset.id
                except Exception as exc:item.add_error('missing_asset',str(exc))
            if ph.type_code==TemplatePlaceholderType.VOICE.value and (ph.required or value not in ('',None)):
                voice=str(value or '')
                if not voice:item.add_error('missing_voice',f'Voice Setup Required: {ph.label}')
                elif self.voice_resolver:
                    try:
                        state=self.voice_resolver(voice,language,ph.role)
                        if state is False or (isinstance(state,dict) and not state.get('available',False)):raise BatchVoiceMissing(f'Voice {voice} is unavailable for {language}.')
                    except Exception as exc:item.add_error('missing_voice',str(exc))
        source=str(resolved.get('source_language') or variant_config.source_language or entry['input'].get('source_language') or entry['input'].get('language') or language);resolved['source_language']=source
        if source!=language:
            policy=str(settings.get('translation_policy') or 'reviewed_only')
            reviewed=bool(entry['input'].get('translation_reviewed') or resolved.get('translation_reviewed'))
            reviewed_content=any(entry['input'].get(k) or resolved.get(k) for k in ('translated_script','translated_body','translated_text','reviewed_translation_id'))
            if policy=='reviewed_only':
                if not reviewed or not reviewed_content:item.add_error('translation_review_required','Reviewed translation content/reference is required before this item can continue.')
            elif policy=='allow_machine_translation':
                if self.languages and hasattr(self.languages,'supports_translation_pair') and not self.languages.supports_translation_pair(source,language):item.add_error('translation_unsupported',f'Configured translation provider does not support {source} → {language}.')
                else:resolved['machine_translation_used']=True
            elif policy=='skip_translation':item.add_warning('Target language differs from source but translation is disabled.')
            else:item.add_error('translation_policy','Unknown Batch translation policy.')
        if bool(settings.get('enable_tts')):
            voice=str(resolved.get('voice') or resolved.get('voice_id') or '')
            if not voice:item.add_error('missing_voice','Voice Setup Required for TTS Batch item.')
            elif self.voice_resolver:
                try:
                    state=self.voice_resolver(voice,language,'')
                    if state is False or (isinstance(state,dict) and not state.get('available',False)):raise BatchVoiceMissing(f'Voice {voice} is unavailable for {language}.')
                except Exception as exc:item.add_error('missing_voice',str(exc))
        workflow=str(getattr(template,'workflow','')).casefold()
        if workflow=='news':
            grounded=any(resolved.get(k) or entry['input'].get(k) for k in ('script','body','approved_script','claim_id','approved_news_project_id','source_attribution','claims'))
            if not grounded:item.add_error('news_grounding_required','News Batch rows require approved claims/script/source content; a topic alone is not enough.')
    @staticmethod
    def _unique_relative(rel:str,used_paths:set[str],root:Path)->str:
        path=Path(rel);parent=path.parent;stem=path.stem or 'output';suffix=path.suffix or '.mp4';index=2
        candidate=path
        while candidate.as_posix().casefold() in used_paths or (root/candidate).exists():
            candidate=parent/f"{stem} ({index}){suffix}";index+=1
        return candidate.as_posix()

    def _estimate(self,item,template,settings)->int:
        if self.export_estimator:
            try:return max(1,int(self.export_estimator(item.resolved,template)))
            except Exception:pass
        # Conservative metadata-only estimate used for dry-run warnings, never an ETA.
        seconds=float(item.resolved.get('duration_seconds') or settings.get('default_duration_seconds') or 30)
        bitrate=int(settings.get('estimate_video_bitrate_bps') or 8_000_000);project_overhead=int(settings.get('estimate_project_overhead_bytes') or 64*1024*1024)
        return int(seconds*bitrate/8)+project_overhead
