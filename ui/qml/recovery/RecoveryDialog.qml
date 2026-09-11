import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
import SPVideoStudio.Phase27 1.0
AppDialog {
    id: root; modal:true; width:Math.min(720,parent?parent.width-48:720); height:Math.min(600,parent?parent.height-48:600); closePolicy:Popup.NoAutoClose
    property var reviewData:({})
    Component.onCompleted:{Recovery.refreshRecoveries();if(Recovery.hasRecoverableWork)open()}
    Connections{target:Recovery;function onRecoveryChanged(){if(Recovery.hasRecoverableWork&&!root.visible)root.open()}}
    contentItem:ColumnLayout{spacing:Theme.spacing.md
        RowLayout{Layout.fillWidth:true
            Rectangle{width:40;height:40;radius:12;color:Theme.colors.warningSoft;Icon{anchors.centerIn:parent;width:19;height:19;name:"projects"}}
            ColumnLayout{Layout.fillWidth:true;spacing:1
                Text{text:"A newer unsaved version was found";color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.sectionTitle;font.weight:Theme.type.semibold}
                Text{Layout.fillWidth:true;text:"Your saved projects are safe. Choose which recovery copy you want to restore.";color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.small;wrapMode:Text.WordWrap}
            }
        }
        ScrollView{Layout.fillWidth:true;Layout.fillHeight:true;clip:true
            ColumnLayout{width:parent.width;spacing:Theme.spacing.sm
                Repeater{model:Recovery.recoveries;delegate:RecoveryCard{snapshot:modelData;onRecoverRequested:function(id){if(Recovery.recoverSnapshot(id)&&!Recovery.hasRecoverableWork)root.close()};onSavedRequested:function(id){Recovery.openSavedVersion(id);root.close()};onReviewRequested:function(id){root.reviewData=Recovery.review(id);reviewBox.visible=true};onDiscardRequested:function(id){Recovery.discardSnapshot(id);if(!Recovery.hasRecoverableWork)root.close()}}}
            }
        }
        AppCard{id:reviewBox;visible:false;Layout.fillWidth:true;implicitHeight:review.implicitHeight+24;RecoveryComparison{id:review;anchors.fill:parent;anchors.margins:12;comparison:root.reviewData.comparison||({})}}
        RowLayout{Layout.fillWidth:true;Text{Layout.fillWidth:true;text:"You can come back to recovery later.";color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption}AppButton{text:"Later";variant:"secondary";onClicked:root.close()}}
    }
}
