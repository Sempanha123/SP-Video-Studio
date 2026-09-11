import QtQuick 2.15
import "../theme"
Canvas {
    id:root
    property var buckets:[]
    property color waveformColor:Theme.colors.clipAudio
    property color centerColor:Theme.colors.borderStrong
    implicitHeight:56
    onBucketsChanged:requestPaint()
    onWidthChanged:requestPaint()
    onHeightChanged:requestPaint()
    onPaint:{
        var ctx=getContext("2d");ctx.reset();ctx.clearRect(0,0,width,height)
        ctx.strokeStyle=centerColor;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(0,height/2);ctx.lineTo(width,height/2);ctx.stroke()
        if(!buckets||buckets.length===0)return
        ctx.strokeStyle=waveformColor;ctx.lineWidth=Math.max(1,width/buckets.length*.65);ctx.beginPath()
        var step=width/buckets.length
        for(var i=0;i<buckets.length;i++){
            var pair=buckets[i];var x=i*step+step/2;var y1=height/2-(Number(pair[1]||0)*height*.46);var y2=height/2-(Number(pair[0]||0)*height*.46)
            ctx.moveTo(x,y1);ctx.lineTo(x,y2)
        }
        ctx.stroke()
    }
}
