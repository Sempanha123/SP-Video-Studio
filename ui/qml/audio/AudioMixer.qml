import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Commands 1.0
import "../theme"
import "../components"
Item {
    id:root
    property var controller
    property bool advanced:false
    function handleCommand(commandId){
        if(!root.controller || !root.controller.selectedTrackId) return false
        var track=root.controller.selectedTrack
        if(commandId==="audio.mute"){root.controller.setTrackMuted(root.controller.selectedTrackId,!Boolean(track.muted));return true}
        if(commandId==="audio.solo"){root.controller.setTrackSolo(root.controller.selectedTrackId,!Boolean(track.solo));return true}
        return false
    }
    onVisibleChanged:if(visible)Commands.setContext("audio_mixer")
    Connections{target:Commands;function onCommandTriggered(commandId){if(Commands.context==="audio_mixer")root.handleCommand(commandId)}}
    ColumnLayout { anchors.fill:parent;spacing:Theme.spacing.sm
        RowLayout { Layout.fillWidth:true
            ColumnLayout { Layout.fillWidth:true;spacing:0
                Text { text:"Audio Mixer";color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.heading;font.weight:Theme.type.semibold }
                Text { text:"Voice clarity, music, SFX and safe final output";color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
            }
            Text{visible:root.controller&&root.controller.selectedTrackId!=="";text:"Shift+M mute · Shift+S solo";color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption}
            AppComboBox { id:preset;model:["Voice Focus","Interview","News","Story","Shorts","Dub"];onActivated:if(root.controller)root.controller.applyPreset(currentText.toLowerCase().replaceAll(" ","_")) }
            SecondaryButton { text:root.advanced?"Simple":"Mixer";compact:true;onClicked:root.advanced=!root.advanced }
            SecondaryButton { text:"Render Audio Preview";compact:true;onClicked:if(root.controller)root.controller.renderPreview() }
        }
        DuckingPanel { Layout.fillWidth:true;controller:root.controller;visible:!root.advanced }
        ListView {
            visible:!root.advanced;Layout.fillWidth:true;Layout.fillHeight:true;clip:true;reuseItems:true;spacing:Theme.spacing.xs;model:root.controller?root.controller.tracks:[]
            delegate:MixerTrack { required property var modelData;width:ListView.view.width;track:modelData;controller:root.controller }
        }
        ColumnLayout {
            visible:root.advanced;Layout.fillWidth:true;Layout.fillHeight:true;spacing:Theme.spacing.sm
            RowLayout {
                Layout.fillWidth:true;Layout.fillHeight:true;spacing:Theme.spacing.sm
                ListView {
                    Layout.fillWidth:true;Layout.fillHeight:true;orientation:ListView.Horizontal;clip:true;reuseItems:true;spacing:Theme.spacing.sm;model:root.controller?root.controller.tracks:[]
                    delegate:MixerStrip { required property var modelData;height:ListView.view.height;track:modelData;controller:root.controller }
                }
                MasterStrip { Layout.preferredWidth:160;Layout.fillHeight:true;master:root.controller?root.controller.master:({});controller:root.controller }
            }
            RowLayout {
                Layout.fillWidth:true;Layout.preferredHeight:128;spacing:Theme.spacing.sm
                Text { text:"Buses";color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.caption;font.weight:Theme.type.semibold }
                ListView {
                    Layout.fillWidth:true;Layout.fillHeight:true;orientation:ListView.Horizontal;clip:true;reuseItems:true;spacing:Theme.spacing.sm;model:root.controller?root.controller.buses:[]
                    delegate:MixerBus { required property var modelData;height:ListView.view.height;bus:modelData;controller:root.controller }
                }
                AppCard {
                    Layout.preferredWidth:220;Layout.fillHeight:true
                    ColumnLayout { anchors.fill:parent;anchors.margins:Theme.spacing.sm;spacing:Theme.spacing.xs
                        Text { text:"Selected Track Effects";color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodySmall;font.weight:Theme.type.semibold }
                        Text { Layout.fillWidth:true;text:root.controller&&root.controller.selectedTrack.name?root.controller.selectedTrack.name:"Select a track";elide:Text.ElideRight;color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
                        RowLayout { Layout.fillWidth:true;enabled:root.controller&&root.controller.selectedTrackId!==""
                            AppButton { Layout.fillWidth:true;text:"Clear Voice";compact:true;variant:"secondary";onClicked:root.controller.addTrackEffectPreset(root.controller.selectedTrackId,"clear_voice") }
                            AppButton { Layout.fillWidth:true;text:"Gentle Comp";compact:true;variant:"secondary";onClicked:root.controller.addTrackEffectPreset(root.controller.selectedTrackId,"gentle_compressor") }
                        }
                        Text { Layout.fillWidth:true;text:"EQ, high-pass and compressor stay conservative; source audio is never rewritten.";wrapMode:Text.WordWrap;color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
                    }
                }
            }
        }
    }
}
