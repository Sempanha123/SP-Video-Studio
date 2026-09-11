from __future__ import annotations
import logging
from PySide6.QtCore import QObject, Property, Signal, Slot

class WordTimingController(QObject):
    changed=Signal(); operationFailed=Signal(str)
    def __init__(self,service,parent=None,logger=None): super().__init__(parent);self.service=service;self.logger=logger or logging.getLogger("sp_video_studio.word_timing");self._project_id="";self._segment_id="";self._words=[]
    @Property('QVariantList',notify=changed)
    def words(self):return list(self._words)
    @Property(str,notify=changed)
    def segmentId(self):return self._segment_id
    @Slot(str,str)
    def load(self,project_id,segment_id):
        self._project_id=project_id or "";self._segment_id=segment_id or "";self.refresh()
    @Slot()
    def refresh(self):
        try:self._words=[self._map(x) for x in self.service.words(self._project_id,self._segment_id)] if self._project_id and self._segment_id else [];self.changed.emit()
        except Exception as exc:self._fail(exc)
    @Slot(str,str,int,int,int,bool,result=bool)
    def updateWord(self,word_id,text,start_ms,end_ms,fps=30,snap=False):
        try:self.service.update_word(self._project_id,word_id,text=text,start_ms=start_ms,end_ms=end_ms,fps=fps,snap_to_frame=snap);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,result=bool)
    def mergeWords(self,first_id,second_id):
        try:self.service.merge(self._project_id,first_id,second_id);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,str,int,result=bool)
    def splitWord(self,word_id,first_text,second_text,split_ms):
        try:self.service.split(self._project_id,word_id,first_text,second_text,split_ms=(split_ms if split_ms>=0 else None));self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @staticmethod
    def _map(x):return {"id":x.id,"text":x.text,"startMs":x.start_ms,"endMs":x.end_ms,"probability":x.probability if x.probability is not None else -1.0,"order":x.order}
    def _fail(self,exc):self.logger.exception("Word timing edit failed");self.operationFailed.emit(str(exc) or "Word timing edit failed.")
