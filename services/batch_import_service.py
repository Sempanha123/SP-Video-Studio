from __future__ import annotations
import csv,json
from pathlib import Path
from typing import Any
from domain.batch_errors import BatchInvalidInput
from domain.batch_input import BatchInputRow

class BatchImportService:
    MAX_BYTES=64*1024*1024
    MAX_ROWS=100_000
    MAX_JSON_DEPTH=12
    def import_csv(self,path:str|Path)->list[BatchInputRow]:
        p=self._file(path);text=p.read_text(encoding='utf-8-sig')
        reader=csv.DictReader(text.splitlines())
        if not reader.fieldnames:raise BatchInvalidInput('CSV requires a header row.')
        headers=[str(h or '').strip() for h in reader.fieldnames]
        if any(not h for h in headers) or len(headers)!=len(set(headers)):raise BatchInvalidInput('CSV headers must be non-empty and unique.')
        rows=[]
        for i,raw in enumerate(reader):
            if i>=self.MAX_ROWS:raise BatchInvalidInput('CSV contains too many rows.')
            rows.append(BatchInputRow(i,{k:(v if v is not None else '') for k,v in raw.items()}))
        return rows
    def import_json(self,path:str|Path)->list[BatchInputRow]:
        p=self._file(path)
        try:data=json.loads(p.read_text(encoding='utf-8-sig'))
        except Exception as exc:raise BatchInvalidInput('JSON input could not be parsed.') from exc
        if not isinstance(data,list):raise BatchInvalidInput('JSON Batch input must be an array of objects.')
        if len(data)>self.MAX_ROWS:raise BatchInvalidInput('JSON contains too many rows.')
        rows=[]
        for i,row in enumerate(data):
            if not isinstance(row,dict):raise BatchInvalidInput(f'JSON row {i+1} must be an object.')
            self._validate_depth(row,0);rows.append(BatchInputRow(i,{str(k):v for k,v in row.items()}))
        return rows
    def import_jsonl(self,path:str|Path)->list[BatchInputRow]:
        p=self._file(path);rows=[]
        for i,line in enumerate(p.read_text(encoding='utf-8-sig').splitlines()):
            if not line.strip():continue
            if len(rows)>=self.MAX_ROWS:raise BatchInvalidInput('JSONL contains too many rows.')
            try:row=json.loads(line)
            except Exception as exc:raise BatchInvalidInput(f'JSONL line {i+1} is invalid.') from exc
            if not isinstance(row,dict):raise BatchInvalidInput(f'JSONL line {i+1} must be an object.')
            self._validate_depth(row,0);rows.append(BatchInputRow(len(rows),{str(k):v for k,v in row.items()}))
        return rows
    def manual_rows(self,rows:list[dict[str,Any]])->list[BatchInputRow]:
        if len(rows)>self.MAX_ROWS:raise BatchInvalidInput('Manual Batch contains too many rows.')
        return [BatchInputRow(i,{str(k):v for k,v in dict(row).items()}) for i,row in enumerate(rows)]
    def import_path(self,path:str|Path)->list[BatchInputRow]:
        suffix=Path(path).suffix.lower()
        if suffix=='.csv':return self.import_csv(path)
        if suffix=='.json':return self.import_json(path)
        if suffix in {'.jsonl','.ndjson'}:return self.import_jsonl(path)
        raise BatchInvalidInput('Batch input must be CSV, JSON or JSONL.')
    def _file(self,path:str|Path)->Path:
        p=Path(path).expanduser().resolve()
        if not p.is_file():raise BatchInvalidInput('Batch input file could not be found.')
        if p.stat().st_size>self.MAX_BYTES:raise BatchInvalidInput('Batch input file is too large.')
        return p
    def _validate_depth(self,value:Any,depth:int)->None:
        if depth>self.MAX_JSON_DEPTH:raise BatchInvalidInput('JSON nesting is too deep.')
        if isinstance(value,dict):
            for v in value.values():self._validate_depth(v,depth+1)
        elif isinstance(value,list):
            for v in value:self._validate_depth(v,depth+1)
