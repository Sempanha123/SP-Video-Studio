import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id:root
    property var track:({})
    property var controller
    implicitHeight:64
    RowLayout {
        anchors.fill:parent;anchors.margins:Theme.spacing.sm;spacing:Theme.spacing.sm
        ColumnLayout { Layout.preferredWidth:170;spacing:0
            Text { Layout.fillWidth:true;text:track.name||"Track";elide:Text.ElideRight;color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodySmall;font.weight:Theme.type.semibold }
            Text { text:(track.role||"").replaceAll("_"," ");color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
        }
        AppButton { text:"Mute";compact:true;variant:track.muted?"primary":"secondary";onClicked:if(controller)controller.setTrackMuted(track.id,!track.muted) }
        AppButton { text:"Solo";compact:true;variant:track.solo?"primary":"secondary";onClicked:if(controller)controller.setTrackSolo(track.id,!track.solo) }
        Text { text:"L";color:Theme.colors.textMuted;font.pixelSize:Theme.type.caption }
        Slider { Layout.preferredWidth:90;from:-1;to:1;value:Number(track.pan||0);onPressedChanged:if(!pressed&&controller)controller.setTrackPan(track.id,value) }
        Text { text:"R";color:Theme.colors.textMuted;font.pixelSize:Theme.type.caption }
        Slider { Layout.fillWidth:true;from:-60;to:12;value:Number(track.gainDb||0);stepSize:.5;onPressedChanged:if(!pressed&&controller)controller.setTrackGain(track.id,value) }
        Text { Layout.preferredWidth:58;text:Number(track.gainDb||0).toFixed(1)+" dB";color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.caption;horizontalAlignment:Text.AlignRight }
    }
}
