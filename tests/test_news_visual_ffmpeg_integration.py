from __future__ import annotations
import shutil
from pathlib import Path
import pytest
from domain.render_settings import RenderSettings
from media.ffmpeg import FFmpegRunner
from media.probe import FFprobeService
from rendering.encoder_registry import EncoderRegistry
from rendering.output_validator import OutputValidator
from rendering.render_plan import RenderPlan
from rendering.renderer import FFmpegRenderer

pytestmark=pytest.mark.skipif(not (shutil.which('ffmpeg') and shutil.which('ffprobe')),reason='FFmpeg/FFprobe not available')

def _renderer():
    r=FFmpegRunner(shutil.which('ffmpeg'));return FFmpegRenderer(r,EncoderRegistry(r,r.discover_capabilities()))

def _shape(x,y,w,h,color='#19242F',opacity=.94):
    return {'id':'shape','type':'shape','order':0,'visible':True,'text':'','x':x,'y':y,'width':w,'height':h,'opacity':opacity,'startOffsetMs':0,'endOffsetMs':-1,'style':{'fillColor':color,'radius':10}}

def _text(identifier,text,secondary='',x=.12,y=.3,w=.76,h=.3,size=48):
    return {'id':identifier,'type':'headline','order':1,'visible':True,'text':text,'secondaryText':secondary,'x':x,'y':y,'width':w,'height':h,'opacity':1.0,'startOffsetMs':0,'endOffsetMs':-1,'style':{'fontFamily':'Noto Sans Khmer','fontSize':size,'fontWeight':700,'color':'#FFFFFFFF'}}

def test_real_khmer_news_card_shape_and_unicode_render(tmp_path:Path):
    scene={'sceneId':'news-km','durationMs':1400,'visual':{'backgroundColor':'#0F141A','fitMode':'fill'},'audio':{},'overlays':[_shape(.07,.18,.86,.65,'#18212B'),_text('headline','ព័ត៌មានបច្ចេកវិទ្យាថ្មី','ក្រុមហ៊ុនបានប្រកាសផលិតផលថ្មីនៅថ្ងៃនេះ។',.12,.27,.76,.38,44)],'transitionIn':{},'transitionOut':{}}
    settings=RenderSettings(320,180,30,'libx264','fast');plan=RenderPlan('p',str(tmp_path/'khmer-news.mp4'),settings,[scene],1400,str(tmp_path/'temp'))
    result=_renderer().render(plan);validation=OutputValidator(FFprobeService(lambda:shutil.which('ffprobe'))).validate(result.output_path,width=320,height=180,fps=30,expected_duration_ms=1400)
    assert validation.probe.width==320 and validation.probe.height==180 and validation.duration_delta_ms<=250

def test_real_vertical_bilingual_news_headline_render(tmp_path:Path):
    scene={'sceneId':'news-bi','durationMs':1300,'visual':{'backgroundColor':'#101820','fitMode':'fill'},'audio':{},'overlays':[_shape(.08,.25,.84,.48,'#20303A'),_text('headline','OpenAI','បច្ចេកវិទ្យាថ្មី',.14,.34,.72,.25,52)],'transitionIn':{},'transitionOut':{}}
    settings=RenderSettings(180,320,30,'libx264','fast');plan=RenderPlan('p',str(tmp_path/'bilingual-news.mp4'),settings,[scene],1300,str(tmp_path/'temp'))
    result=_renderer().render(plan);probe=FFprobeService(lambda:shutil.which('ffprobe')).probe(result.output_path,'video');assert probe.width==180 and probe.height==320
