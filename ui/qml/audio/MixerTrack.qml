import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id:root
    property var track:({})
    property var controller
    implicitHeight:Math.max(64, Math.round(64*Theme.textScale))
    accessibleName:(track.name||"Track") + ". Gain " + Number(track.gainDb||0).toFixed(1) + " decibels. Pan " + Number(track.pan||0).toFixed(2) + (track.muted?". Muted":"") + (track.solo?". Solo":"")
    RowLayout {
        anchors.fill:parent;anchors.margins:Theme.spacing.sm;spacing:Theme.spacing.sm
        ColumnLayout { Layout.preferredWidth:170;spacing:0
            Text { id:nameLabel; Layout.fillWidth:true;text:track.name||"Track";elide:Text.ElideRight;color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodySmall;font.weight:Theme.type.semibold;ToolTip.visible:nameHover.hovered&&nameLabel.truncated;ToolTip.text:text;ToolTip.delay:Theme.tooltipDelay;HoverHandler{id:nameHover} }
            Text { text:(track.role||"").replaceAll("_"," ");color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
        }
        AppButton { text:"Mute";accessibleName:"Mute "+(track.name||"track");compact:true;variant:track.muted?"primary":"secondary";onClicked:if(controller)controller.setTrackMuted(track.id,!track.muted) }
        AppButton { text:"Solo";accessibleName:"Solo "+(track.name||"track");compact:true;variant:track.solo?"primary":"secondary";onClicked:if(controller)controller.setTrackSolo(track.id,!track.solo) }
        Text { text:"L";color:Theme.colors.textMuted;font.pixelSize:Theme.type.caption }
        Slider {
            id:panSlider;Layout.preferredWidth:90;from:-1;to:1;value:Number(track.pan||0);stepSize:.05
            Accessible.name:(track.name||"Track")+" pan, "+Number(value).toFixed(2);Accessible.role:Accessible.Slider
            property bool initialized:false;Component.onCompleted:initialized=true
            onValueChanged:if(initialized&&activeFocus&&!pressed&&controller)controller.setTrackPan(track.id,value)
            onPressedChanged:if(!pressed&&controller)controller.setTrackPan(track.id,value)
        }
        Text { text:"R";color:Theme.colors.textMuted;font.pixelSize:Theme.type.caption }
        Slider {
            id:gainSlider;Layout.fillWidth:true;from:-60;to:12;value:Number(track.gainDb||0);stepSize:.5
            Accessible.name:(track.name||"Track")+" gain, "+Number(value).toFixed(1)+" decibels";Accessible.role:Accessible.Slider
            property bool initialized:false;Component.onCompleted:initialized=true
            onValueChanged:if(initialized&&activeFocus&&!pressed&&controller)controller.setTrackGain(track.id,value)
            onPressedChanged:if(!pressed&&controller)controller.setTrackGain(track.id,value)
        }
        Text { Layout.preferredWidth:58;text:Number(track.gainDb||0).toFixed(1)+" dB";color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.caption;horizontalAlignment:Text.AlignRight }
    }
}
