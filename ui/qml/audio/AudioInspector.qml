import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id:root
    property var clip:({})
    property var controller
    implicitHeight:210
    ColumnLayout { anchors.fill:parent;anchors.margins:Theme.spacing.md;spacing:Theme.spacing.sm
        Text { text:"Audio Inspector";color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.heading;font.weight:Theme.type.semibold }
        Text { Layout.fillWidth:true;text:(clip.speakerName||clip.fileName||clip.sourcePath||"Select an audio clip");elide:Text.ElideMiddle;color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodySmall }
        Text { visible:!!clip.language;text:(clip.speakerName||"")+(clip.language?" • "+clip.language:"");color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
        RowLayout { Layout.fillWidth:true;Text { text:"Gain";color:Theme.colors.textSecondary };Slider { Layout.fillWidth:true;from:-60;to:12;value:Number(clip.gainDb||0);enabled:false };Text { text:Number(clip.gainDb||0).toFixed(1)+" dB";color:Theme.colors.textSecondary } }
        RowLayout { Layout.fillWidth:true;Text { text:"Fade In";color:Theme.colors.textSecondary };Text { Layout.fillWidth:true;text:Number(clip.fadeInMs||0)+" ms";color:Theme.colors.textMuted };Text { text:"Fade Out  "+Number(clip.fadeOutMs||0)+" ms";color:Theme.colors.textMuted } }
        Text { Layout.fillWidth:true;text:"Advanced effects: EQ • High/Low Pass • Compressor • Limiter";wrapMode:Text.WordWrap;color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
    }
}
