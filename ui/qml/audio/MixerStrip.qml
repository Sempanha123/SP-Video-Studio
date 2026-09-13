import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id:root
    property var track:({})
    property var controller
    implicitWidth:138
    implicitHeight:Math.max(274, Math.round(274*Theme.textScale))
    selected:controller&&controller.selectedTrackId===(track.id||"")
    interactive:true
    accessibleName:(track.name||"Track")+" mixer strip. Gain "+Number(track.gainDb||0).toFixed(1)+" decibels"+(track.muted?". Muted":"")+(track.solo?". Solo":"")
    onClicked:if(controller)controller.selectTrack(track.id||"")
    ColumnLayout {
        anchors.fill:parent;anchors.margins:Theme.spacing.sm;spacing:Theme.spacing.xs
        Text { Layout.fillWidth:true;text:track.name||"Track";elide:Text.ElideRight;color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodySmall;font.weight:Theme.type.semibold }
        Text { text:(track.role||"general").replaceAll("_"," ");color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
        RowLayout { Layout.alignment:Qt.AlignHCenter;spacing:Theme.spacing.sm
            AudioMeter { peakDb:Number(track.peakDb||-60);meterName:(track.name||"Track")+" peak" }
            Slider {
                id:fader;orientation:Qt.Vertical;from:-60;to:12;value:Number(track.gainDb||0);stepSize:.5;Layout.preferredHeight:112
                Accessible.name:(track.name||"Track")+" gain, "+Number(value).toFixed(1)+" decibels";Accessible.role:Accessible.Slider
                property bool initialized:false;Component.onCompleted:initialized=true
                onValueChanged:if(initialized&&activeFocus&&!pressed&&root.controller)root.controller.setTrackGain(root.track.id,value)
                onPressedChanged:if(!pressed&&root.controller)root.controller.setTrackGain(root.track.id,value)
                ToolTip.visible:pressed||activeFocus;ToolTip.text:value.toFixed(1)+" dB";ToolTip.delay:Theme.tooltipDelay
            }
        }
        Text { Layout.alignment:Qt.AlignHCenter;text:Number(track.gainDb||0).toFixed(1)+" dB";color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
        Slider {
            id:pan;Layout.fillWidth:true;from:-1;to:1;value:Number(track.pan||0);stepSize:.05
            Accessible.name:(track.name||"Track")+" pan, "+Number(value).toFixed(2);Accessible.role:Accessible.Slider
            property bool initialized:false;Component.onCompleted:initialized=true
            onValueChanged:if(initialized&&activeFocus&&!pressed&&root.controller)root.controller.setTrackPan(root.track.id,value)
            onPressedChanged:if(!pressed&&root.controller)root.controller.setTrackPan(root.track.id,value)
        }
        RowLayout { Layout.fillWidth:true;spacing:Theme.spacing.xs
            AppButton { Layout.fillWidth:true;text:"M";accessibleName:"Mute "+(track.name||"track");tooltip:"Mute "+(track.name||"track");compact:true;variant:track.muted?"primary":"secondary";onClicked:if(root.controller)root.controller.setTrackMuted(root.track.id,!track.muted) }
            AppButton { Layout.fillWidth:true;text:"S";accessibleName:"Solo "+(track.name||"track");tooltip:"Solo "+(track.name||"track");compact:true;variant:track.solo?"primary":"secondary";onClicked:if(root.controller)root.controller.setTrackSolo(root.track.id,!track.solo) }
        }
    }
}
