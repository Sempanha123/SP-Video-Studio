import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase23 1.0
import "../theme"
import "../components"

AppCard {
    ColumnLayout {
        anchors.fill:parent; anchors.margins:Theme.spacing.md; spacing:Theme.spacing.xs
        Text { text:"Reframe"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.headingSmall; font.weight:Theme.type.semibold }
        AppComboBox { id:scene; accessibleName:"Scene to reframe"; Layout.fillWidth:true; model:Shorts.sceneOptions; textRole:"name" }
        RowLayout { Layout.fillWidth:true
            Repeater { model:["Left","Center","Right"]
                delegate:SecondaryButton { required property string modelData; text:modelData; compact:true; enabled:scene.currentIndex>=0; onClicked:Shorts.applyReframePreset(Shorts.sceneOptions[scene.currentIndex].id,modelData.toLowerCase(),zoom.value) }
            }
        }
        RowLayout { Layout.fillWidth:true
            SecondaryButton { text:"Top"; compact:true; enabled:scene.currentIndex>=0; onClicked:Shorts.applyReframePreset(Shorts.sceneOptions[scene.currentIndex].id,"top",zoom.value) }
            SecondaryButton { text:"Bottom"; compact:true; enabled:scene.currentIndex>=0; onClicked:Shorts.applyReframePreset(Shorts.sceneOptions[scene.currentIndex].id,"bottom",zoom.value) }
            Text { text:"Zoom"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
            Slider { id:zoom; Layout.fillWidth:true; from:1; to:2.5; value:1; stepSize:.05; Accessible.name:"Reframe zoom, "+Math.round(value*100)+" percent"; Accessible.role:Accessible.Slider }
            Text { text:Math.round(zoom.value*100)+"%"; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
        }
        Text { Layout.fillWidth:true; text:"9:16 safe-area guides are recommendations only. Split moving subjects and reframe each clip manually; no face tracking is used."; wrapMode:Text.WordWrap; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
    }
}
